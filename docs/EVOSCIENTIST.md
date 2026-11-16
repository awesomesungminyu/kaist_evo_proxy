# EvoScientist integration

The agent-led path asks EvoScientist to write a candidate, call the shell evaluation adapter, read `report.json`, and use measured full results in its next proposal. The launcher is `integrations/evoscientist/run_agent.py`; it starts EvoScientist but does not evaluate candidates on the agent's behalf. The framework must be installed separately. This source copy includes the adapter, not a bundled EvoScientist engine.

Set `EVO_WORK_ROOT` to a writable run folder, `EVO_DATA_ROOT` to the prepared task data, and `EVO_TFL_ROOT` to the TFL checkout. Install the EvoSci executable inside `EVO_WORK_ROOT/venv/bin/EvoSci` or pass `--evosci` pointing to a file inside that root. Supply `CUSTOM_OPENAI_BASE_URL=<YOUR_OPENAI_COMPATIBLE_ENDPOINT>` (an HTTPS `/v1` URL), `CUSTOM_OPENAI_API_KEY`, and `EVO_MODEL` through the environment. The launcher does not read a credentials file. It forwards model calls through a local counted gateway, with a call cap and no redirects.

Prepare `<out>/workspace/skills/proxy-task-bench/SKILL.md`, `<out>/workspace/evaluate.sh`, and a prompt inside `<out>/workspace/`. The EvoScientist file tool sees its virtual workspace; shell commands use relative paths. The agent prompt should direct candidates to `candidates/genN/*.py`, run `./evaluate.sh` one candidate at a time, read `runs/*/report.json`, and cite measured fields when proposing the next generation. See [prompt_template.md](../integrations/evoscientist/prompt_template.md) and [candidate contract](MODELS.md).

```bash
export EVO_WORK_ROOT="$PWD/.evo-work" EVO_DATA_ROOT="$PWD/data" EVO_TFL_ROOT="$PWD/third_party/tfl"
export CUSTOM_OPENAI_BASE_URL="<YOUR_OPENAI_COMPATIBLE_ENDPOINT>" CUSTOM_OPENAI_API_KEY="<YOUR_KEY>"
export EVO_MODEL="<YOUR_MODEL_ID>"
python integrations/evoscientist/run_agent.py --out "$EVO_WORK_ROOT/run1" \
  --prompt "$EVO_WORK_ROOT/run1/workspace/prompts/request.md" --profile smoke \
  --max-minutes 90 --max-generations 2 --max-candidates 2 --llm-cap 30
```

The workspace `evaluate.sh` should be a copy of [the adapter](../integrations/evoscientist/evaluate.sh). It runs precheck, suite and report with the frozen task protocol. `smoke` uses one optimizer update and has no comparable score. `full` uses the fixed learning budgets; completed cells can be reused with the same output folder and identity. One-seed full scores remain provisional. Four continuous-input tasks (T2-R1-11, T2-R3-05, T2-R4-02, T2-R3-02) vary across repeated runs with the same seed, so small differences should not drive a proposal.

`report.json` contains task `mean`, `normalized_score`, `rank`, failure and timeout details when measured full cells complete. Missing cells are never scores of zero. The historical reference baseline is `validation/baselines/final16_v4.json`; it has incomplete nine-architecture three-seed coverage on some tasks.
