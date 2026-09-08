#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"; load_bench_env
PROFILE=${1:-huge-mtp}
PF="$ROOT/configs/profiles/$PROFILE.env"
[ -f "$PF" ] || { echo "Unknown profile: $PROFILE"; exit 2; }
UP="$ROOT/runtime/qwen38-vllm"
[ -d "$UP" ] || "$ROOT/scripts/setup_upstream.sh"
cd "$UP"
# Generate upstream .env from the package profile. Keep the benchmark API key in one place.
{
  cat "$PF"
  echo "PORT=${SERVER_URL##*:}" | sed 's#/v1##'
  echo "VLLM_API_KEY=$API_KEY"
} > .env
log "starting upstream profile=$PROFILE"
docker compose --profile single down --remove-orphans >/dev/null 2>&1 || true
docker compose --profile single up -d
printf '%s\n' "$PROFILE" > "$ROOT/.state/current-profile"
log "server launched; follow: (cd $UP && docker compose logs -f single)"
