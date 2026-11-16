# Evaluation cost — historical full 1-seed wall times

Source: SHA256-verified 310 full cells in the frozen 2026-11-03 training snapshot, summarized in `validation/baselines/final16_v4.json`. Times include setup/training/evaluation where the original runner included them. These are historical GPU wall times, not CPU estimates or exclusive GPU accounting. Different mixers can vary substantially; medians do not guarantee a candidate's runtime. No GPU measurements were made tonight.

| Task | Full cells | Median 1-seed seconds | Range seconds | Transformer seconds | LSTM seconds |
|---|---:|---:|---:|---:|---:|
| T1-R1-05 MAD Compression | 27 | 48.9 | 30.2–192.8 | 35.5 | 31.9 |
| T1-R2-01 Positional Histogram | 13 | 525.7 | 213.1–1081.4 | 326.1 | 289.1 |
| T1-R2-02 String Matching | 16 | 456.6 | 119.6–891.8 | 212.7 | 283.4 |
| T1-R0-07 RegBench | 27 | 95.0 | 75.0–280.0 | 82.0 | 77.0 |
| T1-R0-04 Parity | 27 | 741.0 | 13.0–1017.0 | 673.0 | 19.0 |
| T1-R0-05 Tomita 5 | 27 | 839.0 | 20.0–1098.0 | 781.0 | 51.0 |
| T1-R2-04 Cycle Navigation | 13 | 368.1 | 200.6–1238.3 | 309.0 | 368.1 |
| T1-R2-05 Random Automaton | 13 | 325.2 | 194.4–484.6 | 297.4 | 304.0 |
| T2-R1-11 Permuted MNIST | 20 | 134.0 | 74.3–432.9 | 137.6 | 74.5 |
| T2-R3-05 Permuted Kuzushiji-49 | 13 | 291.3 | 82.0–1287.4 | 223.1 | 237.7 |
| T2-R4-02 Speech Commands (raw waveform)* | 13 | 359.8 | 157.3–1805.1 | 359.8 | 157.7 |
| T2-R3-02 Permuted EMNIST (letters) | 13 | 352.5 | 76.9–1395.1 | 308.4 | 248.5 |
| T2-R1-04 TAPE Stability | 22 | 154.2 | 106.9–416.5 | 124.7 | 113.5 |
| T2-R1-09 enwik8 | 27 | 133.0 | 87.6–933.9 | 116.1 | 87.6 |
| T2-R1-08 IMDB (byte-level) | 26 | 91.9 | 42.0–750.5 | 89.5 | 43.4 |
| T2-R2-02 Lipophilicity (SMILES) | 13 | 92.9 | 29.8–224.6 | 42.3 | 92.9 |

One candidate × 16 tasks × 1 seed, serial median-budget estimate: **5,009.2 s (1.39 h)**; three seeds: **4.17 h**. Tier 1: 0.94 h; Tier 2: 0.45 h. Transformer-specific 16-task sum: 1.14 h; LSTM sum: 0.69 h.

## Cost-reduction hypotheses (not performance-validated or automatically enabled)

- Short training: 10%/25%/50% of steps could reduce the **training-only** component by up to 90%/75%/50%. Setup and evaluation remain; final-rank correlation must be measured before using these proxies. Full step budgets are not changed by this implementation.
- Cascade: if a Tier 1 execution fails, skipping all Tier 2 avoids up to **0.45 h (32.1%)** of this 1-seed median budget. This is a failure gate, not early stopping on low performance. The requested `--cascade` switch implements only this gate.
- Task reduction: the four cheapest historical tasks (T1-R1-05, T2-R1-08, T2-R2-02, T1-R0-07) would avoid about **93.4%** of this estimate. This is only a cost illustration; no claim that they preserve the full16 ranking, and no automatic reduced-task selection is implemented.
- Parallel execution: on 2/4 independent equivalent GPUs, ideal wall-time savings approach 50%/75%; real savings are bounded by the slowest task, memory, data I/O and contention. No multi-GPU scheduler or automatic job/resource tuning is implemented. CPU `--jobs` is an explicit orchestration option; CUDA suite is limited to jobs=1 for shared safety.

Do not use one-step smoke loss as an efficiency or performance proxy. `docs/EVOSCIENTIST.md` describes smoke versus full evidence.
