#!/usr/bin/env bash
# Rollback: TEXT q4 170K, thinking off, sampling 0.7/0.80/presence 1.5.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
export TRIAL_PORT="${PORT}"
export TRIAL_CTX="170000"
export TRIAL_CTK="q4_0"
export TRIAL_CTV="q4_0"
exec "$ROOT/llama-text.sh"
