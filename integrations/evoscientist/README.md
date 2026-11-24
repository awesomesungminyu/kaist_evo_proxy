# EvoScientist integration

Use the [quickstart](../../README.en.md#quickstart) to install the two
workspace skills and run the [example request](../../examples/research_request.md).
EvoScientist writes a candidate, calls `evo-proxy check`, and may revise it
using the printed contract errors. After a passing check it calls
`evo-proxy eval` once and stops. A human opens the resulting `result.md`.

The launcher allows up to three distinct prechecked candidate versions
and 40 model calls by default. It uses a counted OpenAI-compatible gateway
and saves streamed events in the workspace.

The shell wrapper is also available as
`bash integrations/evoscientist/evaluate.sh candidate.py runs/candidate`.
