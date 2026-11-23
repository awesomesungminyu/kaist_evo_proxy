# kaist_evo_proxy

한국어 · [English](README.en.md)

Transformer 대안 mixer를 가벼운 18개 과제로 평가합니다. 후보를 CPU에서 검사하고, 두 티어의 유지율과 자원을 기록하며, EvoScientist가 읽을 피드백을 만듭니다.

## 빠른 시작

### 자동으로 되는 것

| 명령 | 하는 일 |
|---|---|
| `evo-proxy setup` | 지정된 평가기와 의존성을 설치합니다. |
| `evo-proxy data --download` | 필요한 Drive 묶음을 받고 SHA-256을 검사한 뒤 데이터를 준비합니다. |
| `evo-proxy install-skills` | EvoScientist 작업 폴더에 skill을 복사합니다. |
| `evo-proxy eval` | 후보를 검사하고 평가 결과와 피드백을 씁니다. |
| `evo-proxy doctor` | 설치, 데이터, EvoScientist와 skill 준비 상태를 확인합니다. |

### 직접 준비할 것

1. Linux와 Python 3.11을 준비합니다. CUDA GPU는 full 평가에 필요합니다. CPU smoke는 setup 전에 `export EVO_PROXY_CPU=1`을 실행합니다.
2. 로컬 `.env`에 `CUSTOM_OPENAI_API_KEY`와 `CUSTOM_OPENAI_BASE_URL`을 설정합니다.
3. 에이전트 명령의 `YOUR_MODEL`을 제공자의 모델 ID로 바꿉니다.

### 명령 순서

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
evo-proxy setup
```

[Drive 목록](drive_upload_20261123/README.md)의 데이터 묶음을 같은 `incoming/` 폴더에 풀고 수동 경로를 사용할 수도 있습니다.

```bash
evo-proxy data --download
evo-proxy doctor --core
evo-proxy eval examples/candidate_mixer.py --profile smoke --out runs/example
evo-proxy baseline transformer --profile smoke --out runs/baseline
pip install EvoScientist==0.4.1
export EVOSCIENTIST_WORKSPACE_DIR="$PWD/.evo-work"
evo-proxy install-skills
evo-proxy doctor
```

프로젝트의 로컬 `.env`에 `CUSTOM_OPENAI_API_KEY`와 `CUSTOM_OPENAI_BASE_URL`을 넣고 `YOUR_MODEL`을 제공자의 모델 ID로 바꿉니다.

```bash
python integrations/evoscientist/run_agent.py --workspace .evo-work \
  --prompt examples/research_request.md --env-file .env --model YOUR_MODEL
