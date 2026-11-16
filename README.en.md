# kaist_evo_proxy

[한국어](README.md) · English

This harness screens Transformer alternatives with inexpensive proxy tasks before large-scale training. It evaluates a candidate `CandidateMixer` with shared backbones, data, seeds, and training budgets, then reports task-level outcomes. EvoScientist can invoke the same evaluation through its shell tool and read the report to design a next candidate.

## Evaluation scope

| Tier | Scope | Purpose |
|---|---|---|
| 0 | Initial-state metrics without training | Preliminary screening |
| 1 | 8 synthetic tasks | Isolated capabilities; Transformer wins 4, loses 4 |
| 2 | 8 small real-data tasks | Real-data checks; Transformer wins 4, loses 4 |
| 3 | Large language models | Later external validation |

The runnable selection is the final 16 Tier 1 and Tier 2 tasks. Win/loss labels compare Transformer and LSTM over three seeds. Rankings over all nine architectures are incomplete for some tasks. * marks S5 confirmation for Speech Commands, † marks EMNIST as a reserve exceeding diversity capacity, and ‡ marks the [domain-priority rule](docs/PREREG_DOMAIN_PRIORITY.md) for Lipophilicity.

## The 16 tasks

| Task | Input | Metric (↑ higher, ↓ lower) | Data |
|---|---|---|---|
| [T1-R1-05 · MAD Compression](tasks/T1-R1-05/README.md) | Tokens | `token_accuracy` ↑ | Files: synthetic cache |
| [T1-R2-01 · Positional Histogram](tasks/T1-R2-01/README.md) | Tokens | `slot_accuracy` ↑ | Generated at runtime |
| [T1-R2-02 · String Matching](tasks/T1-R2-02/README.md) | Tokens | `accuracy` ↑ | Generated at runtime |
| [T1-R0-07 · RegBench](tasks/T1-R0-07/README.md) | Tokens | `next_token_acc` ↑ | Generated at runtime |
| [T1-R0-04 · Parity](tasks/T1-R0-04/README.md) | Tokens | `mean_best_val_accuracy` ↑ | Files |
| [T1-R0-05 · Tomita 5](tasks/T1-R0-05/README.md) | Tokens | `mean_best_val_accuracy` ↑ | Files |
| [T1-R2-04 · Cycle Navigation](tasks/T1-R2-04/README.md) | Tokens | `accuracy_id50_ex50` ↑ | Generated at runtime |
| [T1-R2-05 · Random Automaton](tasks/T1-R2-05/README.md) | Tokens | `last_state_accuracy_id50_ex50` ↑ | Generated at runtime |
| [T2-R1-11 · Permuted MNIST](tasks/T2-R1-11/README.md) | Image sequences | `accuracy` ↑ | Files |
| [T2-R3-05 · Permuted Kuzushiji-49](tasks/T2-R3-05/README.md) | Image sequences | `accuracy` ↑ | Files |
| [T2-R4-02 · Speech Commands (raw waveform)\*](tasks/T2-R4-02/README.md) | Continuous values | `accuracy` ↑ | Files |
| [T2-R3-02 · Permuted EMNIST (letters)†](tasks/T2-R3-02/README.md) | Image sequences | `accuracy` ↑ | Files |
| [T2-R1-04 · TAPE Stability](tasks/T2-R1-04/README.md) | Amino acid sequences | `spearman_valid` ↑ | Files |
| [T2-R1-09 · enwik8](tasks/T2-R1-09/README.md) | Bytes | `val_bpc` ↓ | Files |
| [T2-R1-08 · IMDB (byte-level)](tasks/T2-R1-08/README.md) | Bytes | `accuracy` ↑ | Files |
| [T2-R2-02 · Lipophilicity (SMILES)‡](tasks/T2-R2-02/README.md) | SMILES characters | `rmse_valid` ↓ | Files |


## Install and prepare data

Linux and Python 3.11 are recommended. Task listing and unit tests work on CPU; full evaluation needs a CUDA GPU.

```bash
git clone https://github.com/awesomesungminyu/kaist_evo_proxy.git
cd kaist_evo_proxy
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m validation list
```

Install the PyTorch build matching your CUDA environment. Prepare source files from the five bundles in the [data guide](docs/DATA.md). Five tasks generate inputs at runtime; 11 require files. The repository contains no datasets or checkpoints.

```bash
python -m validation prepare --source downloads/extracted --data-root data
python -m validation data --data-root data
CUDA_VISIBLE_DEVICES="" python -m unittest discover -s tests -v
```

## Evaluate a candidate architecture

Define `CandidateMixer(nn.Module)` in one Python file. Its constructor takes `(d_model, num_heads, l_max)` and `forward` maps `[B,T,D]` to `[B,T,D]`. Precheck checks causality, finite outputs and gradients, and the ±10% Transformer-block parameter rule. See the [example](examples/candidate_mixer.py) and [contract](docs/MODELS.md).

```bash
CANDIDATE="$PWD/examples/candidate_mixer.py"
OUT="$PWD/artifacts/example"
python -m validation precheck --mixer "$CANDIDATE:CandidateMixer" --data-root data --out "$OUT/precheck.json"
python -m validation suite --mixer "$CANDIDATE:CandidateMixer" --profile smoke --seeds 0 --out "$OUT" --data-root data --tfl-root third_party/tfl --device cpu --jobs 1 --timeout 240
python -m validation report --suite "$OUT"
```

`evaluate.sh` runs the three stages together. Set `EVO_WORK_ROOT`, `EVO_DATA_ROOT`, and `EVO_TFL_ROOT`; outputs stay under `EVO_WORK_ROOT`.

```bash
export EVO_WORK_ROOT="$PWD/.evo-work" EVO_DATA_ROOT="$PWD/data" EVO_TFL_ROOT="$PWD/third_party/tfl"
bash integrations/evoscientist/evaluate.sh "$CANDIDATE" "$EVO_WORK_ROOT/runs/example"
```

Smoke uses one optimizer update per task to check wiring and may take seconds to minutes per task on CPU. Full uses the fixed training budget and evaluation and may take minutes to hours per task on GPU. Actual time depends on the GPU and data. Smoke provides no performance ranking.

## EvoScientist and limitations

EvoScientist writes candidates, calls `evaluate.sh` through its shell tool, and reads `report.json`. See the [integration guide](docs/EVOSCIENTIST.md). Supply the endpoint and credential only through `CUSTOM_OPENAI_BASE_URL=<YOUR_OPENAI_COMPATIBLE_ENDPOINT>` and `CUSTOM_OPENAI_API_KEY`; install the framework separately.

Single-seed full scores are provisional. Four continuous-input tasks (T2-R1-11, T2-R3-05, T2-R4-02, T2-R3-02) showed run-to-run variation even with the same seed; small differences are not evidence of improvement. RegBench evaluates a repeatedly observed development stream. Selection and one-step checks do not establish architectural superiority.
