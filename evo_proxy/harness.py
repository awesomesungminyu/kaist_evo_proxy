"""Install and invoke the pinned evaluator in the current virtual environment."""
from contextlib import contextmanager
import fcntl
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
    if CPU_SETUP:
        subprocess.run([sys.executable,'-m','pip','install','--index-url',
                        'https://download.pytorch.org/whl/cpu','torch==2.5.1'],check=True)
    subprocess.run([sys.executable,'-m','pip','install','-r',str(HARNESS/'requirements.txt')],check=True)
    for dependency in ('formal','retnet'):
        subprocess.run(['bash','setup.sh',dependency],cwd=HARNESS,check=True)


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


def prepare(source):
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


def precheck(candidate, out):
    ref = f'{candidate}:CandidateMixer'
    output = out/'precheck.json'
    official = run('validation','precheck','--mixer',ref,'--data-root',DATA,'--out',output,device='cpu')
    extension = out/'precheck_extra.json'
    extra = run('release_tasks','check','--mixer',ref,'--out',extension,device='cpu')
    return official.returncode == extra.returncode == 0, read(output), read(extension)


@contextmanager
def serial_gpu(enabled):
    if not enabled:
        yield
        return
    path = Path(tempfile.gettempdir())/f'evo-proxy-{os.getuid()}.lock'
    with path.open('a') as file:
        fcntl.flock(file,fcntl.LOCK_EX)
        yield
