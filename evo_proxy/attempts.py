"""Bound distinct prechecked candidate revisions for a single agent run."""
from contextlib import contextmanager
import fcntl
from hashlib import sha256
import os
from pathlib import Path

from .harness import read, save


@contextmanager
def attempt(candidate, out, command):
    path = os.getenv('EVO_PROXY_ATTEMPT_LOG')
    if not path:
        yield None, None
        return
    path = Path(path)
    limit = int(os.environ['EVO_PROXY_MAX_ATTEMPTS'])
    identity = sha256(candidate.read_bytes()).hexdigest() if candidate.is_file() else 'missing'
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        rows = read(path) if path.is_file() else []
        prior = dict.fromkeys(row['sha256'] for row in rows if row['admitted'])
        index = list(prior).index(identity)+1 if identity in prior else len(prior)+1
        blocked = index > limit
        entry = dict(candidate=candidate.name, sha256=identity, command=command, out=str(out),
                     attempt=index, limit=limit, admitted=not blocked, status='started')
        rows.append(entry)
        try:
            yield entry, f'Candidate attempt budget reached ({len(prior)}/{limit})' if blocked else None
        finally:
            save(path,rows)
