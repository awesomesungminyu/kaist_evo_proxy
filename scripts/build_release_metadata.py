"""Generate public metadata from the frozen task settings and archived results."""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean, median

GROUPS = {
    'memory-retrieval': ('T1-R1-05','T1-R2-02'),
    'rule-learning': ('T1-R0-07',), 'counting':('T1-R2-01',),
    'state-tracking': ('T1-R0-04','T1-R0-05','T1-R2-04','T1-R2-05'),
    'continuous-signal':('T2-R1-11','T2-R3-05','T2-R4-02','T2-R3-02'),
    'language-text':('T2-R1-09','T2-R1-08'),
    'biological-chemical':('T2-R1-04','T2-R2-02','promoters'),
    'music':('bach',),
}
TYPES = {'regression':('T2-R1-04','T2-R2-02'), 'next-step':('T1-R0-07','T2-R1-09','bach')}
PAPERS = {
    'transformer': 'Vaswani et al., Attention Is All You Need (2017)',
    'gqa': 'Ainslie et al., GQA (2023)',
    'linear_attention': 'Katharopoulos et al., Transformers are RNNs (2020)',
    'gla': 'Yang et al., Gated Linear Attention Transformers with Hardware-Efficient Training (2024)',
    'retnet': 'Sun et al., Retentive Network (2023)',
    'mamba': 'Gu and Dao, Mamba (2024)',
    's4d': 'Gu et al., On the Parameterization and Initialization of Diagonal State Space Models (2022)',
    'hyena': 'Poli et al., Hyena Hierarchy (2023)',
    'lstm': 'Hochreiter and Schmidhuber, Long Short-Term Memory (1997)',
}


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def table(rows):
    header='| ID | Task | Input | Metric | Data |\n|---|---|---|---|---|'
    return header+'\n'+'\n'.join(f"| {r['id']} | {r['name']} | {r['input']} | "
        f"{r['metric']} {'↑' if r['direction']=='maximize' else '↓'} | {r['data']} |" for r in rows)


def generate(harness, history, out):
    original=json.loads((harness/'validation/protocol.json').read_text())['tasks']
    extensions=json.loads((harness/'release_tasks/protocol.json').read_text())['tasks']
    q5=(history/'length_scaling_20261119/F0_followup.md').read_text().split('## Q5.',1)[1].split('## Q6.',1)[0]
    shapes={}
    for line in q5.splitlines():
        parts=[v.strip() for v in line.strip('|').split('|')]
        if parts[0] in original:
            shapes[parts[0]]=dict(zip(('l_max','d_model','n_layers','num_heads','batch_size'),map(int,parts[2:7])))
    inputs={t:'tokens' for t in original}
    inputs.update({t:'continuous sequence' for t in GROUPS['continuous-signal']})
    inputs.update({'T2-R1-04':'amino acid tokens','T2-R2-02':'SMILES tokens','T2-R1-09':'bytes','T2-R1-08':'bytes'})
    base_rows={r['task']:r for r in read(history/'sunday_20261122/S1_merged_reference.csv') if r['model']=='cs_transformer'}
    new_scores={}
    for r in read(history/'new_tasks_20261121/N_results.csv'):
        if r['model']=='transformer' and r['profile']=='full' and r['status']=='done':
            new_scores.setdefault(r['task'],[]).append(float(r['raw_score']))
    old_costs=read(history/'resource_eval_20261117/followup_v2/C_resources.csv')
    ordering={t:median(float(r['wall_seconds']) for r in old_costs if r['task']==t and r['status']=='done')
              for t in original if original[t]['tier']==1}
    rows=[]
    reference={}
    for t,spec in (original|extensions).items():
        shape=shapes.get(t) or dict(d_model=spec['d_model'],n_layers=spec['layers'],num_heads=spec['heads'],
                                  l_max=spec['length'],batch_size=spec['batch'])
        rows.append(dict(id=t,name=spec['name'].rstrip('*'),tier=spec['tier'],direction=spec['direction'],
            metric=spec['metric'],group=next(group for group,tasks in GROUPS.items() if t in tasks),
            type=next((type_ for type_,tasks in TYPES.items() if t in tasks),'classification'),
            data='file' if spec['assets'] else 'generated',input=inputs[t] if t in inputs else spec['input'],model=shape))
        values=([float(base_rows[t][f'seed_{i}']) for i in range(3)] if t in base_rows else new_scores[t])
        assert len(values)==3
        average=mean(values)
        reference[t]=dict(metric=spec['metric'],direction=spec['direction'],mean=average,
                          threshold=average*.8 if spec['direction']=='maximize' else average/.8)
    rows.sort(key=lambda r:(r['tier'],r['id'] in ('T1-R0-04','T1-R0-05'),ordering.get(r['id'],0)))
    assert len(rows)==len({r['id'] for r in rows})==18
    (out/'tasks/tasks.json').write_text(json.dumps({'tasks':rows},ensure_ascii=False,indent=2)+'\n')
    for i in (1,2):
        (out/f'tasks/tier{i}.md').write_text(f'# Tier {i}\n\n'+table([r for r in rows if r['tier']==i])+'\n')
    (out/'reference/transformer_reference.json').write_text(json.dumps({'retention_threshold':.8,'n_seeds':3,'tasks':reference},indent=2)+'\n')
    labels={'통과':'pass','미달':'fail','미확인':'unknown'}
    lines=['# Baseline 1× verdicts','','| Mixer | Tier 1 | Tier 2 | Strict | Relaxed |','|---|---:|---:|---|---|']
    for r in read(history/'fill_20261122/F_results.csv'):
        if float(r['scale'])==1:
            lines.append(f"| {r['model'].removeprefix('cs_')} | {r['tier1_passed']}/8 | {r['tier2_10_passed']}/10 | "
                         f"{labels[r['overall_10_strict']]} | {labels[r['overall_10_relaxed']]} |")
    (out/'reference/baseline_verdict.md').write_text('\n'.join(lines)+'\n')
    params={r['model'].removeprefix('cs_'):int(r['block_params'])//int(r['n_blocks'])
            for r in read(history/'resource_eval_20261117/parameters.csv') if r['task']=='T1-R1-05'}
    lines=['# Baseline mixers','','The default MAD block has width 128, two layers and four heads.',
           '', '| Mixer | Reference | Params per block | Implementation |','|---|---|---:|---|']
    notes={'mamba':'Frozen token loop','retnet':'FLA CUDA path; PyTorch reference for CPU'}
    for m,paper in PAPERS.items():
        lines.append(f"| {m} | {paper} | {params[m]:,} | {notes.get(m,'Frozen harness')} |")
    (out/'baselines/README.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('harness','history','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    generate(args.harness,args.history,args.out)
