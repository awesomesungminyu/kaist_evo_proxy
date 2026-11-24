# EvoScientist integration

Install the workspace skills with `evo-proxy install-skills`. See the
[quickstart](../../README.en.md#quickstart) for a bounded single request.
The [example request](../../examples/research_request.md) asks the agent
to write the candidate immediately after reading the skills, run `evo-proxy
check` and `evo-proxy eval --profile smoke` from its shell, and read
`feedback.md` before writing a follow-up candidate. The launcher defaults
to 40 model calls and three distinct prechecked candidate revisions. It
forwards requests through a counted OpenAI-compatible gateway and saves
streamed events in the agent workspace.

A shell wrapper is also available as
`bash integrations/evoscientist/evaluate.sh candidate.py runs/candidate`.
