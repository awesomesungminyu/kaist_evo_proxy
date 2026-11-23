Read /skills/proxy-harness/SKILL.md, /skills/mixer-contract/SKILL.md and
/skills/feedback/SKILL.md with read_file. The file-tool root is this workspace.
Use the exact relative shell commands below without changing directories.

Write a single causal vectorized CandidateMixer to /candidate.py. Use the
same ±10% block threshold and keep the datasets, seeds and budgets fixed.
If using dense attention, the reference mixer has exactly four bias-free
width-by-width projections in total.

```sh
evo-proxy check candidate.py --out runs/check
```

When check returns nonzero, read the indicated feedback.md before rewriting
the candidate. Use at most three distinct prechecked revisions in total.
When check passes, invoke the evaluation yourself:

```sh
evo-proxy eval candidate.py --profile smoke --out runs/candidate
```

Read that run's feedback.md with read_file. Then write /candidate_next.py
and /feedback_evidence.md. Cite the feedback path, two values read from it,
and a specific change in candidate_next.py based on those observations.
Smoke does not measure performance. Stop after the two follow-up files.
