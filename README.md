# kaist_evo_proxy

한국어 · [English](README.en.md)

Transformer 대안 구조를 대규모 학습 전에 저비용 proxy task로 거르는 평가 하니스입니다. 동일한 백본·데이터·시드·학습 예산에서 후보 `CandidateMixer`를 검증하고, 과제별 실행 결과를 보고합니다. EvoScientist는 셸 도구로 같은 평가 명령을 호출하고 보고서를 읽어 다음 후보를 설계할 수 있습니다.

## 평가 범위

| Tier | 범위 | 목적 |
|---|---|---|
| 0 | 학습 없는 초기화 지표 | 사전 선별 참고 |
| 1 | 합성 과제 8개 | 능력별 단위 평가, Transformer 승 4·패 4 |
| 2 | 축소한 실제 데이터 8개 | 실제 데이터 평가, Transformer 승 4·패 4 |
| 3 | 대규모 언어 모델 | 후속 외부 검증 |

실행 목록은 Tier 1·2의 최종 16개입니다. 승패는 Transformer와 LSTM의 3시드 비교 결과를 뜻하며, 다른 7개 구조까지 포함한 순위는 일부 과제에서 미완료입니다. Speech Commands의 *는 S5 확인, EMNIST의 †는 예비·다양성 초과, Lipophilicity의 ‡는 [도메인 우선 규칙](docs/PREREG_DOMAIN_PRIORITY.md)을 뜻합니다.

## 16개 과제

| 태스크 | 입력 | 지표(↑ 높을수록, ↓ 낮을수록 좋음) | 데이터 |
|---|---|---|---|
| [T1-R1-05 · MAD Compression](tasks/T1-R1-05/README.md) | 토큰 | `token_accuracy` ↑ | 파일(합성 캐시) |
| [T1-R2-01 · Positional Histogram](tasks/T1-R2-01/README.md) | 토큰 | `slot_accuracy` ↑ | 실행 시 생성 |
| [T1-R2-02 · String Matching](tasks/T1-R2-02/README.md) | 토큰 | `accuracy` ↑ | 실행 시 생성 |
| [T1-R0-07 · RegBench](tasks/T1-R0-07/README.md) | 토큰 | `next_token_acc` ↑ | 실행 시 생성 |
| [T1-R0-04 · Parity](tasks/T1-R0-04/README.md) | 토큰 | `mean_best_val_accuracy` ↑ | 파일 |
| [T1-R0-05 · Tomita 5](tasks/T1-R0-05/README.md) | 토큰 | `mean_best_val_accuracy` ↑ | 파일 |
| [T1-R2-04 · Cycle Navigation](tasks/T1-R2-04/README.md) | 토큰 | `accuracy_id50_ex50` ↑ | 실행 시 생성 |
| [T1-R2-05 · Random Automaton](tasks/T1-R2-05/README.md) | 토큰 | `last_state_accuracy_id50_ex50` ↑ | 실행 시 생성 |
| [T2-R1-11 · Permuted MNIST](tasks/T2-R1-11/README.md) | 이미지 시퀀스 | `accuracy` ↑ | 파일 |
| [T2-R3-05 · Permuted Kuzushiji-49](tasks/T2-R3-05/README.md) | 이미지 시퀀스 | `accuracy` ↑ | 파일 |
| [T2-R4-02 · Speech Commands (raw waveform)\*](tasks/T2-R4-02/README.md) | 연속값 | `accuracy` ↑ | 파일 |
| [T2-R3-02 · Permuted EMNIST (letters)†](tasks/T2-R3-02/README.md) | 이미지 시퀀스 | `accuracy` ↑ | 파일 |
| [T2-R1-04 · TAPE Stability](tasks/T2-R1-04/README.md) | 아미노산 서열 | `spearman_valid` ↑ | 파일 |
| [T2-R1-09 · enwik8](tasks/T2-R1-09/README.md) | 바이트 | `val_bpc` ↓ | 파일 |
| [T2-R1-08 · IMDB (byte-level)](tasks/T2-R1-08/README.md) | 바이트 | `accuracy` ↑ | 파일 |
| [T2-R2-02 · Lipophilicity (SMILES)‡](tasks/T2-R2-02/README.md) | SMILES 문자 | `rmse_valid` ↓ | 파일 |


