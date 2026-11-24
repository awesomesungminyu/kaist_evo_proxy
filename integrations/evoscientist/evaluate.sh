#!/usr/bin/env bash
set -euo pipefail
exec evo-proxy eval "$1" --profile "${EVO_EVAL_PROFILE:-smoke}" --out "$2"
