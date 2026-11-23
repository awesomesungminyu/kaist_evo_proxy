"""Direction-aware thresholds with explicit unknown and skipped tasks."""
from .harness import ROOT, read

THRESHOLD = .8
REFERENCE = ROOT/'reference'/'transformer_reference.json'


def compare(score, reference):
    if score is None:
        return None
    lhs, rhs = ((score,reference['mean']) if reference['direction']=='maximize'
                else (reference['mean'],score))
    if rhs == 0:
        return None
    return lhs/rhs


def tier_verdict(ids, ratios, attempted):
    fail = [t for t in ids if ratios.get(t) is not None and ratios[t] < THRESHOLD]
    count = sum(ratios.get(t) is not None and ratios[t]>=THRESHOLD for t in ids)
    missing = sum(ratios.get(t) is None for t in ids)
    viewed = [t for t in ids if t in attempted]
    def verdict(limit):
        if not viewed:
            return 'not_run'
        if count >= limit:
            return 'pass'
        if count + missing < limit:
            return 'fail'
        return 'unknown'
    return dict(tasks_run=viewed, pass_count=count, fail_tasks=fail, unknown_count=missing,
                strict=verdict(len(ids)),relaxed=verdict(len(ids)-1))


def judge(report,tasks):
    reference = read(REFERENCE)['tasks']
    rows = {}
    for item in report['tasks']:
        task = item['task']
        value = compare(item.get('mean'),reference[task]) if report['performance_comparable'] else None
        rows[task] = dict(retention=value,pass_0p8=value >= THRESHOLD if value is not None else None,
                          status=item['status'])
    ratios = {task:value['retention'] for task,value in rows.items()}
    attempted = {t for t,row in rows.items() if row['status']!='not_run'}
    return dict(profile=report['profile'],performance_comparable=report['performance_comparable'],
                threshold=THRESHOLD,tasks=rows,gate_passed=report.get('gate_passed'),
                stop_reason=report.get('stop_reason'),**{
                    f'tier{i}':tier_verdict([t['id'] for t in tasks if t['tier']==i],ratios,attempted)
                    for i in (1,2)})
