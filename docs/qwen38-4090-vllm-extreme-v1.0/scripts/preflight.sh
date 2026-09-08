#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"
load_bench_env "${1:-}"

fail=0
printf '%-24s %s\n' 'check' 'value'
printf '%-24s %s\n' '-----' '-----'

gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || true)
drv=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1 || true)
mem=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || true)
printf '%-24s %s\n' GPU "${gpu:-MISSING}"
printf '%-24s %s\n' Driver "${drv:-MISSING}"
printf '%-24s %s MiB\n' VRAM "${mem:-0}"

if [[ "$gpu" != *4090* ]]; then echo 'WARN: package tuned for RTX 4090'; fi
if [ -z "$drv" ]; then echo 'FAIL: nvidia-smi unavailable'; fail=1; else
  major=${drv%%.*}
  if (( major < 580 )); then echo "FAIL: CUDA-13 container needs R580+; current=$drv"; fail=1; else echo 'PASS: driver CUDA-13 gate'; fi
fi

if command -v nvcc >/dev/null 2>&1; then
  nvcc --version | tail -1
else
  echo 'INFO: host nvcc absent; Docker path does not require host Toolkit 13'
fi

ram_kb=$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)
ram_gb=$((ram_kb/1024/1024))
printf '%-24s %s GiB\n' RAM "$ram_gb"
(( ram_gb >= 60 )) || { echo 'WARN: expected ~64 GiB RAM'; }

free_gb=$(df -Pk "$ROOT" | awk 'NR==2 {printf "%d", $4/1024/1024}')
printf '%-24s %s GiB\n' FreeDisk "$free_gb"
(( free_gb >= 100 )) || { echo 'FAIL: recommend >=100 GiB free disk'; fail=1; }

for c in git python3 curl docker timeout; do
  if command -v "$c" >/dev/null 2>&1; then printf '%-24s %s\n' "$c" "$(command -v "$c")"; else echo "FAIL: $c missing"; fail=1; fi
done

if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then echo 'PASS: docker daemon reachable'; else echo 'FAIL: docker daemon not reachable'; fail=1; fi
fi

if command -v "${PI_BIN:-pi}" >/dev/null 2>&1; then echo "PASS: Pi found: $(command -v "${PI_BIN:-pi}")"; else echo 'WARN: Pi not found; HTTP tests can run but Pi cases will fail/skip'; fi

exit "$fail"
