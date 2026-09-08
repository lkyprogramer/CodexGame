#!/usr/bin/env bash
# Mac-side: Pi × Lucebox prefix off then on. Restores WORK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CTL=/tmp/4090_lucebox_ctl.sh
NOW() { date +%Y-%m-%dT%H:%M:%S; }
scp -o ConnectTimeout=10 "$ROOT/scripts/4090_lucebox_ctl.sh" hhtele@192.168.10.29:/tmp/4090_lucebox_ctl.sh
ssh hhtele@192.168.10.29 'chmod +x /tmp/4090_lucebox_ctl.sh'

restart_proxy() {
  local lane="$1"
  mkdir -p "$ROOT/results/$lane"
  if [[ -f "$ROOT/results/work/proxy.pid" ]]; then
    kill "$(cat "$ROOT/results/work/proxy.pid")" 2>/dev/null || true
  fi
  pkill -f log_proxy.py 2>/dev/null || true
  sleep 1
  python3 "$ROOT/scripts/log_proxy.py" "$ROOT/results/$lane/proxy.jsonl" \
    >"$ROOT/results/$lane/proxy.stdout" 2>"$ROOT/results/$lane/proxy.stderr" &
  echo $! >"$ROOT/results/$lane/proxy.pid"
  sleep 1
}

run_pi_lane() {
  local lane="$1"
  export LANE="$lane"
  mkdir -p "$ROOT/results/$lane"
  echo "$lane START $(NOW)" | tee "$ROOT/results/$lane/status.txt"
  bash "$ROOT/scripts/run_pi_task.sh" P-short
  echo "P-short done $(NOW)" | tee -a "$ROOT/results/$lane/status.txt"
  bash "$ROOT/scripts/run_pi_task.sh" P-loop
  echo "$lane OK $(NOW)" | tee -a "$ROOT/results/$lane/status.txt"
}

cleanup() {
  echo "cleanup restore $(NOW)"
  ssh hhtele@192.168.10.29 'bash /tmp/4090_lucebox_ctl.sh restore' || true
  bash "$ROOT/scripts/ensure_tunnel.sh" || true
}
trap cleanup EXIT

echo "LUCEBOX_PI_START $(NOW)" | tee "$ROOT/results/lucebox-status.txt"
bash "$ROOT/scripts/ensure_tunnel.sh"

ssh hhtele@192.168.10.29 'bash /tmp/4090_lucebox_ctl.sh start-off'
sleep 2
bash "$ROOT/scripts/ensure_tunnel.sh"
restart_proxy lucebox-off
run_pi_lane lucebox-off

ssh hhtele@192.168.10.29 'bash /tmp/4090_lucebox_ctl.sh start-on'
sleep 2
bash "$ROOT/scripts/ensure_tunnel.sh"
restart_proxy lucebox-on
run_pi_lane lucebox-on

echo "LUCEBOX_PI_OK $(NOW)" | tee -a "$ROOT/results/lucebox-status.txt"
