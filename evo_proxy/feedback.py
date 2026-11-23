"""Render measured outcomes for an agent without prescribing candidate changes."""
def make_feedback(report, judged, resources):
    def value(value):
        return 'unavailable' if value is None else f'{value:.5g}' if isinstance(value,float) else str(value)
    lines=['# Candidate feedback','','Profile: '+report['profile'],
           'Comparable performance: '+value(report['performance_comparable']),
           'Stop reason: '+value(judged['stop_reason']), 'Gate passed: '+value(judged['gate_passed']),'']
    for tier in ('tier1','tier2'):
        row=judged[tier]
        lines.append(f"- {tier}: strict={row['strict']}; relaxed={row['relaxed']}; "
                     f"pass_count={row['pass_count']}; fail_tasks={', '.join(row['fail_tasks']) or 'none'}")
    lines += ['', '| Task | Status | Retention | GPU min | Peak VRAM MiB | GPU % | CPU s |',
              '|---|---|---:|---:|---:|---:|---:|']
    for task,row in judged['tasks'].items():
        cost=resources.get(task,{})
        measures=[cost.get(k) for k in ('gpu_time_min','peak_vram_mib','gpu_util_pct','cpu_time_s')]
        lines.append('| '+' | '.join(map(value,[task,row['status'],row['retention'],*measures]))+' |')
    return '\n'.join(lines)+'\n'
