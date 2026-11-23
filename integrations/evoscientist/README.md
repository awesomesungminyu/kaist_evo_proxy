# EvoScientist integration

Install the workspace skills with `evo-proxy install-skills`. See the
[quickstart](../../README.en.md#quickstart) for a bounded single request.
The agent calls `evo-proxy eval` directly from its shell. The launcher
forwards requests through a counted OpenAI-compatible gateway and writes
streamed evidence to the agent workspace.

A shell wrapper is also available as
`bash integrations/evoscientist/evaluate.sh candidate.py runs/candidate`.
