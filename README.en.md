# kaist_evo_proxy

[한국어](README.md) · English

Evaluate Transformer alternatives on 18 small proxy tasks. Check a mixer on CPU, record retention and costs by tier, and return feedback to EvoScientist.

## Quickstart
Use Linux and Python 3.11. For CPU-only smoke, run `export EVO_PROXY_CPU=1` before setup.


```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
evo-proxy setup
```

Extract the data archives from the [Drive checklist](drive_upload_20261123/README.md) into one `incoming/` folder.

```bash
evo-proxy data --source incoming
evo-proxy doctor --core
evo-proxy eval examples/candidate_mixer.py --profile smoke --out runs/example
evo-proxy baseline transformer --profile smoke --out runs/transformer
pip install EvoScientist==0.4.1
export EVOSCIENTIST_WORKSPACE_DIR="$PWD/.evo-work"
evo-proxy install-skills
evo-proxy doctor
```

Put `CUSTOM_OPENAI_API_KEY` and `CUSTOM_OPENAI_BASE_URL` in a local `.env` and replace `YOUR_MODEL` with the provider model ID.

```bash
python integrations/evoscientist/run_agent.py --workspace .evo-work \
  --prompt examples/research_request.md --env-file .env --model YOUR_MODEL
```

## EvoScientist loop

Read skills → write candidate → `evo-proxy eval` → read `feedback.md` → next candidate

## Profiles

| Profile | Tasks | Typical planning window | Use |
|---|---|---|---|
| smoke | All 18, one CPU update per task | Minutes | Check wiring and finiteness |
| tier1 | 8 synthetic tasks | Minutes to under an hour | Isolate sequence capabilities |
| tier2 | 10 dataset tasks | Minutes to under an hour | Measure dataset performance |
| cascade | Tier 1, then Tier 2 on a relaxed pass | Up to a full run | Stop after the second measured Tier 1 miss |
| full | All 18, seed 0 on CUDA | Tens of minutes or more | Collect a comparable score for each task |

## Tasks

### Tier 1

| ID | Task | Input | Metric | Data |
|---|---|---|---|---|
| T1-R1-05 | MAD Compression | tokens | token_accuracy ↑ | file |
| T1-R0-07 | RegBench | tokens | next_token_acc ↑ | generated |
| T1-R2-02 | String Matching | tokens | accuracy ↑ | generated |
| T1-R2-01 | Positional Histogram | tokens | slot_accuracy ↑ | generated |
| T1-R2-05 | Random Automaton | tokens | last_state_accuracy_id50_ex50 ↑ | generated |
| T1-R2-04 | Cycle Navigation | tokens | accuracy_id50_ex50 ↑ | generated |
| T1-R0-04 | Parity | tokens | mean_best_val_accuracy ↑ | file |
| T1-R0-05 | Tomita 5 | tokens | mean_best_val_accuracy ↑ | file |

### Tier 2

| ID | Task | Input | Metric | Data |
|---|---|---|---|---|
| T2-R1-11 | Permuted MNIST | continuous sequence | accuracy ↑ | file |
| T2-R3-05 | Permuted Kuzushiji-49 | continuous sequence | accuracy ↑ | file |
| T2-R4-02 | Speech Commands (raw waveform) | continuous sequence | accuracy ↑ | file |
| T2-R3-02 | Permuted EMNIST (letters) | continuous sequence | accuracy ↑ | file |
| T2-R1-04 | TAPE Stability | amino acid tokens | spearman_valid ↑ | file |
| T2-R1-09 | enwik8 | bytes | val_bpc ↓ | file |
| T2-R1-08 | IMDB (byte-level) | bytes | accuracy ↑ | file |
| T2-R2-02 | Lipophilicity (SMILES) | SMILES tokens | rmse_valid ↓ | file |
| promoters | Human non-TATA promoter classification | ACGTN IDs, 0 padding | accuracy ↑ | file |
| bach | DCMLab Bach chorales | 128 MIDI-pitch binary flags per sixteenth note | NLL (nats per next frame) ↓ | file |

## Judging

Retention compares with the 1× Transformer three-seed mean. Divide candidate by reference for maximize metrics and reference by candidate for minimize metrics. The task threshold is 0.8. Strict requires 8/8 and 10/10; relaxed requires 7/8 and 9/10. Smoke leaves performance scores and retention empty.

[Transformer reference](reference/transformer_reference.json) · [Baseline verdicts](reference/baseline_verdict.md)

## Candidates and baselines

Copy the example, implement `CandidateMixer(d_model, num_heads, l_max)`, and verify it with `evo-proxy check candidate.py`. Run `evo-proxy baseline NAME --profile smoke` for a stock mixer.

[Candidate example](examples/candidate_mixer.py) · [Baseline mixers](baselines/README.md) · [Excluded tasks](tasks/excluded.md)

## Limits

Resource measurements use serial seed 0 training. Mamba uses the frozen loop implementation. The release leaves learning rates fixed and does not validate concurrent speedup or seed-to-seed cost variation. Candidate Python is imported directly; only evaluate trusted source.

An existing output directory receives a new child run. Each evaluation writes `report.json`, `judged.json`, `resources.json`, and `feedback.md`.