## 설치와 데이터

Linux와 Python 3.11을 권장합니다. CPU에서 목록 조회와 단위 테스트가 가능하고 full 평가는 CUDA GPU가 필요합니다.

```bash
git clone https://github.com/awesomesungminyu/kaist_evo_proxy.git
cd kaist_evo_proxy
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m validation list
```

PyTorch 빌드는 사용 중인 CUDA 환경에 맞춰 설치합니다. 원본 데이터는 [데이터 안내](docs/DATA.md)에 적힌 다섯 묶음에서 준비합니다. 생성형 5개는 실행 중 만들며 11개는 파일이 필요합니다. 데이터·체크포인트는 저장소에 포함하지 않습니다.

```bash
python -m validation prepare --source downloads/extracted --data-root data
python -m validation data --data-root data
CUDA_VISIBLE_DEVICES="" python -m unittest discover -s tests -v
```

## 후보 구조 평가

단일 Python 파일에 `CandidateMixer(nn.Module)`을 정의합니다. 생성자는 `(d_model, num_heads, l_max)`, `forward`는 `[B,T,D]` 입력을 같은 모양으로 반환해야 합니다. 인과성, 유한 출력·기울기, Transformer 블록 대비 ±10% 파라미터 규칙을 precheck가 검사합니다. [후보 예시](examples/candidate_mixer.py)와 [상세 규약](docs/MODELS.md)을 참고하세요.

```bash
CANDIDATE="$PWD/examples/candidate_mixer.py"
OUT="$PWD/artifacts/example"
python -m validation precheck --mixer "$CANDIDATE:CandidateMixer" --data-root data --out "$OUT/precheck.json"
python -m validation suite --mixer "$CANDIDATE:CandidateMixer" --profile smoke --seeds 0 --out "$OUT" --data-root data --tfl-root third_party/tfl --device cpu --jobs 1 --timeout 240
python -m validation report --suite "$OUT"
```

`evaluate.sh`는 위 세 단계를 한 번에 실행합니다. `EVO_WORK_ROOT`, `EVO_DATA_ROOT`, `EVO_TFL_ROOT`로 입력·출력 위치를 지정합니다. 출력은 `EVO_WORK_ROOT` 아래에 둡니다.

```bash
export EVO_WORK_ROOT="$PWD/.evo-work" EVO_DATA_ROOT="$PWD/data" EVO_TFL_ROOT="$PWD/third_party/tfl"
bash integrations/evoscientist/evaluate.sh "$CANDIDATE" "$EVO_WORK_ROOT/runs/example"
```

smoke는 과제당 optimizer 1회로 연결 확인에 사용하며 CPU에서 과제별 수초~수분이 걸릴 수 있습니다. full은 고정 학습 예산과 평가를 사용하고 GPU에서 과제별 수분~수시간이 걸릴 수 있습니다. GPU와 데이터에 따라 시간은 달라집니다. smoke 점수는 성능 순위가 아닙니다.

## EvoScientist 연결과 한계

EvoScientist가 후보를 쓰고 셸 도구로 `evaluate.sh`를 호출한 뒤 `report.json`을 읽습니다. 실행기는 [연동 안내](docs/EVOSCIENTIST.md)에 있습니다. 엔드포인트와 자격증명은 `CUSTOM_OPENAI_BASE_URL=<YOUR_OPENAI_COMPATIBLE_ENDPOINT>` 및 `CUSTOM_OPENAI_API_KEY` 환경 변수로만 전달합니다. 프레임워크는 별도로 설치해야 합니다.

1시드 full 결과는 잠정치입니다. 연속값 입력 네 과제(T2-R1-11, T2-R3-05, T2-R4-02, T2-R3-02)는 같은 시드에서도 실행 간 흔들림이 관찰되어 작은 차이를 개선 근거로 삼지 않습니다. RegBench는 반복 관측한 개발 스트림을 평가합니다. 과제 선정과 1스텝 확인만으로 전체 구조의 우위를 확정하지 않습니다.
