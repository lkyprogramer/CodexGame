#!/usr/bin/env bash
# Frozen TEXT production. Probe winner: q4_170k (22622 MiB / 1595 free).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
export TRIAL_PORT="${PORT}"
export TRIAL_CTX="170000"
export TRIAL_CTK="q4_0"
export TRIAL_CTV="q4_0"
exec "$ROOT/llama-text.sh"
