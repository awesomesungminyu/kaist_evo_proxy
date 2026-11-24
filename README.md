# kaist_evo_proxy

한국어 · [English](README.en.md)

EvoScientist가 제안한 새 시퀀스 구조를 18개 작은 과제에서 Transformer와 비교해 자동으로 채점하고, 사람이 읽을 결과표를 만들어 주는 도구입니다.

## 한눈에 보기

EvoScientist 후보 작성 → `evo-proxy check`(계약 검사) → `evo-proxy eval`(학습·채점) → `result.md`(사람이 판단)

## 빠른 시작

Linux와 Python 3.11이 필요합니다. CPU 빠른 시작은 디스크 약 5 GB를 사용했습니다. CUDA GPU는 채점용 모드에 필요하며 검증 장비는 TITAN RTX 24 GB입니다. 아래 CPU 예제는 MAD 한 과제만 실행합니다. 처음 설치하거나 네트워크가 느리면 5분보다 오래 걸릴 수 있습니다.

코드는 `git clone`으로 받으세요. Release 페이지의 **Source code (zip/tar.gz)**는 쓰지 않습니다. 데이터는 아래 명령이 Release에서 자동으로 받습니다.

```bash
git clone https://github.com/awesomesungminyu/kaist_evo_proxy.git && cd kaist_evo_proxy  # 코드를 받고 프로젝트 폴더로 이동
python3.11 -m venv .venv  # Python 가상환경 만들기
source .venv/bin/activate  # 가상환경 활성화
pip install -e .  # evo-proxy 명령 설치
export EVO_PROXY_CPU=1  # 이 빠른 시작은 CPU smoke 사용
evo-proxy setup  # 고정된 평가 하니스와 의존성 설치
evo-proxy data --download  # 단일 데이터 파일 다운로드 및 준비
evo-proxy doctor --core  # 평가기와 데이터 18개 준비 확인
evo-proxy baseline transformer --profile smoke --task T1-R1-05 --out runs/baseline  # MAD Transformer 기준 실행
evo-proxy eval examples/candidate_mixer.py --profile smoke --task T1-R1-05 --out runs/example  # 예제 후보 평가 및 결과표 생성
```

### 정상 출력 예시

`evo-proxy doctor --core` 출력에서 발췌했습니다. 처음에는 EvoScientist와 skill을 설치하기 전이라 해당 두 항목이 `false`일 수 있습니다.

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

평가가 끝나면 `runs/example/`에 `result.md`, `report.json`, `judged.json`, `resources.json`이 생깁니다. 실행별 로그는 `observations/`에서 볼 수 있습니다. 출력 폴더가 이미 있으면 터미널에 찍힌 새 하위 실행 경로를 여세요.

`result.md` 앞부분에서 발췌했습니다.

```text
Tier 1: 0/8 통과 (strict 미확인, relaxed 미확인)
Tier 2: 0/10 통과 (strict 미실행, relaxed 미실행)
자원: Transformer 대비 GPU 시간 —, 최대 VRAM —, 파라미터(블록) ×1.00
```

### EvoScientist 연결

```bash
pip install EvoScientist==0.4.1  # 검증한 EvoScientist 버전 설치
export EVOSCIENTIST_WORKSPACE_DIR="$PWD/.evo-work"  # 에이전트 작업 폴더 지정
evo-proxy install-skills  # 계약 검사와 평가 skill 2개 설치
evo-proxy doctor  # EvoScientist와 skill까지 점검
```

에이전트를 실행하기 직전에 프로젝트의 로컬 `.env`에 `CUSTOM_OPENAI_API_KEY`와 `CUSTOM_OPENAI_BASE_URL`(HTTPS, `/v1` 끝점)을 넣으세요. 명령의 `YOUR_MODEL`은 제공자의 모델 ID로 바꿉니다.

```bash
python integrations/evoscientist/run_agent.py --workspace .evo-work --prompt examples/research_request.md --env-file .env --model YOUR_MODEL  # 후보 하나를 검사·평가
```

에이전트는 출력된 계약 오류만 보고 최대 세 후보 버전까지 검사합니다. 첫 계약 통과 후 한 번 평가하고 종료합니다. 결과표는 사람이 읽습니다. 기존 skill과 충돌하면 새 작업 폴더에 설치하세요.

## 결과 읽는 법

| 파일 | 내용 |
|---|---|
| `result.md` | 사람용 과제 점수와 Transformer 대비 표 |
| `report.json` | 모드, 원점수, 과제별 실행 상태 |
| `judged.json` | 과제별 유지율과 Tier별 통과 판정 |
| `resources.json` | 실제 실행에서 측정한 시간, 메모리와 파라미터 |

