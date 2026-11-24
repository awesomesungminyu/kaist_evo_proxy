Connection check / 연결 확인용: one CPU smoke task.

File tools start at this workspace's virtual /. Shell commands already run
in this workspace. The evo-proxy command and prepared data are ready.

First read /skills/proxy-harness/SKILL.md and /skills/mixer-contract/SKILL.md
in one group. Then write /runs/kep_smoke/candidate_mixer.py immediately. Implement only
CandidateMixer, without a second MLP, normalization, or residual block.
A suitable initial design uses bias-free d→3d QKV and d→d output projections
with causal SDPA. Keep the frozen parameter and causality checks.

Run exactly:
evo-proxy check ./runs/kep_smoke/candidate_mixer.py --out ./runs/kep_smoke/check

If check fails, revise only in response to the contract errors printed by
check. Use at most three distinct candidate versions in total. On a third
failure, stop. After check passes, run exactly:
evo-proxy eval ./runs/kep_smoke/candidate_mixer.py --profile smoke --task T1-R1-05 --out ./runs/kep_smoke/eval

Wait for the eval command to finish. When EVALUATION_COMPLETE appears, immediately reply DONE and end the task.
Do not call any further tool or read any file after eval.
Do not open result.md, report.json,
judged.json, or resources.json. Do not write a follow-up candidate, interpret
the evaluation, or use its results for a new design. The human reads the
result. Do not use directory discovery or web search.
