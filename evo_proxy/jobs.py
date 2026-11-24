"""Start a detached evaluation and expose its state without opening results."""

import json
import os
from pathlib import Path
import subprocess
import sys

from . import harness as h


def process_identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    return None if fields[0] == 'Z' else fields[19]


def write_state(target, state):
    temporary = target / '.job.json.tmp'
    h.save(temporary, state)
    temporary.replace(target / 'job.json')


def start(candidate, profile, out, baseline_run=None):
    target = h.new_output(out)
    write_state(target, dict(status='queued', profile=profile))
    args = [sys.executable, '-m', 'evo_proxy.jobs', str(candidate), profile, str(target)]
    if baseline_run is not None:
        args.append(str(baseline_run.resolve()))
    try:
        with (target / 'run.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, start_new_session=True)
    except OSError:
        write_state(target, dict(status='failed', profile=profile))
        raise
    print(f'Started {profile} evaluation (PID {process.pid})\nOutput: {target}')
    return 0


def show(target):
    target = target.resolve()
    if (target / 'job.json').is_file():
        state = h.read(target / 'job.json')
        pid = state.get('pid')
        if state['status'] in ('precheck', 'waiting_for_gpu', 'running') and (
                not pid or process_identity(pid) != state.get('process_identity')):
            state['status'] = 'stopped'
    elif (target / 'report.json').is_file():
        report = h.read(target / 'report.json')
        state = dict(status=report['status'], profile=report['profile'])
    else:
        raise ValueError(f'No evaluation status at {target}')
    state['output'] = str(target)
    state['log'] = str(target / 'run.log') if (target / 'run.log').is_file() else None
    state['result'] = str(target / 'result.md') if (target / 'result.md').is_file() else None
    print(json.dumps(state, indent=2))
    return 0


def worker(candidate, profile, target, baseline_run=None):
    from .cli import evaluate

    pid = os.getpid()
    state = dict(profile=profile, pid=pid, process_identity=process_identity(pid))

    def update(status):
        state['status'] = status
        write_state(target, state)

    update('precheck')
    try:
        code = evaluate(candidate, profile, target, baseline_run=baseline_run, target=target, progress=update)
    except BaseException:
        update('failed')
        raise
    state['exit_code'] = code
    update('done' if code == 0 else 'failed')
    return code


if __name__ == '__main__':
    candidate, profile, target, *baseline = sys.argv[1:]
    sys.exit(worker(Path(candidate), profile, Path(target), Path(baseline[0]) if baseline else None))
