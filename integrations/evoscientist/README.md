# EvoScientist shell integration

This directory supplies an evaluation adapter and an optional agent-led launcher. EvoScientist itself is installed separately from [its upstream project](https://github.com/EvoScientist/EvoScientist). No laboratory framework source or local run transcript is included here.

`evaluate.sh` accepts a `CandidateMixer` Python file and an output folder under `EVO_WORK_ROOT`. It runs precheck, suite and report. In full mode it waits for an idle GPU, retries incomplete cells using the same output folder, and preserves completed cells. It uses `EVO_DATA_ROOT`, `EVO_TFL_ROOT`, and optional `EVO_ML_PYTHON`; no machine-specific path is embedded.

`run_agent.py` launches EvoScientist with its virtual workspace and a counted local model gateway. The agent must write candidates and call `./evaluate.sh` with its shell tool. The launcher reads `CUSTOM_OPENAI_BASE_URL` and `CUSTOM_OPENAI_API_KEY` only from the environment. An explicit HTTPS `/v1` endpoint is required. `--model`, `--llm-cap`, `--max-minutes`, `--max-generations`, and `--max-candidates` bound the run. Gateway request and response transcripts are written only to the run output folder; do not publish that folder.

`adapter.py` also provides a deterministic offline fixture for connection tests. Its mock candidates reuse the included Transformer example. Mock generation is not architecture discovery. `verify_agent_run_v2.py` checks agent-led evidence; `llm_call_usage.py` summarizes counted calls. See [the setup guide](../../docs/EVOSCIENTIST.md) and [candidate contract](../../docs/MODELS.md).