```

### 데이터 선택 및 수동 준비

[Drive](https://drive.google.com/drive/folders/1SceShb6mBJXSaWDNzq6VrOgVajY-4ru0?usp=sharing) · [archive and task checklist](drive_upload_20261123/README.md)

```bash
evo-proxy data --download --tasks tier1 --dest incoming
evo-proxy data --download --tasks T1-R1-05 T2-R4-02
evo-proxy data --source incoming
```

기본 다운로드는 9개 묶음, 881,766,137바이트입니다. 신규 Linux 검증에서 다운로드·검증·압축 해제·준비를 합쳐 58초가 걸렸습니다. Speech의 원본 WAV 묶음은 선택이며, 기본 경로는 평가 캐시를 사용합니다. 이전 extras와 겹치는 자료는 11/23 묶음을 사용합니다.

| Tier | ID | 과제 | 데이터 | 기본 묶음 | 준비 후 파일 |
|---|---|---|---|---|---|
| 1 | T1-R1-05 | MAD Compression | 파일 | proxy-data-final-pool-mad.tar.gz | inputs.npy |
| 1 | T1-R0-07 | RegBench | 생성형 | — | — |
| 1 | T1-R2-02 | String Matching | 생성형 | — | — |
| 1 | T1-R2-01 | Positional Histogram | 생성형 | — | — |
| 1 | T1-R2-05 | Random Automaton | 생성형 | — | — |
| 1 | T1-R2-04 | Cycle Navigation | 생성형 | — | — |
| 1 | T1-R0-04 | Parity | 파일 | proxy-data-final-pool-parity.tar.gz | train_corpus.pk, val_corpus_bins.pk |
| 1 | T1-R0-05 | Tomita 5 | 파일 | proxy-data-tomita5.tar.gz | train_corpus.pk, val_corpus_bins.pk |
| 2 | T2-R1-11 | Permuted MNIST | 파일 | proxy-data-final-pool-small.tar.gz | train-images-idx3-ubyte.gz, train-labels-idx1-ubyte.gz |
| 2 | T2-R3-05 | Permuted Kuzushiji-49 | 파일 | proxy-data-final-pool-small.tar.gz | train_x.npy, train_y.npy |
| 2 | T2-R4-02 | Speech Commands (raw waveform) | 파일 | proxy-data-speech-cache.tar.gz | train_x.npy, train_y.npy, val_x.npy, val_y.npy |
| 2 | T2-R3-02 | Permuted EMNIST (letters) | 파일 | proxy-data-emnist.tar.gz | train_x.npy, train_y.npy |
| 2 | T2-R1-04 | TAPE Stability | 파일 | proxy-data-final-pool-small.tar.gz | train.csv, valid.csv |
| 2 | T2-R1-09 | enwik8 | 파일 | proxy-data-final-pool-small.tar.gz | enwik8.zip |
| 2 | T2-R1-08 | IMDB (byte-level) | 파일 | proxy-data-final-pool-small.tar.gz | train_x.npy, train_y.npy, val_x.npy, val_y.npy |
| 2 | T2-R2-02 | Lipophilicity (SMILES) | 파일 | proxy-data-final-pool-small.tar.gz, proxy-data-lipophilicity.tar.gz | Lipophilicity.csv, split.npz |
| 2 | promoters | Human non-TATA promoter classification | 파일 | proxy-data-promoters.tar.gz | arrays.npz |
| 2 | bach | DCMLab Bach chorales | 파일 | proxy-data-bach.tar.gz | arrays.npz |

## EvoScientist 루프

skill 읽기 → 후보 작성 → `evo-proxy check` → `evo-proxy eval --profile smoke` → `feedback.md` 읽기 → 다음 후보 작성

기본 상한은 모델 호출 40회, precheck를 받는 서로 다른 후보 버전 3개입니다. Smoke로는 실행과 피드백 전달을 확인합니다.

## 실행 모드

| Profile | Tasks | Typical planning window | Use |
|---|---|---|---|
| smoke | All 18, one CPU update per task | Minutes | Check wiring and finiteness |
| tier1 | 8 synthetic tasks | Minutes to under an hour | Isolate sequence capabilities |
| tier2 | 10 dataset tasks | Minutes to under an hour | Measure dataset performance |
| cascade | Tier 1, then Tier 2 on a relaxed pass | Up to a full run | Stop after the second measured Tier 1 miss |
| full | All 18, seed 0 on CUDA | Tens of minutes or more | Collect a comparable score for each task |

## 과제

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

## 판정

유지율은 1배 Transformer 3시드 평균을 기준으로 합니다. maximize 지표는 후보/기준, minimize 지표는 기준/후보입니다. 과제 통과선은 0.8입니다. 엄격 기준은 Tier 1 8/8·Tier 2 10/10, 완화 기준은 각각 7/8·9/10입니다. Smoke에서는 점수와 유지율을 비워 둡니다.

[Transformer 기준값](reference/transformer_reference.json) · [구조별 판정](reference/baseline_verdict.md)

## 후보와 기준 구조

예시를 복사해 `CandidateMixer(d_model, num_heads, l_max)`를 구현합니다. `evo-proxy check candidate.py`로 계약을 확인한 뒤 평가합니다. 기준 구조는 `evo-proxy baseline NAME --profile smoke`로 실행합니다.

[후보 예시](examples/candidate_mixer.py) · [기준 구조](baselines/README.md) · [제외 과제](tasks/excluded.md)

## 한계

자원 관측은 직렬 seed 0 실행 기준입니다. Mamba는 하니스의 loop 구현을 사용합니다. 학습률 재조정, 병렬 실행 가속, 시드별 비용 편차는 이 릴리스에서 검증하지 않았습니다. 후보 Python을 직접 import하므로 신뢰할 수 있는 후보만 실행합니다.

출력 폴더가 이미 있으면 그 아래에 새 실행 폴더를 생성합니다. `report.json`, `judged.json`, `resources.json`, `feedback.md`를 생성합니다.
