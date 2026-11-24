---
name: proxy-harness
description: Evaluate a causal mixer with evo-proxy and read separate Tier 1 and Tier 2 results.
---

Write a single candidate Python file, then run:

```sh
evo-proxy eval candidate.py --profile smoke --out runs/candidate
```

Read the output path printed by the command and open its `feedback.md`.
Smoke checks one update per task on CPU and provides no performance score.
Tier 1 tests synthetic capabilities. Tier 2 measures dataset performance.
Use tier1 or tier2 to isolate a tier, cascade to require the Tier 1 relaxed
gate before Tier 2, and full for all tasks. Those four scored profiles
run the frozen seed 0 workload and use CUDA. Keep comparisons within a tier.
