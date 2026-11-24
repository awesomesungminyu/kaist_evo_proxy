"""Portable command-line harness and EvoScientist entry point."""
import argparse
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import shutil
import subprocess
import sys

from . import harness as h
from .attempts import attempt
from .precheck import format_precheck
from .judge import REFERENCE, compare, judge
from .resources import measure, query, wait_idle
from .result import load_baseline, write_result

PROFILES = ('smoke','tier1','tier2','cascade','full')
SKILLS = ('proxy-harness','mixer-contract')


def install_skills(destination):
    destination = destination.resolve()
    destination.mkdir(parents=True,exist_ok=True)
    for name in SKILLS:
        source = h.ROOT/'skills'/name
        target = destination/name
        if target.exists():
            if (target/'SKILL.md').read_bytes() != (source/'SKILL.md').read_bytes():
                raise ValueError(f'Existing skill differs at {target}; choose another directory')
        else:
            shutil.copytree(source,target)
    print(destination)


def doctor(core=False):
    results = {}
    results['pinned_harness'] = h.installed()
    results['formal'] = (h.TFL/'src/args.py').is_file()
    results['retnet'] = (h.HARNESS/'third_party/fla_vendor/fla').is_dir()
    results['data_18'] = len(rows:=h.data_ready())==18 and all(row['ready'] for row in rows)
    probe = subprocess.run([sys.executable,'-c',
        'import json, torch; print(json.dumps({"torch": torch.__version__, "cuda": torch.cuda.is_available()}))'],
        text=True,capture_output=True)
    runtime = json.loads(probe.stdout) if probe.returncode==0 else {}
    results['torch'] = runtime.get('torch','').split('+')[0]=='2.5.1'
    results['cuda'] = 'not required (CPU setup)' if h.CPU_SETUP else runtime.get('cuda',False)
    results['nvidia_smi'] = shutil.which('nvidia-smi') is not None or h.CPU_SETUP
    try:
        results['evoscientist_0_4_1'] = version('EvoScientist')=='0.4.1'
    except PackageNotFoundError:
        results['evoscientist_0_4_1'] = False
    results['workspace_skills'] = all((h.skills_path()/name/'SKILL.md').is_file() for name in SKILLS)
    print(json.dumps(results,indent=2))
    checks = [v for k,v in results.items() if not core or k not in ('evoscientist_0_4_1','workspace_skills')]
    return int(False in checks)


def ordered_tasks(profile,config):
    tasks=config['tasks']
    if profile=='tier1':
        return [task for task in tasks if task['tier']==1]
    if profile=='tier2':
        return [task for task in tasks if task['tier']==2]
    return sorted(tasks,key=lambda t:(t['tier'],t['id'] in ('T1-R0-04','T1-R0-05')))