기준 정확도가 0.90이고 후보가 0.72이면 유지율은 `0.72 ÷ 0.90 = 0.80`으로 통과합니다. 낮을수록 좋은 지표는 반대로 나눕니다. 기준 손실이 2.0이고 후보가 2.5이면 역시 `2.0 ÷ 2.5 = 0.80`입니다. Tier 1에서 7개가 통과하고 1개가 미달하면 strict는 실패, relaxed는 통과입니다.

자원 비교는 `--baseline-run runs/baseline`으로 기준을 지정하거나, 같은 모드의 최신 Transformer 기준 실행을 `runs/`에서 찾습니다. CPU smoke에서 GPU 시간과 VRAM은 해당 없음(`—`)으로 표시됩니다. 저장된 결과표는 `evo-proxy report runs/example`로 다시 만들 수 있습니다.

## 실행 모드

| 모드 | 실행 과제 | 예상 시간 | 언제 쓰나 |
|---|---|---|---|
| `smoke` | 기본 18개, CPU에서 한 번씩 업데이트. `--task`로 한 과제 선택 | MAD 한 과제는 수 초, 전체는 수 분 | 설치와 실행 확인 |
| `tier1` | Tier 1 8개, CUDA | 수 분~1시간 이상 | 합성 과제에서 능력별 비교 |
| `tier2` | Tier 2 10개, CUDA | 수 분~1시간 이상 | 실제 데이터에서 비교 |
| `cascade` | Tier 1부터 실행. 측정에서 두 과제가 0.8 미만이면 일찍 종료. 7개 통과가 확인되면 Tier 2 실행 | Tier 1 일부부터 full까지 | Tier 1 기준을 통과한 후보에만 Tier 2 비용 사용 |
| `full` | 전체 18개, CUDA | 수십 분 이상 | 전체 과제 점수 수집 |

시간은 계획용 추정치입니다. 채점 모드는 seed 0의 고정 학습 설정을 사용합니다. Cascade에서 실패나 미측정 때문에 Tier 1 통과 7개를 확인할 수 없으면 Tier 2를 실행하지 않습니다.

## 과제

### Tier 1

능력을 하나씩 보는 합성 과제입니다.

| ID | 과제 | 입력 | 지표 | 데이터 | 재는 능력 |
|---|---|---|---|---|---|
| T1-R1-05 | MAD Compression | 토큰 | token_accuracy ↑ | 파일 | 기억·검색 |
| T1-R0-07 | RegBench | 토큰 | next_token_acc ↑ | 실행 시 생성 | 규칙 학습 |
| T1-R2-02 | String Matching | 토큰 | accuracy ↑ | 실행 시 생성 | 기억·검색 |
| T1-R2-01 | Positional Histogram | 토큰 | slot_accuracy ↑ | 실행 시 생성 | 카운팅 |
| T1-R2-05 | Random Automaton | 토큰 | last_state_accuracy_id50_ex50 ↑ | 실행 시 생성 | 상태 추적 |
| T1-R2-04 | Cycle Navigation | 토큰 | accuracy_id50_ex50 ↑ | 실행 시 생성 | 상태 추적 |
| T1-R0-04 | Parity | 토큰 | mean_best_val_accuracy ↑ | 파일 | 상태 추적 |
| T1-R0-05 | Tomita 5 | 토큰 | mean_best_val_accuracy ↑ | 파일 | 상태 추적 |

### Tier 2

실제 데이터를 사용하는 과제입니다.

| ID | 과제 | 입력 | 지표 | 데이터 | 데이터 성격 |
|---|---|---|---|---|---|
| T2-R1-11 | Permuted MNIST | 연속값 시퀀스 | accuracy ↑ | 파일 | 연속 신호 |
| T2-R3-05 | Permuted Kuzushiji-49 | 연속값 시퀀스 | accuracy ↑ | 파일 | 연속 신호 |
| T2-R4-02 | Speech Commands (raw waveform) | 연속값 시퀀스 | accuracy ↑ | 파일 | 연속 신호 |
| T2-R3-02 | Permuted EMNIST (letters) | 연속값 시퀀스 | accuracy ↑ | 파일 | 연속 신호 |
| T2-R1-04 | TAPE Stability | 아미노산 토큰 | spearman_valid ↑ | 파일 | 생물·화학 서열 |
| T2-R1-09 | enwik8 | 바이트 | val_bpc ↓ | 파일 | 언어·텍스트 |
| T2-R1-08 | IMDB (byte-level) | 바이트 | accuracy ↑ | 파일 | 언어·텍스트 |
| T2-R2-02 | Lipophilicity (SMILES) | SMILES 토큰 | rmse_valid ↓ | 파일 | 생물·화학 서열 |
| promoters | Genomics (Human non-TATA promoters) | ACGTN ID, 0 패딩 | accuracy ↑ | 파일 | 생물·화학 서열 |
| bach | Bach Chorales | 16분음표당 MIDI 음높이 128개 | NLL (nats per next frame) ↓ | 파일 | 음악 |

