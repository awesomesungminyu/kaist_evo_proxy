"""Format frozen precheck results and replay failed CPU probes for diagnostics."""
from collections import defaultdict
import re


def bounds(reference):
    return (9 * reference + 9) // 10, 11 * reference // 10


def format_precheck(official, extra):
    tasks = official.get('tasks', {}) | extra
    groups = defaultdict(list)
    for task, row in tasks.items():
        cfg = row.get('configuration', {})
        if 'transformer_block_parameters' in row:
            key = (cfg['d_model'], cfg['n_layers'], cfg['num_heads'],
                   row['block_parameters'], row['transformer_block_parameters'])
            groups[key].append(task)
    lines = ['## Precheck', '', f"Status: {official.get('status', 'unavailable')}"
             f" (extensions: {'passed' if extra and all(r['passed'] for r in extra.values()) else 'failed or unavailable'})", '']
    if groups:
        lines += ['| Configuration (width/layers/heads) | Tasks | Current block params | Allowed (Transformer ±10%) | Transformer block params |',
                  '|---|---|---:|---:|---:|']
    for (d, layers, heads, actual, ref), ids in groups.items():
        low, high = bounds(ref)
        lines.append(f"| {d}/{layers}/{heads} | {', '.join(ids)} | {actual:,} | {low:,}–{high:,} | {ref:,} |")
    lines += ['', '### Failed checks', '']
    if official.get('error'):
        lines.append(f"- {official['error']}")
    if not extra:
        lines.append('- Extension precheck produced no results. See precheck_extension.log.')
    for (d, layers, heads, actual, ref), ids in groups.items():
        if any(tasks[task].get('checks', {}).get('parameter_budget') is False for task in ids):
            lo, hi = bounds(ref)
            lines.append(f'- {d}/{layers}/{heads} · parameter_budget: current {actual:,}; '
                         f'allowed {lo:,}–{hi:,} (Transformer {ref:,} ±10%)')
    for task, row in tasks.items():
        if row.get('error'):
            lines.append(f"- {task}: {row['error']}")
        for name, passed in row.get('checks', {}).items():
            if passed or name == 'parameter_budget':
                continue
            detail = row.get('diagnostics', {}).get(name)
            if name == 'gpu_max_length_finite':
                peak = row.get('gpu', {}).get('peak_bytes')
                amount = f'{peak:,} bytes' if peak is not None else 'unavailable'
                detail = f'finite output/gradients = false; requires true; GPU peak = {amount}; no fixed memory threshold'
            lines.append(f"- {task} · {name}: {detail or 'observed false; requires true; numeric diagnostic unavailable'}")
    measured = [r['gpu']['peak_bytes'] for r in tasks.values()
                if r.get('gpu', {}).get('peak_bytes') is not None]
    gpu = f'maximum observed peak {max(measured):,} bytes' if measured else 'peak bytes unavailable'
    lines += ['', f'GPU precheck: {gpu}; no fixed memory threshold.', '']
    return '\n'.join(lines)


def replay(candidate, config, failures):
    """Replay the frozen CPU input seeds for failed checks only; never gate a run."""
    import torch

    torch.manual_seed(0)
    d, heads, max_len = (config[k] for k in ('d_model', 'num_heads', 'l_max'))
    mixer = candidate(d_model=d, num_heads=heads, l_max=max_len).cpu()
    # The frozen precheck constructs its reference before entering the probes.
    from proxy_tasks.common_set.mixers import CausalSelfAttention
    CausalSelfAttention(d, heads)
    diagnostics = {}
    for mode in ['eval', 'train']:
        getattr(mixer, mode)()
        for length in sorted({min(17, max_len), min(41, max_len)}):
            prefix = f'{mode}_{length}'
            torch.manual_seed(length)
            x = torch.randn(2, length, d, requires_grad=True)
            y = mixer(x)
            shape = tuple(y.shape)
            if prefix+'_shape' in failures:
                diagnostics[prefix+'_shape'] = f'observed {shape}; required {tuple(x.shape)}'
            nonfinite = int((~torch.isfinite(y)).sum())
            if prefix+'_finite' in failures:
                diagnostics[prefix+'_finite'] = f'{nonfinite} nonfinite output values; allowed 0'
            if shape != tuple(x.shape) or nonfinite:
                continue
            mixer.zero_grad(set_to_none=True)
            y.square().mean().backward()
            grads = [p.grad for p in mixer.parameters() if p.requires_grad and p.grad is not None]
            if prefix+'_backward' in failures:
                bad = sum(int((~torch.isfinite(g)).sum()) for g in [*grads, x.grad] if g is not None)
                diagnostics[prefix+'_backward'] = (
                    f'{len(grads)} parameter gradient tensors; required ≥1; '
                    f'input gradient present = {x.grad is not None}; requires true; {bad} nonfinite values; allowed 0')
            for cut in [1, length // 2, length - 1]:
                changed = x.detach().clone()
                changed[:, cut:] = torch.randn_like(changed[:, cut:]) * 7
                with torch.no_grad():
                    torch.manual_seed(123)
                    a = mixer(x.detach())[:, :cut]
                    torch.manual_seed(123)
                    b = mixer(changed)[:, :cut]
                check = f'{prefix}_causal_{cut}'
                if check in failures:
                    delta = (a-b).abs()
                    limit = 1e-5 + 1e-5*b.abs()
                    diagnostics[check] = (f'{int((delta > limit).sum())} prefix values over tolerance; allowed 0; '
                                          f'max |Δ|={float(delta.max()):.6g}; atol=1e-5, rtol=1e-5')
    return diagnostics


def main():
    import argparse
    from pathlib import Path
    from .harness import read, save
    from proxy_tasks.common_set.plugins import load
    import torch

    parser = argparse.ArgumentParser()
    parser.add_argument('mixer')
    parser.add_argument('precheck', type=Path)
    parser.add_argument('extra', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    torch.set_num_threads(1)
    matcher = re.compile(r'_(?:shape|finite|backward|causal_\d+)$')
    cls = load(args.mixer)
    cached, results = {}, {}
    for task,row in (read(args.precheck).get('tasks',{}) | read(args.extra)).items():
        failures = tuple(name for name, ok in row.get('checks',{}).items() if not ok and matcher.search(name))
        if not failures:
            continue
        key = tuple(sorted(row['configuration'].items())), failures
        if key not in cached:
            try:
                cached[key] = replay(cls, row['configuration'], failures)
            except Exception:
                cached[key] = {}
        results[task] = cached[key]
    save(args.out,results)


if __name__ == '__main__':
    main()
