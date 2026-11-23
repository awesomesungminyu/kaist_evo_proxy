"""Rebuild feedback.md from an evaluation output directory."""
import argparse
from pathlib import Path
from evo_proxy.feedback import make_feedback
from evo_proxy.harness import read

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    run=parser.parse_args().run
    print(make_feedback(*(read(run/f'{name}.json') for name in ('report','judged','resources'))),end='')