def run_tasks(candidate, profile, out, tasks, checks):
    smoke = profile=='smoke'
    budget = 'smoke' if smoke else 'full'
    reference = h.read(REFERENCE)['tasks']
    rows, costs = {}, {}
    tier1_passes, misses, gate, stop = 0, 0, None, 'completed'
    for task in tasks:
        task_id=task['id']
        if profile=='cascade':
            if task['tier']==1 and misses>=2:
                gate, stop = False, 'tier1_two_below_threshold'
                break
            if task['tier']==2:
                gate=tier1_passes>=7
                if not gate:
                    stop='tier1_two_below_threshold' if misses>=2 else 'tier1_gate_unconfirmed'
                    break
        if not smoke:
            try:
                wait_idle()
            except TimeoutError:
                stop='gpu_idle_timeout'
                break
        folder=out/'observations'/task_id
        folder.mkdir(parents=True)
        mode='cpu' if smoke else 'cuda'
        costs[task_id]=measure(h.command('release_tasks','cell','--task',task_id,'--profile',budget,
            '--mixer',f'{candidate}:CandidateMixer','--out',folder,'--data-root',h.DATA,'--tfl-root',h.TFL),
            cwd=h.HARNESS,env=h.environment(mode),out=folder,gpu=not smoke)
        result=folder/'result.json'
        raw=h.read(result) if result.is_file() else dict(status='failed',error='See process.log')
        metrics=raw.get('metrics',{})
        score=metrics.get(task['metric']) if not smoke and raw['status']=='done' else None
        rows[task_id]=dict(task=task_id,tier=task['tier'],name=task['name'],status=raw['status'],
                           mean=score, completed_seeds=[0] if raw['status']=='done' else [],
                           requested_seeds=[0], metric=task['metric'], evidence=raw.get('evidence'),
                           error=raw.get('error'))
        if 'smoke_loss' in raw:
            rows[task_id]['smoke_loss']=raw['smoke_loss']
        native = raw.get('native_result')
        details = h.read(Path(native)) if native and Path(native).is_file() else {}
        per_block = checks[task_id].get('block_parameters')
        per_mixer = checks[task_id].get('mixer_parameters')
        layers = task['model']['n_layers']
        costs[task_id]['parameters'] = raw.get('parameters') or dict(
            total=details.get('n_params'),
            block=per_block*layers if per_block is not None else None,
            mixer=per_mixer*layers if per_mixer is not None else None,
        )
        if smoke and 'smoke_loss' not in raw:
            rows[task_id]['smoke_loss'] = details.get('loss')
        if profile=='cascade' and task['tier']==1:
            ratio=compare(score,reference[task_id])
            if ratio is not None:
                tier1_passes+=ratio>=.8
                misses+=ratio<.8
        print(f"{task_id}: {raw['status']}",flush=True)
    if stop=='completed' and any(r['status']!='done' for r in rows.values()):
        stop='incomplete'
    return rows,costs,gate,stop


def checked(candidate, target, command, gpu=False):
    with attempt(candidate,target,command) as (record, blocked):
        if blocked:
            result = False, dict(status='failed',error=blocked), {}
        elif gpu:
            with h.serial_gpu(True):
                wait_idle()
                result = h.precheck(candidate,target,gpu=True)
        else:
            result = h.precheck(candidate,target)
        if record is not None:
            record['status'] = 'passed' if result[0] else 'blocked' if blocked else 'failed'
    return result


def hardware(profile):
    try:
        gpus = [dict(name=name, vram_mib=int(memory))
                for name, memory in query('gpu', 'name,memory.total')]
    except (OSError, ValueError, subprocess.SubprocessError):
        gpus = []
    return dict(device='CPU (smoke)' if profile == 'smoke' else 'CUDA', gpus=gpus)


def evaluate(candidate, profile, out, only=None, baseline_run=None, baseline_model=None):
    target = h.new_output(out)
    baseline_path, _ = load_baseline(target.resolve(), {'profile': profile}, baseline_run)
    ok,check,extra = checked(candidate,target,'eval')
    config=h.read(h.ROOT/'tasks/tasks.json')
    tasks=ordered_tasks(profile,config)
    if only is not None:
        tasks=[task for task in tasks if task['id']==only]
    if ok:
        with h.serial_gpu(profile!='smoke'):
            rows,costs,gate,stop=run_tasks(candidate,profile,target,tasks,check['tasks']|extra)
    else:
        rows,costs,gate,stop={}, {}, None, 'precheck_failed'
    report=dict(profile=profile, status='blocked' if not ok else
                'done' if stop=='completed' else 'incomplete',
                candidate=check.get('candidate'), performance_comparable=ok and profile!='smoke',
                gate_passed=gate,stop_reason=stop,
                tasks=[rows.get(t['id'],dict(task=t['id'],tier=t['tier'],name=t['name'],
                                             mean=None,status='not_run')) for t in tasks])
    reference = h.read(REFERENCE)['tasks']
    report.update(baseline_model=baseline_model, hardware=hardware(profile),
                  resource_baseline=str(baseline_path) if baseline_path else None,
                  score_reference={row['task']: reference[row['task']] for row in report['tasks']})
    if not ok:
        report['precheck_diagnostics'] = format_precheck(check,extra)
    judged=judge(report,config['tasks'])
    h.save(target/'report.json',report)
    h.save(target/'judged.json',judged)
    h.save(target/'resources.json',costs)
    write_result(target, baseline_path)
    print(f'Output: {target}')
    return int(stop not in ('completed','tier1_two_below_threshold'))