## 판정과 기준값

1배 Transformer의 3시드 평균을 기준으로 과제별 유지율을 계산합니다. 과제 통과선은 0.8입니다. Strict는 Tier 1 8/8 및 Tier 2 10/10, relaxed는 각각 7/8 및 9/10입니다. Smoke는 비교 점수와 유지율을 계산하지 않습니다.

[Transformer 기준값](reference/transformer_reference.json) · [구조별 판정](reference/baseline_verdict.md) · [기준 구조](baselines/README.md) · [제외 과제](tasks/excluded.md)

## 데이터

기본 `evo-proxy data --download`가 [Release](https://github.com/awesomesungminyu/kaist_evo_proxy/releases/tag/data-20261124)에서 단일 파일 약 882 MB를 받습니다. 이번 CPU 빠른 시작에서 다운로드·검증·준비는 90초였습니다. 네트워크에 따라 더 오래 걸릴 수 있습니다.

수동으로는 Release에서 `proxy-task-bench-data_20261124.tar` 하나를 받고 `evo-proxy data --source proxy-task-bench-data_20261124.tar`를 실행하세요.

[Drive](https://drive.google.com/drive/folders/1SceShb6mBJXSaWDNzq6VrOgVajY-4ru0?usp=sharing)는 Release 다운로드·검증에 실패할 때 사용하는 자동 예비 미러입니다. [데이터 라이선스와 출처](DATA_LICENSES.md)

## 문제 해결

| 증상 | 해결 |
|---|---|
| Release 다운로드 실패 | 자동으로 Drive를 시도합니다. 둘 다 실패하면 터미널에 표시된 수동 링크를 사용하세요. |
| 서버 인터넷 제한 | 다른 곳에서 Release TAR를 받아 옮긴 뒤 `evo-proxy data --source 파일경로`를 실행하세요. 하니스 설치도 별도 네트워크 접근이 필요합니다. |
| Torch 버전 또는 CUDA 오류 | `evo-proxy doctor --core`에서 `torch`와 `cuda`를 확인하세요. Torch 2.5.1이 필요합니다. CUDA 채점은 드라이버에 맞는 CUDA PyTorch 가상환경을 사용하세요. CPU smoke는 setup 전에 `EVO_PROXY_CPU=1`을 설정합니다. |
| `data_18: false` | `evo-proxy data --download`를 다시 실행해 빠진 과제를 확인하세요. `--tasks`로 일부만 준비하면 전체 점검은 계속 실패합니다. |
| GPU 메모리 부족 | 해당 과제의 `observations/<ID>/process.log`를 확인하세요. 다른 GPU 작업이 끝난 뒤 다시 시도하세요. CPU smoke는 연결 확인에 사용할 수 있습니다. |
| 계약 검사 탈락 | `evo-proxy check`가 출력한 허용 범위, 인과성, shape 또는 backward 오류를 보고 수정하세요. 검사에서 막힌 eval은 `result.md`에 진단을 남깁니다. |

## 한계

자원 관측은 직렬 seed 0 실행 기준입니다. Mamba는 하니스의 loop 구현을 사용합니다. 학습률 재조정, 병렬 실행 가속, 시드별 비용 편차는 이 릴리스에서 검증하지 않았습니다. 후보 Python을 직접 import하므로 신뢰할 수 있는 후보만 실행합니다.

## 관련 저장소·인용·문의

[평가 하니스 B](https://github.com/awesomesungminyu/KAIST-Intern-Proxy-Task-Bench)를 직접 복제하거나 읽을 필요는 없습니다. `evo-proxy setup`이 해당 버전을 설치합니다. [후보 구현 예제](examples/candidate_mixer.py)는 `CandidateMixer(d_model, num_heads, l_max)` 계약을 따릅니다.

이 도구를 인용할 때는 **KAIST Evo Proxy**, 저장소 주소와 사용한 커밋, [데이터 출처와 인용](DATA_LICENSES.md)을 적어주세요. 문의는 [GitHub Issues](https://github.com/awesomesungminyu/kaist_evo_proxy/issues)에 남겨주세요.
