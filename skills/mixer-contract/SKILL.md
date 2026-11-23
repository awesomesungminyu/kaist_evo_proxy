---
name: mixer-contract
description: Implement and precheck a parameter-matched causal PyTorch mixer for the proxy evaluator.
---

Define `CandidateMixer(d_model, num_heads, l_max)` as a torch module.
Its forward maps float32 `[batch, time, width]` to the same shape. Prefix
outputs must remain unchanged when a suffix changes, and gradients must be
finite on CPU. Use vectorized tensor operations over time. Do not implement
a time-axis Python loop.

The parameter tolerance is ±10% of the **Transformer block**, including
identical normalization and MLP. Use `evo-proxy check candidate.py` to
verify each configured shape. Leave data, optimizer, training steps and
seeds as defined by the harness.
