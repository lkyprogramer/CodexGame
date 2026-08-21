#!/usr/bin/env bash
# Stop production, run C1-C3 and D0-D2, always restore 18343.
set -uo pipefail
WORKDIR="${DFLASH2_WORKDIR:-/home/hhtele/qwen38-dflash2-20260819}"
export DFLASH2_WORKDIR="$WORKDIR"
ROOT="$WORKDIR"
LOG="$WORKDIR/logs/run_remaining.log"
mkdir -p "$WORKDIR/logs" "$WORKDIR/results"
exec > >(tee -a "$LOG") 2>&1

fail=0
restore() {
  echo "=== restore prod $(date -Iseconds) ==="
  bash "$ROOT/launch/restore-prod.sh" || echo "RESTORE_FAILED"
}
trap restore EXIT

echo "=== stop prod $(date -Iseconds) ==="
bash "$ROOT/launch/stop-prod.sh"

run() {
  local lane="$1" launch="$2" model="$3"
  echo "=== $lane $(date -Iseconds) ==="
  if ! bash "$ROOT/scripts/run_lane.sh" "$lane" "$launch" "$model"; then
    echo "LANE_FAIL $lane"
    fail=1
    tail -n 40 "$WORKDIR/logs/${lane}.stderr.log" || true
  fi
}

run C1 "$ROOT/launch/c1-gavwhittaker-mtp.sh" openclaw/Qwen3.8-27B-DFLASH2
run C2 "$ROOT/launch/c2-gavwhittaker-text.sh" openclaw/Qwen3.8-27B-DFLASH2
run C3 "$ROOT/launch/c3-prod-mtp-n6.sh" openclaw/Qwen3.8-27B-DFLASH2
run D0 "$ROOT/launch/d0-alok-dflash2.sh" openclaw/Qwen3.8-27B-DFLASH2
run D1 "$ROOT/launch/d1-openclaw-dflash2.sh" openclaw/Qwen3.8-27B-DFLASH2

if [[ -f "$WORKDIR/results/D1/summary.json" ]]; then
  for n in 3 5 7; do
    echo "=== D2_n${n} $(date -Iseconds) ==="
    SPEC_DRAFT_N_MAX="$n" bash "$ROOT/scripts/run_lane.sh" "D2_n${n}" "$ROOT/launch/d1-openclaw-dflash2.sh" openclaw/Qwen3.8-27B-DFLASH2 || {
      echo "LANE_FAIL D2_n${n}"
      fail=1
    }
  done
fi

echo "=== remaining done fail=$fail $(date -Iseconds) ==="
exit 0
