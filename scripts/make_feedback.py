"""Rebuild feedback.md from an evaluation output directory."""
import argparse
from pathlib import Path
from evo_proxy.feedback import make_feedback
from evo_proxy.harness import read
from evo_proxy.precheck import format_precheck

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    run=parser.parse_args().run
    report, judged, resources = (read(run/f'{name}.json') for name in ('report','judged','resources'))
    if judged['stop_reason'] == 'precheck_failed':
        # This also preserves diagnostics for capped/failed imports with no native JSON.
        print((run/'feedback.md').read_text(encoding='utf-8'),end='')
    else:
        print(make_feedback(report,judged,resources),end='')
