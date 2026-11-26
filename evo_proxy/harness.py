"""Install and invoke the pinned evaluator in the current virtual environment."""
from contextlib import contextmanager
import fcntl
from importlib import metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
HOME = Path(os.environ.get('EVO_PROXY_HOME', Path.home()/'.cache'/'kaist-evo-proxy')).expanduser().resolve()
DATA = Path(os.environ.get('EVO_PROXY_DATA', HOME/'data')).expanduser().resolve()
HARNESS = HOME/'harness'
TFL = HARNESS/'third_party/tfl'
CPU_SETUP = os.getenv('EVO_PROXY_CPU') == '1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2)+'\n', encoding='utf-8')


def environment(device=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', PYTHONPATH=str(HARNESS))
    # Evaluation subprocesses do not need model-provider credentials.
    for name in list(env):
        if re.search(r'(API_KEY|ACCESS_TOKEN|SECRET_KEY|PASSWORD)$', name):
            env.pop(name)
    env.pop('PROXY_CANDIDATE_MIXER', None)
    if device == 'cpu':
        env['CUDA_VISIBLE_DEVICES'] = ''
    return env


def command(*args):
    return [sys.executable, '-m', *map(str,args)]


def run(*args, device=None, **kwargs):
    return subprocess.run(command(*args), cwd=HARNESS, env=environment(device), **kwargs)


def pin():
    value = read(ROOT/'reference'/'harness.json')
    if not re.fullmatch('[a-f0-9]{40}', value['commit']):
        raise ValueError('The harness pin must be a full commit hash')
    return value


def installed():
    if not (HARNESS/'release_tasks'/'protocol.json').is_file():
        raise ValueError('Run evo-proxy setup first')
    return subprocess.check_output(['git','rev-parse','HEAD'], cwd=HARNESS, text=True).strip() == pin()['commit']


def setup():
    source = pin()
    url = os.getenv('EVO_PROXY_HARNESS_URL',source['url'])
    HOME.mkdir(parents=True,exist_ok=True)
    if not HARNESS.exists():
        with tempfile.TemporaryDirectory(dir=HOME) as stage:
            checkout = Path(stage)/'checkout'
            subprocess.run(['git','clone','--no-checkout','--',url,str(checkout)],check=True)
            subprocess.run(['git','checkout','--detach',source['commit']],cwd=checkout,check=True)
            checkout.rename(HARNESS)
    if not installed():
        raise ValueError(f'The checkout at {HARNESS} does not match the pinned commit')
    timeout = os.getenv('PIP_DEFAULT_TIMEOUT', '120')
    try:
        if float(timeout) <= 0:
            raise ValueError
    except ValueError:
        raise ValueError('PIP_DEFAULT_TIMEOUT must be a positive number') from None
    requirements = [line.strip() for line in (HARNESS/'requirements.txt').read_text().splitlines()
                    if line.strip() and not line.lstrip().startswith('#')]
    for requirement in requirements:
        options = ['--constraint', str(HARNESS/'requirements.txt')]
        if CPU_SETUP and requirement.startswith('torch=='):
            options += ['--index-url', 'https://download.pytorch.org/whl/cpu']
        install_requirement(requirement, timeout, options)
    # TFL's Parity/Tomita loaders import these even for a one-step smoke.
    for requirement in ('gensim==4.3.3', 'attrdict3==2.0.2', 'matplotlib==3.9.4', 'seaborn==0.13.2'):
        install_requirement(requirement, timeout, ['--constraint', str(HARNESS/'requirements.txt')])
    subprocess.run(['bash', 'setup.sh', 'formal'], cwd=HARNESS, check=True)
    vendor = HARNESS/'third_party/fla_vendor'
    for requirement in ('flash-linear-attention==0.3.1', 'einops==0.8.1'):
        install_requirement(requirement, timeout, ['--no-deps', '--target', str(vendor)], vendor)


def install_requirement(requirement, timeout, options, target=None):
    # Packaging ships with pip, including in a fresh Python virtual environment.
    from pip._vendor.packaging.requirements import Requirement

    spec = Requirement(requirement)
    if target is None:
        try:
            current = metadata.version(spec.name)
        except metadata.PackageNotFoundError:
            current = None
    else:
        normalized = lambda name: re.sub(r'[-_.]+', '-', name).lower()
        current = next((dist.version for dist in metadata.distributions(path=[str(target)])
                        if normalized(dist.metadata['Name']) == normalized(spec.name)), None)
    if current is not None and spec.specifier.contains(current, prereleases=True):
        print(f'Already installed: {spec.name} {current}; skipping', flush=True)
        return
    args = [sys.executable, '-m', 'pip', 'install', '--timeout', str(timeout), '--retries', '10',
            *options, requirement]
    try:
        subprocess.run(args, check=True)
    except subprocess.CalledProcessError:
        print(f'Failed package: {spec.name}', file=sys.stderr, flush=True)
        raise ValueError('같은 명령을 다시 실행하면 이어서 설치됩니다. '
                         'Run the same command again to continue; installed compatible packages are skipped.') from None


def data_ready():
    results = []
    for module in ('validation','release_tasks'):
        result = run(module,'data','--data-root',DATA,capture_output=True,text=True)
        text = result.stdout
        try:
            rows = json.loads(text) if module=='validation' else [json.loads(line) for line in text.splitlines()]
        except json.JSONDecodeError:
            raise ValueError(f'{module} data check failed') from None
        results.extend(rows)
    return results


def prepare(source, selected=None):
    if selected is not None:
        tasks = read(ROOT/'tasks/tasks.json')['tasks']
        extensions = {task['id'] for task in tasks if task['id'] in ('promoters', 'bach')}
        results = [run('validation', 'prepare', '--source', source, '--data-root', DATA,
                       '--task', task).returncode for task in sorted(selected - extensions)]
        if selected & extensions:
            # The extension command checks both tasks, so inspect selected readiness below.
            run('release_tasks', 'data', '--source', source, '--data-root', DATA)
        ready = [row for row in data_ready() if row['task'] in selected]
        print(json.dumps(ready, ensure_ascii=False, indent=2))
        return int(any(results) or len(ready) != len(selected) or not all(row['ready'] for row in ready))
    results = [
        run('validation','prepare','--source',source,'--data-root',DATA).returncode,
        run('release_tasks','data','--source',source,'--data-root',DATA).returncode,
    ]
    ready = data_ready()
    print(json.dumps(ready, ensure_ascii=False, indent=2))
    return int(any(results) or len(ready)!=18 or not all(t['ready'] for t in ready))


def skills_path():
    return Path(os.environ.get('EVOSCIENTIST_WORKSPACE_DIR', Path.cwd())).expanduser().resolve()/'skills'


def new_output(path):
    path = path.expanduser().resolve()
    try:
        path.mkdir(parents=True)
        return path
    except FileExistsError:
        if not path.is_dir():
            raise
        return Path(tempfile.mkdtemp(prefix='run-',dir=path))


def precheck(candidate, out, gpu=False, contract_only=False):
    ref = f'{candidate}:CandidateMixer'
    output = out/'precheck.json'
    extension = out/'precheck_extra.json'
    args = ['validation','precheck','--mixer',ref,'--data-root',DATA,'--out',output]
    if contract_only:
        args = ['evo_proxy.contract', ref, output]
        if gpu:
            args.append('--gpu')

    if gpu and not contract_only:
        args.append('--gpu-benchmark')
    with (out/'precheck_official.log').open('w') as log:
        official = run(*args,device=None if gpu else 'cpu',stdout=log,stderr=subprocess.STDOUT)
    with (out/'precheck_extension.log').open('w') as log:
        extra = run('release_tasks','check','--mixer',ref,'--out',extension,
                    device='cpu',stdout=log,stderr=subprocess.STDOUT)
    check = read(output) if output.is_file() else dict(status='failed',error='See precheck_official.log')
    extras = read(extension) if extension.is_file() else {}
    if output.is_file() and extension.is_file() and any(not ok for row in (check.get('tasks', {})|extras).values()
           for name, ok in row.get('checks', {}).items()
           if name not in ('parameter_budget','gpu_max_length_finite')):
        path = out/'precheck_diagnostics.json'
        with (out/'precheck_diagnostics.log').open('w') as log:
            run('evo_proxy.precheck',ref,output,extension,path,
                device='cpu',stdout=log,stderr=subprocess.STDOUT)
        if path.is_file():
            for task, details in read(path).items():
                (check.get('tasks', {})|extras)[task]['diagnostics'] = details
    return official.returncode == extra.returncode == 0, check, extras


@contextmanager
def serial_gpu(enabled):
    if not enabled:
        yield
        return
    path = Path(tempfile.gettempdir())/f'evo-proxy-{os.getuid()}.lock'
    with path.open('a') as file:
        fcntl.flock(file,fcntl.LOCK_EX)
        yield
