"""Render a human report from saved evaluation records."""
from pathlib import Path

from .harness import read
from .judge import REFERENCE


VERDICTS = {'pass': '통과', 'fail': '실패', 'unknown': '미확인', 'not_run': '미실행'}
NO_BASELINE = '기준 실행 없음'


def transformer_run(report):
    candidate = report.get('candidate') or {}
    return (report.get('baseline_model') == 'transformer'
            or (not report.get('baseline_model') and
                str(candidate.get('path', '')).endswith('/baselines/mixers/transformer.py')))


def load_baseline(run, report, explicit=None):
    def matches(path):
        record = read(path / 'report.json')
        return (transformer_run(record) and record['profile'] == report['profile']
                and record['status'] == 'done')

    if explicit is not None:
        path = explicit.resolve()
        if not matches(path):
            raise ValueError('--baseline-run requires a Transformer baseline with the same profile')
        return path, read(path / 'resources.json')
    saved = report.get('resource_baseline')
    if saved:
        path = Path(saved)
        if path != run and (path / 'resources.json').is_file() and matches(path):
            return path, read(path / 'resources.json')
    paths = sorted(Path('runs').rglob('report.json'), key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in paths:
        candidate = path.parent.resolve()
        if candidate == run or not (candidate / 'resources.json').is_file():
            continue
        try:
            if matches(candidate):
                return candidate, read(candidate / 'resources.json')
        except (OSError, ValueError, KeyError):
            continue
    return None, {}


def number(value, suffix=''):
    return '—' if value is None else f'{value:.2f}{suffix}'


def fold(left, right):
    return '—' if left is None or right in (None, 0) else f'×{left / right:.2f}'


def aggregate(resources, ids, get, combine):
    values = [get(resources.get(task, {})) for task in ids]
    return combine(values) if values and all(value is not None for value in values) else None


def render(report, judged, resources, baseline, baseline_path):
    smoke = report['profile'] == 'smoke'
    lines = []
    for key, total in [('tier1', 8), ('tier2', 10)]:
        tier = judged[key]
        label = 'Tier 1' if key == 'tier1' else 'Tier 2'
        lines.append(f"{label}: {tier['pass_count']}/{total} 통과 "
                     f"(strict {VERDICTS[tier['strict']]}, relaxed {VERDICTS[tier['relaxed']]})")
    if baseline_path is None:
        lines.append(f'자원: {NO_BASELINE} — `evo-proxy baseline transformer --profile {report["profile"]}` 를 먼저 실행')
    else:
        ids = [row['task'] for row in report['tasks']
               if row['status'] == 'done' and resources.get(row['task'], {}).get('exit_code') == 0]
        paired = [task for task in ids if baseline.get(task, {}).get('exit_code') == 0]
        def comparison(get, combine):
            return fold(aggregate(resources, paired, get, combine),
                        aggregate(baseline, paired, get, combine))
        gpu = comparison(lambda row: row.get('gpu_time_min'), sum)
        vram = comparison(lambda row: row.get('peak_vram_mib'), max)
        params = comparison(lambda row: (row.get('parameters') or {}).get('total'), sum)
        basis = '전체'
        if params == '—':
            params = comparison(lambda row: (row.get('parameters') or {}).get('block'), sum)
            basis = '블록'
        lines.append(f'자원: Transformer 대비 GPU 시간 {gpu}, 최대 VRAM {vram}, 파라미터({basis}) {params}')
        lines += ['', f'자원 기준 실행: `{baseline_path}` · 양쪽이 완료한 같은 과제 {len(paired)}/{len(ids)}개']
    if report.get('precheck_diagnostics'):
        lines += ['', '## 계약 검사', '', report['precheck_diagnostics'].strip()]
    reference = report.get('score_reference')
    if reference is None:
        reference = read(REFERENCE)['tasks']
    for tier in (1, 2):
        lines += ['', f'## Tier {tier}', '',
                  '| 과제 | 지표(↑/↓) | 후보 점수 | Transformer 기준(3시드 평균) | Transformer 대비(×) | 0.8 통과 | GPU 시간(분) 후보/기준 | VRAM(MiB) 후보/기준 |',
                  '|---|---|---:|---:|---:|---|---:|---:|']
        for row in report['tasks']:
            if row['tier'] != tier:
                continue
            task = row['task']
            ref = reference[task]
            result = judged['tasks'][task]
            arrow = '↑' if ref['direction'] == 'maximize' else '↓'
            ratio = result['retention']
            threshold = {True: '통과', False: '미통과', None: '—'}[result['pass_0p8']]
            if smoke:
                score = f"smoke: 점수 없음 ({row['status']})"
                ref_score = '—'
            else:
                score, ref_score = number(row['mean']), number(ref['mean'])
            def pair(key):
                return f'{number(resources.get(task, {}).get(key))} / {number(baseline.get(task, {}).get(key))}'
            fields = (row['name'], f"{row.get('metric') or ref.get('metric', '—')} {arrow}",
                      score, ref_score, '—' if ratio is None else f'×{ratio:.2f}', threshold,
                      pair('gpu_time_min'), pair('peak_vram_mib'))
            lines.append('| ' + ' | '.join(fields) + ' |')
        if not any(row['tier'] == tier for row in report['tasks']):
            lines.append('| 실행 대상 없음 | — | — | — | — | — | — | — |')
    hardware = report.get('hardware') or {}
    devices = ', '.join(f"{gpu['name']} ({gpu['vram_mib']} MiB)" for gpu in hardware.get('gpus', []))
    lines += ['', '×1.00은 Transformer 기준 점수와 같습니다.',
              '0.80 미만이면 해당 과제는 미통과입니다.',
              '↓ 지표의 유지율은 Transformer 기준 점수 ÷ 후보 점수입니다.',
              '', '기준값 출처: `reference/transformer_reference.json`',
              f"실행 장치: {hardware.get('device', '기록 없음')} · GPU: {devices or '기록 없음'}",
              '—는 미측정 또는 해당 없음입니다.']
    return '\n'.join(lines) + '\n'


def write_result(run, explicit=None):
    run = run.resolve()
    report = read(run / 'report.json')
    judged = read(run / 'judged.json')
    resources = read(run / 'resources.json')
    baseline_path, baseline = load_baseline(run, report, explicit)
    path = run / 'result.md'
    path.write_text(render(report, judged, resources, baseline, baseline_path), encoding='utf-8')
    return path
