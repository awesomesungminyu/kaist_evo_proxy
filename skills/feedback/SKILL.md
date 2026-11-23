---
name: feedback
description: Interpret evo-proxy retention, tier verdicts and resource observations from feedback.md.
---

Read task status, retention, and tier strict and relaxed verdicts separately.
Retention uses the 1× Transformer's three-seed mean. Accuracy-like metrics
use candidate/reference. Loss-like metrics use reference/candidate.
A known retention of at least 0.8 passes a task. Missing scores and smoke
results give no performance evidence.

Compare measured GPU minutes and peak VRAM only under matched settings.
Treat CPU time, GPU utilization and unavailable fields separately.
Use observations from the output to justify the next candidate in your own words.
