# Baseline mixers

The default MAD block has width 128, two layers and four heads.

| Mixer | Reference | Params per block | Implementation |
|---|---|---:|---|
| transformer | Vaswani et al., Attention Is All You Need (2017) | 194,816 | Frozen harness |
| gqa | Ainslie et al., GQA (2023) | 178,432 | Frozen harness |
| linear_attention | Katharopoulos et al., Transformers are RNNs (2020) | 194,816 | Frozen harness |
| gla | Yang et al., Gated Linear Attention Transformers with Hardware-Efficient Training (2024) | 195,332 | Frozen harness |
| retnet | Sun et al., Retentive Network (2023) | 195,862 | FLA CUDA path; PyTorch reference for CPU |
| mamba | Gu and Dao, Mamba (2024) | 194,800 | Frozen token loop |
| s4d | Gu et al., On the Parameterization and Initialization of Diagonal State Space Models (2022) | 178,944 | Frozen harness |
| hyena | Poli et al., Hyena Hierarchy (2023) | 213,824 | Frozen harness |
| lstm | Hochreiter and Schmidhuber, Long Short-Term Memory (1997) | 196,672 | Frozen harness |
