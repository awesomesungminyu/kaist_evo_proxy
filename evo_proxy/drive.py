"""Fetch and verify GitHub Release and Drive archives for the selected tasks."""
import hashlib
import os
import shutil
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import gdown
import requests
from requests import RequestException

from . import harness


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def select_tasks(selectors):
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
    return selected


def fetch(destination, selected):
    manifest = harness.read(Path(__file__).with_name('drive_manifest.json'))
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


def prepare_bundle(source, selected=None):
    """Stage a local outer TAR and verify every nested archive before preparation."""
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
        return harness.prepare(directory, selected)


BUNDLE = {
    'name': 'proxy-task-bench-data_20261124.tar',
    'size': 881797120,
    'sha256': '6b74b5ec8f0132457d8ff053d7a83e4adbf5db37ea6ac812aa253dbe70c777a9',
}
RELEASE_PAGE = 'https://github.com/awesomesungminyu/kaist_evo_proxy/releases/tag/data-20261124'
RELEASE_URL = RELEASE_PAGE.replace('/tag/', '/download/') + '/' + BUNDLE['name']


def write_response(response, output, expected):
    received = 0
    for chunk in response.iter_content(chunk_size=1024 * 1024):
        received += len(chunk)
        if received > expected:
            raise ValueError('GitHub Release response exceeds expected size')
        output.write(chunk)
    if received != expected:
        raise ValueError('GitHub Release response is incomplete')


def download_asset(url, path, size):
    """Use bounded range requests when the server supports them."""
    timeout = (15, 60)
    with requests.get(url, headers={'Range': 'bytes=0-0'}, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        if response.status_code == 200:
            with path.open('wb') as output:
                write_response(response, output, size)
            return
        if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes 0-0/{size}':
            raise ValueError('Unexpected GitHub Release range response')
    with path.open('wb') as output:
        output.truncate(size)
    segment = 32 * 1024 * 1024

    def fetch_segment(start):
        stop = min(start + segment, size) - 1
        span = f'{start}-{stop}'
        with requests.get(url, headers={'Range': f'bytes={span}'}, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {span}/{size}':
                raise ValueError('Unexpected GitHub Release range response')
            with path.open('r+b') as output:
                output.seek(start)
                write_response(response, output, stop - start + 1)

    with ThreadPoolExecutor(max_workers=8) as workers:
        for _ in workers.map(fetch_segment, range(0, size, segment)):
            pass


def fetch_release(destination):
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / BUNDLE['name']
    if target.is_file():
        verify(target, BUNDLE)
        print(f'Using verified cached bundle: {target.name}', flush=True)
        return target
    url = os.getenv('EVO_PROXY_RELEASE_URL', RELEASE_URL)
    with tempfile.TemporaryDirectory(dir=destination) as staging:
        path = Path(staging) / target.name
        download_asset(url, path, BUNDLE['size'])
        verify(path, BUNDLE)
        path.replace(target)
    print(f'Verified GitHub Release bundle: {target.name} ({BUNDLE["size"]} bytes)', flush=True)
    return target


def download_and_prepare(destination, selectors):
    selected = select_tasks(selectors)
    try:
        archive = fetch_release(destination)
    except (RequestException, ValueError, OSError):
        print(f'{BUNDLE["name"]}: GitHub Release download or verification failed. Trying Drive.', flush=True)
        try:
            fetch(destination, selected)
        except (ValueError, OSError, tarfile.TarError) as error:
            folder = harness.read(Path(__file__).with_name('drive_manifest.json'))['folder']
            raise ValueError(f'{error}. Manual downloads: {RELEASE_PAGE} or {folder}') from error
        return harness.prepare(destination, selected)
    return prepare_bundle(archive, selected)
