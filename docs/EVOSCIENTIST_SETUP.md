# 연구실 EvoScientist 연결 · Lab EvoScientist setup

[English](#english)

## 한국어

### 0. 연구실 설치

[연구실 AI4Science_archive의 EvoScientist 안내](https://github.com/UVR-WJCHO/AI4Science_archive/tree/main/evoscientist)를 따르세요. 이 절차는 연구실의 `evoscientist/setup.sh`로 설치한 **EvoScientist 0.4.4**에서 확인했습니다.

- 연구실 설치 스크립트가 만든 `.venv-evoscientist/bin/EvoSci`를 사용할 수 있어야 합니다.
- 연구실 저장소의 `evoscientist/.env`에 `CUSTOM_OPENAI_BASE_URL`과 `CUSTOM_OPENAI_API_KEY`를 설정하세요. `custom-openai` provider와 사용할 모델을 지정합니다. 검증 모델은 `deepseek-v4-flash`였습니다.
- 평가 도구의 `.venv`는 연구실 `.venv-evoscientist`와 분리하세요. 연구실의 다른 프레임워크는 호환되지 않는 LangGraph 버전을 사용합니다. 하니스는 아래에서 별도 가상환경으로 실행합니다.

### 1. 평가 도구 준비

다음 두 절대경로를 실제 위치로 바꾸세요. 앞서 빠른 시작을 마쳤다면 준비된 하니스의 `EVO_PROXY_HOME`을 그대로 쓰고 `doctor --core`만 확인해도 됩니다.

```bash
export LAB_ARCHIVE="$HOME/AI4Science_archive"
export KEP_USER="$HOME/kaist_evo_proxy"
export EVO_PROXY_HOME="$KEP_USER/.kep-data"
export EVO_PROXY_CPU=1
git clone https://github.com/awesomesungminyu/kaist_evo_proxy.git "$KEP_USER"
cd "$KEP_USER"
python3.11 -m venv .venv
.venv/bin/pip install -e .
export EVO_PROXY_BIN="$KEP_USER/.venv/bin/evo-proxy"
"$EVO_PROXY_BIN" setup
"$EVO_PROXY_BIN" data --download
"$EVO_PROXY_BIN" doctor --core
```

### 2. 연결 세 단계

1. 작업공간에 skill 두 개를 설치합니다. 설치 위치는 `$KEP_USER/skills/`입니다.

   ```bash
   "$EVO_PROXY_BIN" install-skills --evo-workspace "$KEP_USER"
   ```

2. 절대경로 실행 명령과 결과 폴더가 담긴 단발 프롬프트를 생성합니다. 모델 호출은 이 단계에서 일어나지 않습니다.

   ```bash
   "$EVO_PROXY_BIN" evo-prompt --out runs/kep_eval > "$KEP_USER/kep_prompt.md"
   ```

3. 연구실 `evoscientist/`에서 환경값을 불러온 뒤 실행합니다. 검증 당시 0.4.4는 파일이 옆에 있어도 셸에 값을 내보내기 전에는 provider 설정을 읽지 못했습니다.

   ```bash
   cd "$LAB_ARCHIVE/evoscientist"
   (
     set -a
     source ./.env
     set +a
     export EVO_PROXY_MAX_ATTEMPTS=3
     export EVO_PROXY_ATTEMPT_LOG="$KEP_USER/runs/.kep-attempts-$(date +%s).json"
     ../.venv-evoscientist/bin/EvoSci --workdir "$KEP_USER" --auto-mode --output-format stream-json --prompt-file "$KEP_USER/kep_prompt.md"
   )
   ```

`--workdir`는 하니스 폴더를 가상 작업공간의 루트로 지정합니다. 별도 `--mode run` 세션에서는 세션 밖의 하니스 실행 경로가 세션 안의 가상 경로로 해석돼 실행되지 않았습니다. 기본 연결에 `--dangerous`는 필요하지 않습니다. 이 옵션은 실제 호스트 파일시스템 접근을 허용하므로 위 명령에는 추가하지 마세요.

### 3. 정상 실행

아래는 실제 도구 출력에서 발췌했습니다.

```text
Precheck: passed
T1-R1-05: done
Output: /tmp/kep_user/runs/kep_eval
```

후보는 `$KEP_USER/candidate_mixer.py`에, 결과는 `$KEP_USER/runs/kep_eval/`의 `result.md`, `report.json`, `judged.json`, `resources.json`에 생성됩니다. 에이전트는 평가 명령 뒤 종료합니다. 계약 검사 오류가 있을 때만 최대 세 후보 버전까지 수정합니다.

```text
Tier 1: 0/8 통과 (strict 미확인, relaxed 미확인)
Tier 2: 0/10 통과 (strict 미실행, relaxed 미실행)
자원: 기준 실행 없음 — `evo-proxy baseline transformer --profile smoke` 를 먼저 실행
```

### 4. 결과표 읽기

`×1.00`은 Transformer 기준과 같습니다. `×0.80` 이상이면 과제 통과입니다. ↓ 지표는 기준 점수 ÷ 후보 점수로 계산합니다. 위 smoke는 설치와 실행 확인용이어서 점수와 GPU 비용을 비워 둡니다.

### 5. 자주 막히는 곳

| 증상 | 확인할 것 |
|---|---|
| 모델 이름을 넣어도 연결이 안 됨 | `EvoSci config set provider custom-openai`와 `EvoSci config set model <모델>`을 둘 다 지정하세요. |
| 환경값을 못 읽음 | 연구실 `evoscientist/`에서 위의 `source ./.env`를 실행하세요. |
| skill이 안 보임 | `--evo-workspace`와 `--workdir`가 같은 절대경로인지 확인하세요. |
| `evo-proxy`를 찾지 못함 | `EVO_PROXY_BIN`을 하니스의 `.venv/bin/evo-proxy`로 지정하세요. 별도 run 모드 대신 위 `--workdir`를 사용하세요. |
| Tavily 경고 | 위 단발 평가에는 웹 검색이 필요 없으므로 이 경고는 무시해도 됩니다. |

### 6. 상태가 쌓이는 곳

기본 세션과 메모리는 `~/.evoscientist/`, 설정은 `~/.config/evoscientist/`에 저장됩니다. 평가 산출물은 하니스의 `runs/`에 남습니다. 검증은 별도 HOME에서 진행했습니다.

연구실 환경을 사용하지 않는 경우, 별도 평가 환경에 EvoScientist 0.4.1을 설치하고 [A의 단발 실행기](../integrations/evoscientist/run_agent.py)를 사용할 수 있습니다. [다른 환경용 실행 예시](#standalone-launcher).

## English

### 0. Lab installation

Follow the [EvoScientist setup in AI4Science_archive](https://github.com/UVR-WJCHO/AI4Science_archive/tree/main/evoscientist). The lab setup script installed **EvoScientist 0.4.4** in this test.

- Confirm the lab’s `.venv-evoscientist/bin/EvoSci` runs.
- Set `CUSTOM_OPENAI_BASE_URL` and `CUSTOM_OPENAI_API_KEY` in the lab checkout’s `evoscientist/.env`. Select provider `custom-openai` and set the model explicitly. We verified `deepseek-v4-flash`.
- Keep the harness’s `.venv` separate from the lab environment. The lab documents incompatible LangGraph versions across its frameworks. The harness runs in its own interpreter.

### 1. Prepare the harness

Set the two absolute paths and run the [harness setup commands](#1-평가-도구-준비). If the quickstart is already complete, reuse its `EVO_PROXY_HOME` and confirm `doctor --core` succeeds.

### 2. Connect in three steps

1. Install both skills inside the harness workspace.

   ```bash
   "$EVO_PROXY_BIN" install-skills --evo-workspace "$KEP_USER"
   ```

2. Generate a one-shot request with the absolute executable and output directory. This command does not call the model.

   ```bash
   "$EVO_PROXY_BIN" evo-prompt --out runs/kep_eval > "$KEP_USER/kep_prompt.md"
   ```

3. From the lab checkout, load the environment file and start EvoScientist.

   ```bash
   cd "$LAB_ARCHIVE/evoscientist"
   (
     set -a
     source ./.env
     set +a
     export EVO_PROXY_MAX_ATTEMPTS=3
     export EVO_PROXY_ATTEMPT_LOG="$KEP_USER/runs/.kep-attempts-$(date +%s).json"
     ../.venv-evoscientist/bin/EvoSci --workdir "$KEP_USER" --auto-mode --output-format stream-json --prompt-file "$KEP_USER/kep_prompt.md"
   )
   ```

The explicit workspace keeps path isolation enabled. In per-session `--mode run`, the external executable resolved inside the session folder and was missing. The tested connection uses `--workdir` without `--dangerous`, which would grant real host filesystem access.

### 3. Successful output

Excerpt from the actual tool output.

```text
Precheck: passed
T1-R1-05: done
Output: /tmp/kep_user/runs/kep_eval
```

Look for `candidate_mixer.py` in the harness workspace and `result.md`, `report.json`, `judged.json`, and `resources.json` under `runs/kep_eval/`. The agent stops after eval. It can revise up to three distinct candidate versions using the contract errors printed by check.

```text
Tier 1: 0/8 통과 (strict 미확인, relaxed 미확인)
Tier 2: 0/10 통과 (strict 미실행, relaxed 미실행)
자원: 기준 실행 없음 — `evo-proxy baseline transformer --profile smoke` 를 먼저 실행
```

### 4. Read the table

`×1.00` matches Transformer. A retention of at least `×0.80` passes. For ↓ metrics, retention is the reference divided by the candidate. This CPU smoke run leaves performance scores and GPU costs empty.

### 5. Troubleshooting

| Symptom | What to check |
|---|---|
| Wrong provider | Set both `EvoSci config set provider custom-openai` and `EvoSci config set model <model>`. |
| Credentials unavailable | Run `source ./.env` with the exports shown above from the lab’s `evoscientist/` directory. |
| Missing skills | Use the same absolute path for `--evo-workspace` and `--workdir`. |
| Harness executable missing | Point `EVO_PROXY_BIN` to the harness’s `.venv/bin/evo-proxy` and launch with the tested `--workdir`. |
| Tavily warning | This one-shot evaluation needs no web search. |

### 6. State locations

EvoScientist normally writes session and memory state into `~/.evoscientist/` and configuration into `~/.config/evoscientist/`. Evaluation output stays under the harness’s `runs/`. Testing used an isolated HOME.

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
