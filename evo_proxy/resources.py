"""External training-process measurements (Linux, one process tree at a time)."""
import os
from pathlib import Path
import re
import subprocess
import time


def query(kind, columns):
    output = subprocess.check_output(['nvidia-smi',f'--query-{kind}={columns}',
                                      '--format=csv,noheader,nounits'],text=True,timeout=15)
    return [tuple(part.strip() for part in line.split(',')) for line in output.splitlines() if line.strip()]


def wait_idle(seconds=7200):
    def idle():
        values = query('gpu','memory.used,utilization.gpu')
        return values and all(int(memory)<=1024 and int(util)<=10 for memory,util in values) and not query('compute-apps','pid')
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        if idle():
            return
        time.sleep(15)
    raise TimeoutError('GPU remained occupied during the idle wait')


def descendants(pid):
    found, pending = {pid}, [pid]
    while pending:
        current = pending.pop()
        try:
            children = {int(v) for v in Path(f'/proc/{current}/task/{current}/children').read_text().split()}
        except OSError:
            continue
        pending.extend(children - found)
        found.update(children)
    return found


def linux_owns_gpu(pids):
    for pid in pids:
        try:
            for item in Path(f'/proc/{pid}/fd').iterdir():
                try:
                    if os.readlink(item).startswith('/dev/nvidia'):
                        return True
                except OSError:
                    pass
        except OSError:
            pass
    return False


def measure(command, *, cwd, env, out, gpu):
    timing=out/'cpu_time.txt'
    external_time=Path('/usr/bin/time').is_file()
    launch=['/usr/bin/time','-o',str(timing),'-f','%U %S %M',*command] if external_time else command
    started=time.monotonic()
    peak, usage = None, []
    with (out/'process.log').open('w') as log:
        process=subprocess.Popen(launch,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None:
            if gpu:
                try:
                    rows=query('compute-apps','gpu_uuid,pid,used_gpu_memory')
                    tree=descendants(process.pid)
                    known=[(dev,int(mem)) for dev,pid,mem in rows if pid.isdigit() and mem.isdigit() and int(pid) in tree]
                    if not known and len(rows)==1 and rows[0][2].isdigit() and linux_owns_gpu(tree):
                        known=[(rows[0][0],int(rows[0][2]))]
                    if known and len(known)==len(rows):
                        snapshot=sum(mem for _,mem in known)
                        peak=snapshot if peak is None else max(peak,snapshot)
                        active={dev for dev,_ in known}
                        usage.extend(int(u) for dev,u in query('gpu','uuid,utilization.gpu') if dev in active and u.isdigit())
                except (subprocess.SubprocessError,OSError,ValueError):
                    pass
            try:
                process.wait(timeout=1 if gpu else .25)
            except subprocess.TimeoutExpired:
                pass
    elapsed = time.monotonic()-started
    cpu,rss=None,None
    if timing.is_file():
        for line in timing.read_text().splitlines():
            if re.fullmatch(r'[0-9.]+ [0-9.]+ [0-9]+',line):
                user,system,peak_rss=map(float,line.split())
                cpu,rss=user+system,peak_rss/1024
    return dict(exit_code=process.returncode,wall_seconds=elapsed,gpu_time_min=elapsed/60 if gpu else None,
                peak_vram_mib=peak,gpu_util_pct=sum(usage)/len(usage) if usage else None,
                cpu_time_s=cpu,peak_rss_mib=rss)
