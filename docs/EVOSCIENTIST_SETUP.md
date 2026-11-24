# 연구실 EvoScientist 연결 · Lab EvoScientist setup

[English](#english)

## 한국어

### 0. 연구실 설치

[AI4Science_archive의 EvoScientist 설치 안내](https://github.com/UVR-WJCHO/AI4Science_archive/tree/main/evoscientist)를 따르세요. 이 절차는 **EvoScientist 0.4.4**와 `deepseek-v4-flash`에서 검증했습니다. 연구실 `.venv-evoscientist`와 하니스용 `.venv`는 분리합니다. 연구실의 `evoscientist/.env`에 endpoint와 키를 준비하고, EvoSci의 provider를 `custom-openai`로 설정합니다.

설치된 EvoScientist 버전이 검증 버전과 다르면 연구실 저장소 루트에서 `.venv-evoscientist/bin/pip install EvoScientist==0.4.4`를 실행하세요.

### 1. 하니스 준비

경로를 실제 위치로 바꾸세요. 이미 준비한 데이터가 있으면 그 `EVO_PROXY_HOME`을 그대로 쓸 수 있습니다.

```bash
export PIP_DEFAULT_TIMEOUT=120  # 느린 네트워크에서 설치 끊김 방지
export LAB_ARCHIVE="$HOME/AI4Science_archive"
export KEP_USER="$HOME/kaist_evo_proxy"
export EVO_PROXY_HOME="${EVO_PROXY_HOME:-$HOME/.cache/kaist-evo-proxy}"
# export EVO_PROXY_CPU=1  # GPU 없는 컴퓨터에서 연결만 확인할 때만
git clone https://github.com/awesomesungminyu/kaist_evo_proxy.git "$KEP_USER"
cd "$KEP_USER"
python3.11 -m venv .venv
.venv/bin/pip install -e .
export EVO_PROXY_BIN="$KEP_USER/.venv/bin/evo-proxy"
"$EVO_PROXY_BIN" setup
"$EVO_PROXY_BIN" data --download --dest "$EVO_PROXY_HOME/incoming"
"$EVO_PROXY_BIN" doctor --core
"$EVO_PROXY_BIN" install-skills --evo-workspace "$KEP_USER"
```

작업공간과 하니스의 `skills/`가 같으면 기존 파일을 그대로 사용합니다.

데이터를 받기 전에도 `"$EVO_PROXY_BIN" check examples/candidate_mixer.py`로 인과성·shape·backward·파라미터 계약을 검사할 수 있습니다. 데이터가 필요한 검증은 준비 후 확인으로 표시하며 실제 eval은 데이터를 요구합니다.

### 2. 연결 확인과 실제 평가

현재 셸에 다음 실행 함수를 정의하세요. EvoSci 실행은 하니스 작업공간 격리를 유지합니다.

```bash
launch_eval() (
  profile="$1"
  run_dir="$2"
  cd "$LAB_ARCHIVE/evoscientist"
  set -a
  source ./.env
  set +a
  export EVO_PROXY_MAX_ATTEMPTS=3
  export EVO_PROXY_ATTEMPT_LOG="$run_dir/attempts.json"
  "$EVO_PROXY_BIN" evo-prompt --profile "$profile" --out "${run_dir#"$KEP_USER"/}/eval" > "$run_dir/kep_prompt.md"
  ../.venv-evoscientist/bin/EvoSci --workdir "$KEP_USER" --auto-mode --output-format stream-json --prompt-file "$run_dir/kep_prompt.md"
)
mkdir -p "$KEP_USER/runs"
```

**① 연결 확인 · smoke · 보통 약 1분**

```bash
SMOKE_RUN=$(mktemp -d "$KEP_USER/runs/kep_smoke_XXXXXX")
launch_eval smoke "$SMOKE_RUN"
"$EVO_PROXY_BIN" status "$SMOKE_RUN/eval"
```

기본 smoke는 MAD 한 과제입니다. 연결 확인용이며, 다른 단일 과제는 `evo-prompt --profile smoke --task <ID>`로 고릅니다. 에이전트는 eval 종료까지만 기다립니다. `EVALUATION_COMPLETE`가 나오면 추가 명령이나 파일 읽기 없이 즉시 종료하며 결과 파일은 사람이 엽니다.

**② 실제 평가 · tier1 또는 full**

CUDA Torch를 설치한 환경을 사용하세요. Tier 1은 기존 Transformer v4 실행에서 약 40분이었고, full은 수십 분 이상 걸릴 수 있습니다. 모델과 GPU 대기 시간에 따라 달라집니다. 아래 `tier1` 대신 `tier2`, `cascade`, `full`도 사용할 수 있습니다.

```bash
SCORED_RUN=$(mktemp -d "$KEP_USER/runs/kep_scored_XXXXXX")
launch_eval tier1 "$SCORED_RUN"
"$EVO_PROXY_BIN" status "$SCORED_RUN/eval"
```

0.4.4 셸 도구의 기본 제한은 300초입니다. 채점 모드에서는 에이전트가 분리 실행의 PID와 출력 경로를 받은 뒤 종료합니다. `status`는 `precheck`, `waiting_for_gpu`, `running`, `done` 등의 상태를 표시합니다. 완료 후 `"$EVO_PROXY_BIN" report "$SCORED_RUN/eval"`로 표를 다시 만들 수 있습니다. 자세한 실행 기록은 `eval/run.log`에 있습니다.

매 실행은 고유한 `runs/<이름>/`를 만들며 그 아래에 후보, 프롬프트, 계약 검사, `eval/` 결과가 쌓입니다.

### 3. 결과 예시

Smoke는 결과 파일 생성과 실행 상태를 확인합니다. Transformer 대비 성능 점수와 GPU 비용은 비어 있습니다.

```text
Tier 1: 0/8 통과 (strict 미확인, relaxed 미확인)
Tier 2: 0/10 통과 (strict 미실행, relaxed 미실행)
자원: 기준 실행 없음 — `evo-proxy baseline transformer --profile smoke` 를 먼저 실행
```

다음은 **예시**입니다. 이전 Transformer v4 GPU 기록으로 렌더링한 Tier 1 표의 MAD 행입니다. 이번 연결 테스트에서 새로 측정한 점수는 아닙니다.

| 과제 | 지표(↑/↓) | 후보 점수 | Transformer 기준(3시드 평균) | Transformer 대비(×) | 0.8 통과 | GPU 시간(분) 후보/기준 | VRAM(MiB) 후보/기준 |
|---|---|---:|---:|---:|---|---:|---:|
| MAD Compression | token_accuracy ↑ | 0.54 | 0.53 | ×1.02 | 통과 | 0.73 / 0.73 | — / — |

`×1.00`은 Transformer와 같고, `×0.80` 이상은 과제 통과입니다. 낮을수록 좋은 지표의 유지율은 기준 점수 ÷ 후보 점수입니다.

### 4. 자주 막히는 곳

| 증상 | 확인할 것 |
|---|---|
| 모델 연결이 안 됨 | 연구실 `evoscientist/`의 `.env`를 위 함수에서 불러오고, provider `custom-openai`와 모델을 둘 다 지정하세요. |
| skill이나 실행 파일을 찾지 못함 | `--evo-workspace`와 `--workdir`는 하니스 절대경로, `EVO_PROXY_BIN`은 그 안의 `.venv/bin/evo-proxy`를 가리켜야 합니다. |
| GPU가 바쁨 | `status`로 상태를 보세요. 하니스가 빈 GPU를 기다립니다. |
| Tavily 경고 | 이 평가에는 웹 검색이 필요 없습니다. |

세션과 메모리는 기본적으로 `~/.evoscientist/`, 설정은 `~/.config/evoscientist/`에 남습니다. `--mode run` 대신 위의 격리된 `--workdir`를 사용합니다. 작업공간 밖의 파일에 접근할 필요가 없습니다.

### 알려진 제한

Tier·full 에이전트 실행은 모델 게이트웨이 장애로 검증을 마치지 못했으며, GPU 완주 점수는 측정하지 않았습니다.

## English

### 0. Install the lab EvoScientist

Follow the [AI4Science_archive setup](https://github.com/UVR-WJCHO/AI4Science_archive/tree/main/evoscientist). This guide was verified with **EvoScientist 0.4.4** and `deepseek-v4-flash`. Keep the lab and evaluator virtual environments separate. Configure `custom-openai` and put the endpoint and key in the lab checkout's `evoscientist/.env`.

If your EvoScientist version differs, run `.venv-evoscientist/bin/pip install EvoScientist==0.4.4` from the lab repository root.

### 1. Prepare the evaluator

Run the [setup block above](#1-하니스-준비) with your absolute paths. The evaluator lives at `$KEP_USER`; downloaded data defaults to `$HOME/.cache/kaist-evo-proxy`. Use the commented CPU-only export only for a connection check on a machine without a GPU. The two existing skills are left in place when the requested destination is the harness workspace itself.

Before downloading data, `"$EVO_PROXY_BIN" check examples/candidate_mixer.py` checks causality, shape, backward and parameters. Dataset-dependent checks are marked deferred; evaluation still requires prepared data.

### 2. Connection check and scored evaluation

Define [the launch function above](#2-연결-확인과-실제-평가) in your shell.

**① Connection check · smoke · about a minute**

```bash
SMOKE_RUN=$(mktemp -d "$KEP_USER/runs/kep_smoke_XXXXXX")
launch_eval smoke "$SMOKE_RUN"
"$EVO_PROXY_BIN" status "$SMOKE_RUN/eval"
```

MAD is the default. To select a different single task, generate a prompt with `--profile smoke --task <ID>`. After `EVALUATION_COMPLETE`, the agent must immediately end without another command or file read. Result files are left for you.

**② Scored evaluation · tier1 or full**

Use an environment with CUDA Torch. Tier 1 took about 40 minutes for the historical Transformer v4 run. Full runs can take tens of minutes or longer. GPU availability and the candidate affect both times. Use `tier1`, `tier2`, `cascade`, or `full`.

```bash
SCORED_RUN=$(mktemp -d "$KEP_USER/runs/kep_scored_XXXXXX")
launch_eval tier1 "$SCORED_RUN"
"$EVO_PROXY_BIN" status "$SCORED_RUN/eval"
```

The 0.4.4 shell tool has a 300-second default timeout. Scored prompts ask the agent to start a detached evaluation and wait only for the launch response. Use `status` to see whether it is in precheck, waiting for the GPU, running, or done. The log is `eval/run.log`. Once complete, regenerate the table with `"$EVO_PROXY_BIN" report "$SCORED_RUN/eval"`.

Every run creates a unique `runs/<name>/` directory containing the candidate, prompt, contract-check output, and `eval/` results.

### 3. Result examples

Smoke checks execution and result creation. Performance and GPU costs are blank.

```text
Tier 1: 0/8 통과 (strict 미확인, relaxed 미확인)
Tier 2: 0/10 통과 (strict 미실행, relaxed 미실행)
자원: 기준 실행 없음 — `evo-proxy baseline transformer --profile smoke` 를 먼저 실행
```

**Example from historical Transformer v4 GPU results.** This MAD row is from a rendered Tier 1 table, using a past seed-0 score against the existing three-seed reference.

| 과제 | 지표(↑/↓) | 후보 점수 | Transformer 기준(3시드 평균) | Transformer 대비(×) | 0.8 통과 | GPU 시간(분) 후보/기준 | VRAM(MiB) 후보/기준 |
|---|---|---:|---:|---:|---|---:|---:|
| MAD Compression | token_accuracy ↑ | 0.54 | 0.53 | ×1.02 | 통과 | 0.73 / 0.73 | — / — |

`×1.00` matches Transformer, and `×0.80` or higher passes the task. For metrics where lower is better, retention is the reference score divided by the candidate score.

### 4. Troubleshooting

| Symptom | What to check |
|---|---|
| Wrong provider or missing credentials | Select `custom-openai` and the model. The launch function exports the settings from the lab `evoscientist/.env`. |
| Skills or executable unavailable | Use the harness path for both `--evo-workspace` and `--workdir`. Set `EVO_PROXY_BIN` to its `.venv/bin/evo-proxy`. |
| GPU busy | Check `status`. The harness waits for an idle GPU. |
| Tavily warning | This evaluation does not use web search. |

Session and memory files normally live in `~/.evoscientist/`. Settings are in `~/.config/evoscientist/`. Use the isolated `--workdir` launch above. The separate session mode roots the shell in its run subdirectory.

### Known limitations

A model gateway outage prevented end-to-end tier and full agent verification. Completed GPU scores were not measured.

### Standalone launcher

For a non-lab environment, use a dedicated harness virtual environment with EvoScientist 0.4.1 and the [bundled launcher](../integrations/evoscientist/run_agent.py).

```bash
cd "$KEP_USER"
source .venv/bin/activate
pip install EvoScientist==0.4.1
export EVOSCIENTIST_WORKSPACE_DIR="$PWD/.evo-work"
evo-proxy install-skills
evo-proxy doctor
python integrations/evoscientist/run_agent.py --workspace .evo-work --prompt examples/research_request.md --env-file .env --model YOUR_MODEL
```

설치 중 ReadTimeoutError가 나면 같은 명령을 다시 실행하세요. 이미 받은 부분은 건너뜁니다. 설치가 완료된 호환 패키지를 재사용하며, 캐시가 없으면 중단된 패키지는 다시 다운로드할 수 있습니다.

If setup times out, rerun it. Compatible installed packages are skipped; an incomplete download may restart with caching disabled.
