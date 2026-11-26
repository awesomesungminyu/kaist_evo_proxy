# YAML 후보 평가 · YAML candidates

## 한국어

이 어댑터는 한교진 연구원님 trial 브랜치의 `beyond_transformer/btyaml` 실행기를 **외부에서 import**합니다. 실행기·스키마·후보는 연구실 기여자의 작업이며 이 저장소에 복사하거나 수정하지 않습니다. [원본 브랜치](https://github.com/UVR-WJCHO/AI4Science_archive/tree/gyojin/evoscientist-trial01/beyond_transformer), 검증 소스 커밋 `a9fbd2b2676dd16bc33b0a0a442708928893d387`.

1. 하니스 설치·데이터 준비 후 외부 checkout의 `beyond_transformer`를 지정합니다. `representation.yaml`과 `relation.yaml`이 있는 후보 폴더를 선택합니다.

```bash
export EVO_PROXY_BTYAML=/path/to/AI4Science_archive/beyond_transformer
CANDIDATE="$EVO_PROXY_BTYAML/examples/trial01_1123/mixers/y04"
evo-proxy doctor --core
```

2. 학습 없이 계약을 검사합니다. 인과성·shape·backward·Transformer 블록 파라미터 ±10%는 기존 검사 그대로입니다.

```bash
evo-proxy check "$CANDIDATE" --out runs/y04_check
```

3. 검사를 통과하면 평가합니다. smoke는 CPU 1스텝 실행 확인이며 성능 점수가 아닙니다. full은 CUDA seed 0 고정 예산을 사용합니다. 다른 GPU 작업이 있으면 기다립니다.

```bash
evo-proxy baseline transformer --profile full --out runs/baseline_full
evo-proxy eval "$CANDIDATE" --profile full --baseline-run runs/baseline_full --out runs/y04_full
```

사람이 `result.md`를 읽습니다. `evo-proxy eval ... --profile smoke --task T1-R1-05`로 연결만 먼저 확인할 수 있습니다. 프로토콜 슬롯을 추가하거나 benchmark 코드를 변경하지 않습니다. 생성된 `yaml_candidate.py`는 Sam의 얇은 plugin wrapper이며 `yaml_provenance.json`에 후보와 외부 실행기 해시를 남깁니다. 외부 소스가 바뀌면 어댑터를 다시 생성해야 합니다. GPU OOM은 구현 한계/실패로 기록하며 예산이나 과제를 줄여 통과시키지 않습니다.

기존 연구원님 trial01의 5과제/max-SD 승패와 이 도구의 18과제/0.8 유지율·strict/relaxed는 다른 판정입니다. 결과를 섞지 마세요. 이 방식은 원본 YAML 실행기를 그대로 사용하므로 IMDB처럼 긴 과제에서 큰 중간 텐서 메모리가 필요할 수 있습니다.

## English

The adapter imports the external `beyond_transformer/btyaml` executor from the lab contributors' trial branch. No executor, schema or candidate implementation is vendored or modified. Source and attribution are linked above; the verified source revision is `a9fbd2b2676dd16bc33b0a0a442708928893d387`.

1. Prepare the evaluator and data, then set `EVO_PROXY_BTYAML` to the external checkout's `beyond_transformer` directory. Select a folder containing both `representation.yaml` and `relation.yaml` (first command block above).
2. Run `evo-proxy check "$CANDIDATE" --out runs/y04_check`. Frozen causality, shape, backward and ±10% Transformer block parameter checks remain unchanged.
3. Run the baseline and evaluation commands above. `full` uses the fixed CUDA seed-0 budget; smoke performs one CPU update and provides no performance score. Read `result.md` as a human. For a quick wiring check, use `--profile smoke --task T1-R1-05`.

No protocol slots or benchmark code are changed. The generated Python plugin is a small adapter, with candidate and external-source hashes in `yaml_provenance.json`. Regenerate it after external sources change. The original YAML executor can need substantial intermediate memory on long tasks such as IMDB; an OOM remains a failure, without reducing the evaluation budget. Do not combine the historical five-task/max-SD trial verdicts with this tool's eighteen-task/0.8 retention decisions.
