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
