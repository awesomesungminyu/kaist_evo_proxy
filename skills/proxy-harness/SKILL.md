---
name: proxy-harness
description: Check and evaluate one causal mixer with evo-proxy, then stop.
---

The prompt may set the executable through `EVO_PROXY_BIN`; otherwise use
`evo-proxy` from PATH. Use the command supplied by the prompt.

Write one candidate Python file. Run the check command and
use only its printed contract errors when revising. Check at most three
distinct versions. If check passes, run the evaluation specified in the
request and then stop. Leave result.md and the JSON reports for the human.
Do not read evaluation output files or design another candidate from them.

Smoke runs one CPU update per task and provides no performance score.
Tier 1 tests synthetic capabilities. Tier 2 measures dataset performance.
The scored profiles run the frozen seed 0 CUDA workload. Keep comparisons
within a tier.
