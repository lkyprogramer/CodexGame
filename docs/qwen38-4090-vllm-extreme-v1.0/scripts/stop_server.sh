#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UP="$ROOT/runtime/qwen38-vllm"
[ -d "$UP" ] || exit 0
cd "$UP"
docker compose --profile single down --remove-orphans