def main(argv=None):
    parser=argparse.ArgumentParser(prog='evo-proxy',description=__doc__)
    actions=parser.add_subparsers(dest='command',required=True)
    actions.add_parser('setup',help='Install the pinned evaluator and dependencies')
    data=actions.add_parser('data',help='Prepare extracted Drive bundles and check readiness')
    sources = data.add_mutually_exclusive_group(required=True)
    sources.add_argument('--source', type=Path)
    sources.add_argument('--download', action='store_true')
    data.add_argument('--tasks', nargs='+', default=['all'])
    data.add_argument('--dest', type=Path, default=Path('incoming'))
    diagnose=actions.add_parser('doctor',help='Check Torch, CUDA, datasets, EvoScientist and installed skills')
    diagnose.add_argument('--core',action='store_true',help='Only require evaluator readiness')
    skills=actions.add_parser('install-skills',help='Copy skills to <EvoScientist workspace>/skills')
    skills.add_argument('destination',type=Path,nargs='?',default=h.skills_path())
    check=actions.add_parser('check',help='Check one candidate on CPU without training')
    check.add_argument('mixer',type=Path)
    check.add_argument('--out',type=Path,default=Path('runs/precheck'))
    check.add_argument('--gpu-benchmark',action='store_true',help='Also probe maximum-length GPU memory on the official tasks')
    rebuild = actions.add_parser('report', help='Rebuild result.md from saved evaluation JSON')
    rebuild.add_argument('run', type=Path)
    rebuild.add_argument('--baseline-run', type=Path)
    ev=actions.add_parser('eval',help='Evaluate a candidate and write result.md')
    ev.add_argument('--baseline-run', type=Path)
    ev.add_argument('mixer',type=Path)
    base=actions.add_parser('baseline',help='Run a named reference mixer')
    names=sorted(p.stem for p in (h.ROOT/'baselines/mixers').glob('*.py'))
    base.add_argument('name',choices=names)
    task_ids=[t['id'] for t in h.read(h.ROOT/'tasks/tasks.json')['tasks']]
    for cmd in (ev,base):
        cmd.add_argument('--task',choices=task_ids,help='Select one task in smoke mode')
        cmd.add_argument('--profile',choices=PROFILES,default='smoke')
        cmd.add_argument('--out',type=Path,default=Path('runs/evaluation'))
    args=parser.parse_args(argv)
    try:
        if args.command=='setup':
            h.setup()
            return 0
        if args.command=='install-skills':
            install_skills(args.destination)
            return 0
        if args.command=='report':
            print(write_result(args.run, args.baseline_run))
            return 0
        if not h.installed():
            raise ValueError('The evaluator does not match the pin; run evo-proxy setup with a clean install directory')
        if args.command=='doctor':
            return doctor(args.core)
        if args.command=='data':
            if not args.download:
                if args.tasks != ['all'] or args.dest != Path('incoming'):
                    parser.error('--tasks and --dest require --download')
                source = args.source.resolve()
                if source.is_file() and source.suffix == '.tar':
                    from .drive import prepare_bundle
                    return prepare_bundle(source)
                return h.prepare(source)
            from .drive import download_and_prepare
            return download_and_prepare(args.dest.resolve(), args.tasks)
        if args.command=='check':
            target=h.new_output(args.out)
            ok,check,extra=checked(args.mixer.resolve(),target,'check',args.gpu_benchmark)
            print(f'Precheck: {"passed" if ok else "failed"}')
            print(format_precheck(check,extra))
            return int(not ok)
        candidate = args.mixer.resolve() if args.command=='eval' else h.ROOT/'baselines/mixers'/f'{args.name}.py'
        if args.task and args.profile!='smoke':
            parser.error('--task requires --profile smoke')
        return evaluate(candidate,args.profile,args.out,args.task,
                        getattr(args,'baseline_run',None), args.name if args.command=='baseline' else None)
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        parser.exit(1,f'evo-proxy: {error}\n')


if __name__=='__main__':
    raise SystemExit(main())
