"""Rebuild feedback.md from an evaluation output directory."""
import argparse
from pathlib import Path
from evo_proxy.feedback import make_feedback
from evo_proxy.harness import read

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    run=parser.parse_args().run
    report, judged, resources = (read(run/f'{name}.json') for name in ('report','judged','resources'))
    print(make_feedback(report,judged,resources,report.get('precheck_feedback')),end='')
