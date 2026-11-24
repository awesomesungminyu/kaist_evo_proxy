# kaist_evo_proxy

[한국어](README.md) · English

This tool compares new sequence architectures proposed by EvoScientist against Transformer on 18 small tasks and writes a result table for you to review.

## At a glance

EvoScientist writes a candidate → `evo-proxy check` (contract) → `evo-proxy eval` (train and score) → `result.md` (human review)

## Quickstart

Use Linux and Python 3.11. The CPU quickstart used about 5 GB of disk. Scored modes require a CUDA GPU. Our validation hardware is a TITAN RTX with 24 GB. This walkthrough runs one CPU smoke task, MAD. First-time installation and slower networks can push it past five minutes.

Get the code with `git clone`. Skip the Release page’s **Source code (zip/tar.gz)** files. The commands below fetch the data from the Release.

```bash
export PIP_DEFAULT_TIMEOUT=120  # 느린 네트워크에서 설치 끊김 방지
git clone https://github.com/awesomesungminyu/kaist_evo_proxy.git && cd kaist_evo_proxy  # Get the code and enter its directory
python3.11 -m venv .venv  # Create a Python environment
source .venv/bin/activate  # Activate the environment
pip install -e .  # Install the evo-proxy command
export EVO_PROXY_CPU=1  # Use CPU-only setup for this smoke test
evo-proxy setup  # Install the pinned harness and dependencies
evo-proxy data --download  # Download and prepare the single data bundle
evo-proxy doctor --core  # Check the evaluator and all 18 tasks
evo-proxy baseline transformer --profile smoke --task T1-R1-05 --out runs/baseline  # Run the MAD Transformer baseline
evo-proxy eval examples/candidate_mixer.py --profile smoke --task T1-R1-05 --out runs/example  # Evaluate the example and write its result table
```

### What success looks like

Excerpt from `evo-proxy doctor --core`. The EvoScientist and skill checks may say `false` until you install them.

```json
{
  "pinned_harness": true,
  "formal": true,
  "retnet": true,
  "data_18": true,
  "torch": true,
  "cuda": "not required (CPU setup)",
  "nvidia_smi": true,
  "evoscientist_0_4_1": false,
  "workspace_skills": true
}
```

Evaluation creates `result.md`, `report.json`, `judged.json`, and `resources.json` in `runs/example/`. Task logs are in `observations/`. If the output directory already exists, open the new run directory printed by the command.

Excerpt from `result.md`.

```text
Tier 1: 0/8 통과 (strict 미확인, relaxed 미확인)
Tier 2: 0/10 통과 (strict 미실행, relaxed 미실행)
자원: Transformer 대비 GPU 시간 —, 최대 VRAM —, 파라미터(블록) ×1.00
```

### Connect EvoScientist

1. Set up the lab EvoScientist and the harness in separate environments.
2. Install two skills in the harness workspace and generate the one-shot prompt.
3. Run EvoScientist with workspace isolation and review `result.md` yourself.

