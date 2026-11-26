#!/usr/bin/env bash
# Run one lab command inside a production stop window, then always restore production.
# Usage: lab_window.sh <minutes (1-90)> <command> [args...]
# Exit codes: payload rc on success; 3 driver risk; 4 production busy; 5 production not healthy after restore; 2 usage.
set -u -o pipefail
UNIT=openclaw-qwen38-next.service
HEALTH=http://127.0.0.1:18343/health
METRICS=http://127.0.0.1:18343/metrics
LAB=${LAB:?source env.sh first}
HERE=$(cd "$(dirname "$0")" && pwd)
BASE=$LAB/evidence/driver-baseline.txt
LOG=$LAB/evidence/windows.log

MIN=${1:-}; shift || true
case $MIN in ''|*[!0-9]*) echo "usage: $0 <minutes> <command...>" >&2; exit 2 ;; esac
[ "$MIN" -ge 1 ] && [ "$MIN" -le 90 ] || { echo "window must be 1-90 minutes; longer needs user approval" >&2; exit 2; }
[ $# -gt 0 ] || { echo "no command given" >&2; exit 2; }
[ -f "$BASE" ] || { echo "missing driver baseline $BASE (run T00)" >&2; exit 2; }

health_loaded() { curl -fsS --max-time 3 "$HEALTH" | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("loaded") is True else 1)'; }
prod_idle() { curl -fsS --max-time 3 "$METRICS" | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["live"]["state"] == "idle" else 1)'; }
stamp() { date -u +%FT%TZ; }

bash "$HERE/driver_guard.sh" check "$BASE" >/dev/null || { echo "driver guard failed before the window; production untouched" >&2; exit 3; }
prod_idle || { echo "production is not idle; not entering the window" >&2; exit 4; }

START=$(stamp); RC=0
ancestors() { local p=$$; while [ -n "$p" ] && [ "$p" -gt 1 ]; do echo "$p"; p=$(ps -o ppid= -p "$p" 2>/dev/null | tr -d ' '); done; }
cleanup_lab() {
  # Stop leftover lab processes (e.g. a background llama-server); never this script or its parents.
  local keep pid
  keep=" $(ancestors | tr '\n' ' ') "
  for pid in $(pgrep -u "$(id -u)" -f "$LAB/(src|runs|toolchains)/" || true); do
    case "$keep" in *" $pid "*) continue ;; esac
    kill "$pid" 2>/dev/null || true
  done
}
restore() {
  trap - EXIT INT TERM
  cleanup_lab
  sleep 2
  sudo -n /usr/bin/systemctl start "$UNIT"
  local ok=0
  for _ in $(seq 1 60); do if health_loaded; then ok=1; break; fi; sleep 5; done
  local drc=0
  bash "$HERE/driver_guard.sh" check "$BASE" >/dev/null || drc=3
  echo "$START $(stamp) minutes=$MIN rc=$RC restored=$ok driver_rc=$drc cmd=$*" >> "$LOG"
  if [ $drc -ne 0 ]; then echo "DRIVER FINGERPRINT CHANGED during the window: notify the user" >&2; exit 3; fi
  if [ $ok -ne 1 ]; then echo "production NOT healthy after 300 s: inspect the service log" >&2; exit 5; fi
  echo "production restored (lab rc=$RC)"
  exit $RC
}
trap restore EXIT
trap 'RC=130; exit' INT TERM

sudo -n /usr/bin/systemctl stop "$UNIT" || { RC=2; echo "could not stop production" >&2; exit 2; }
for _ in $(seq 1 30); do
  used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  [ "${used:-99999}" -lt 1024 ] && break; sleep 2
done
nvidia-smi --query-gpu=memory.used,memory.total --format=csv | tee -a "$LAB/evidence/gpu-after-stop.csv"
timeout --kill-after=30 "$((MIN * 60))" "$@"; RC=$?
