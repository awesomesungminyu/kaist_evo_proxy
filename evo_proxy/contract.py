"""Run the frozen candidate probes using declared task shapes, without data."""
from pathlib import Path
import os
import sys
import torch

from validation.precheck import check_configuration
from proxy_tasks.common_set.plugins import describe, load
from .harness import ROOT, read, save


def check(reference, output, gpu=False):
    torch.set_num_threads(max(1, min(2, (os.cpu_count() or 2)//2)))
    tasks = read(ROOT/'tasks/tasks.json')['tasks']
    result = dict(status='failed', candidate=None, tasks={},
                  data_checks='데이터 준비 후 확인 / deferred until data is prepared')
    try:
        cls = load(reference)
        result['candidate'] = describe(reference)
        cache = {}
        for task in tasks:
            config = {k: task['model'][k] for k in ('d_model','n_layers','num_heads','l_max')}
            key = tuple(config.items())
            if key not in cache:
                try:
                    cache[key] = check_configuration(cls, config, gpu=gpu)
                except Exception as error:
                    cache[key] = dict(passed=False, error=f'{type(error).__name__}: {error}')
            result['tasks'][task['id']] = dict(configuration=config, **cache[key])
        result['status'] = 'passed' if all(row['passed'] for row in result['tasks'].values()) else 'failed'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    save(output, result)
    return int(result['status'] != 'passed')


if __name__ == '__main__':
    sys.exit(check(sys.argv[1], Path(sys.argv[2]), '--gpu' in sys.argv[3:]))