[Lab setup and the standalone launcher](docs/EVOSCIENTIST_SETUP.md#english)

## Two ways to use it

| Use case | Start here |
|---|---|
| Evaluation only | Run `evo-proxy check` and `evo-proxy eval` on your candidate. |
| Automatic candidate generation | Follow the lab setup to write and evaluate one candidate. |

## Read the results

| File | Contents |
|---|---|
| `result.md` | Human-readable scores and Transformer comparisons |
| `report.json` | Profile, raw scores, and per-task run status |
| `judged.json` | Retention and pass thresholds by task and tier |
| `resources.json` | Time, memory, and parameters observed for the run |

If reference accuracy is 0.90 and the candidate scores 0.72, retention is `0.72 ÷ 0.90 = 0.80`, a pass. For a metric where lower is better, divide in the other direction. A reference loss of 2.0 and candidate loss of 2.5 also give `2.0 ÷ 2.5 = 0.80`. Seven passes and one miss in Tier 1 fail strict and pass relaxed.

Use `--baseline-run runs/baseline` to choose the resource comparison, or let the CLI find the latest Transformer run of the same profile under `runs/`. GPU time and VRAM show `—` in CPU smoke. Use `evo-proxy report runs/example` to rebuild the table.

## Profiles

| Profile | Tasks | Planning estimate | When to use it |
|---|---|---|---|
| `smoke` | Defaults to all 18, one CPU update per task. Select one with `--task` | Seconds for MAD, minutes for the suite | Check installation and execution |
| `tier1` | Eight Tier 1 tasks on CUDA | Minutes to an hour or longer | Compare isolated capabilities |
| `tier2` | Ten Tier 2 tasks on CUDA | Minutes to an hour or longer | Compare on real data |
| `cascade` | Start with Tier 1. Stop early after two measured misses below 0.8. Run Tier 2 once seven Tier 1 passes are confirmed | Part of Tier 1 up to a full run | Spend Tier 2 time on candidates clearing the Tier 1 gate |
| `full` | All 18 on CUDA | Tens of minutes or longer | Collect comparable scores across the suite |

Times are planning estimates. Scored modes use the frozen seed 0 workload. Cascade skips Tier 2 if failures or missing results leave fewer than seven confirmed Tier 1 passes.

## Tasks

### Tier 1

Synthetic tasks that isolate one capability at a time.

| ID | Task | Input | Metric | Data | Capability |
|---|---|---|---|---|---|
| T1-R1-05 | MAD Compression | tokens | token_accuracy ↑ | file | Memory and retrieval |
| T1-R0-07 | RegBench | tokens | next_token_acc ↑ | generated | Rule learning |
| T1-R2-02 | String Matching | tokens | accuracy ↑ | generated | Memory and retrieval |
| T1-R2-01 | Positional Histogram | tokens | slot_accuracy ↑ | generated | Counting |
| T1-R2-05 | Random Automaton | tokens | last_state_accuracy_id50_ex50 ↑ | generated | State tracking |
| T1-R2-04 | Cycle Navigation | tokens | accuracy_id50_ex50 ↑ | generated | State tracking |
| T1-R0-04 | Parity | tokens | mean_best_val_accuracy ↑ | file | State tracking |
| T1-R0-05 | Tomita 5 | tokens | mean_best_val_accuracy ↑ | file | State tracking |

### Tier 2

Tasks drawn from real datasets.

| ID | Task | Input | Metric | Data | Data type |
|---|---|---|---|---|---|
| T2-R1-11 | Permuted MNIST | continuous sequence | accuracy ↑ | file | Continuous signals |
| T2-R3-05 | Permuted Kuzushiji-49 | continuous sequence | accuracy ↑ | file | Continuous signals |
| T2-R4-02 | Speech Commands (raw waveform) | continuous sequence | accuracy ↑ | file | Continuous signals |
| T2-R3-02 | Permuted EMNIST (letters) | continuous sequence | accuracy ↑ | file | Continuous signals |
| T2-R1-04 | TAPE Stability | amino acid tokens | spearman_valid ↑ | file | Biological and chemical sequences |
| T2-R1-09 | enwik8 | bytes | val_bpc ↓ | file | Language and text |
| T2-R1-08 | IMDB (byte-level) | bytes | accuracy ↑ | file | Language and text |
| T2-R2-02 | Lipophilicity (SMILES) | SMILES tokens | rmse_valid ↓ | file | Biological and chemical sequences |
| promoters | Genomics (Human non-TATA promoters) | ACGTN IDs, 0 padding | accuracy ↑ | file | Biological and chemical sequences |
| bach | Bach Chorales | 128 MIDI-pitch binary flags per sixteenth note | NLL (nats per next frame) ↓ | file | Music |

## Judging and reference values

Retention uses the 1× Transformer three-seed mean. The pass threshold is 0.8. Strict requires 8/8 and 10/10, and relaxed requires 7/8 and 9/10. Smoke leaves performance scores and retention empty.

[Transformer reference](reference/transformer_reference.json) · [Baseline verdicts](reference/baseline_verdict.md) · [Baseline mixers](baselines/README.md) · [Excluded tasks](tasks/excluded.md)

## Data

By default `evo-proxy data --download` fetches one file, about 882 MB, from the [Release](https://github.com/awesomesungminyu/kaist_evo_proxy/releases/tag/data-20261124). Download, verification, and preparation took 90 seconds in this CPU quickstart. Your network may be slower.

For manual setup, get `proxy-task-bench-data_20261124.tar` from the Release and run `evo-proxy data --source proxy-task-bench-data_20261124.tar`.

[Drive](https://drive.google.com/drive/folders/1SceShb6mBJXSaWDNzq6VrOgVajY-4ru0?usp=sharing) is the automatic fallback mirror if the Release download or verification fails. [Data licenses and sources](DATA_LICENSES.md)

## Troubleshooting

| Symptom | What to do |
|---|---|
| Release download fails | The command tries Drive automatically. If both fail, use the manual link printed by the command. |
| Restricted internet | Transfer the Release TAR from a connected machine and use `evo-proxy data --source path/to/file.tar`. Harness setup also needs network access. |
| Torch or CUDA error | Check `torch` and `cuda` in `evo-proxy doctor --core`. Torch 2.5.1 is required. Use a CUDA build compatible with your GPU driver for scored runs. Set `EVO_PROXY_CPU=1` before setup for CPU smoke. |
| `data_18: false` | Rerun `evo-proxy data --download` and look for missing tasks. Preparing a subset with `--tasks` leaves the all-data check false. |
| GPU out of memory | Check `observations/<ID>/process.log`, then try again when other GPU jobs are done. CPU smoke can check the installation. |
| Contract check fails | Use the bounds, causality, shape, or backward errors printed by `evo-proxy check`. If precheck blocks eval, its `result.md` includes the diagnostics. |

## Limits

Resource measurements use serial seed 0 training. Mamba uses the frozen loop implementation. The release leaves learning rates fixed and does not validate concurrent speedup or seed-to-seed cost variation. Candidate Python is imported directly, so only evaluate trusted source.

## Related repository, citation, and questions

`evo-proxy setup` installs the pinned [evaluation harness B](https://github.com/awesomesungminyu/KAIST-Intern-Proxy-Task-Bench) for you. The [candidate example](examples/candidate_mixer.py) follows the `CandidateMixer(d_model, num_heads, l_max)` contract.

Cite **KAIST Evo Proxy**, the repository URL and commit, and the relevant sources in [Data licenses and citations](DATA_LICENSES.md). Ask questions in [GitHub Issues](https://github.com/awesomesungminyu/kaist_evo_proxy/issues).

If installation raises ReadTimeoutError, rerun the same command. Compatible installed packages are skipped. An interrupted package download may restart when caching is disabled.

You can run `evo-proxy check examples/candidate_mixer.py` before downloading data. Dataset-dependent checks are deferred; evaluation still requires prepared data.

The verified default is `deepseek-v4-flash` with EvoScientist 0.4.4. The connection guide lists measured model timings and call counts.
