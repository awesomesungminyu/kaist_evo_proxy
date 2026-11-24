"""Fetch and verify public Drive archives for the selected tasks."""
import hashlib
import tarfile
import tempfile
from pathlib import Path

import gdown
from requests import RequestException

from . import harness


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(destination, selectors):
    manifest = harness.read(Path(__file__).with_name('drive_manifest.json'))
    tasks = harness.read(harness.ROOT / 'tasks/tasks.json')['tasks']
    ids = {task['id'] for task in tasks}
    selected = set()
    for value in selectors:
        for selector in value.split(','):
            if selector == 'all':
                selected.update(ids)
            elif selector in ('tier1', 'tier2'):
                selected.update(task['id'] for task in tasks if task['tier'] == int(selector[-1]))
            elif selector in ids:
                selected.add(selector)
            else:
                raise ValueError(f'Unknown task: {selector}')
    destination.mkdir(parents=True, exist_ok=True)
    archives = [item for item in manifest['archives'] if not item['optional'] and selected.intersection(item['tasks'])]
    for item in archives:
        name = item['name']
        target = destination / name
        if not target.is_file():
            with tempfile.TemporaryDirectory(dir=destination) as staging:
                path = Path(staging) / name
                for retry in range(2):
                    try:
                        result = gdown.download(id=item['id'], output=str(path), resume=False)
                    except (gdown.exceptions.FileURLRetrievalError, RequestException):
                        result = None
                    if result is not None:
                        break
                    if retry == 0:
                        print(f'{name}: retrying the Drive request once', flush=True)
                else:
                    raise ValueError(f'{name}: Drive unavailable. Download manually from {manifest["folder"]}')
                verify(path, item)
                path.replace(target)
        else:
            verify(target, item)
        print(f'Verified {name} ({item["size"]} bytes)', flush=True)
    for item in archives:
        with tarfile.open(destination / item['name'], 'r:gz') as archive:
            archive.extractall(destination, filter='data')
    return selected


def verify(path, item):
    if path.stat().st_size != item['size'] or checksum(path) != item['sha256']:
        raise ValueError(f'{item["name"]}: size or SHA-256 mismatch')


def prepare_bundle(source):
    """Stage a local outer TAR and verify every nested archive before preparation."""
    import shutil

    manifest = harness.read(Path(__file__).with_name('drive_manifest.json'))
    archives = [item for item in manifest['archives'] if not item['optional']]
    name_set = {item['name'] for item in archives} | {'README.txt', 'SHA256SUMS_all.txt'}
    with tempfile.TemporaryDirectory(prefix='evo-proxy-data-') as staging:
        directory = Path(staging)
        with tarfile.open(source, 'r:') as bundle:
            members = bundle.getmembers()
            if (len(members) != len(name_set) or {member.name for member in members} != name_set
                    or not all(member.isfile() for member in members)):
                raise ValueError(f'{source.name}: unexpected bundle members')
            for item in archives:
                member = bundle.getmember(item['name'])
                if member.size != item['size']:
                    raise ValueError(f'{member.name}: size or SHA-256 mismatch')
                target = directory / member.name
                with bundle.extractfile(member) as stream, target.open('wb') as output:
                    shutil.copyfileobj(stream, output)
                verify(target, item)
        for item in archives:
            with tarfile.open(directory / item['name'], 'r:gz') as archive:
                archive.extractall(directory, filter='data')
        return harness.prepare(directory)
