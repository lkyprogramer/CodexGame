#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NOW() { date +%Y-%m-%dT%H:%M:%S; }
scp -o ConnectTimeout=10 "$ROOT/scripts/4090_dflash2_ctl.sh" hhtele@192.168.10.29:/tmp/4090_dflash2_ctl.sh
ssh hhtele@192.168.10.29 'chmod +x /tmp/4090_dflash2_ctl.sh'

cleanup() {
  echo "cleanup restore $(NOW)"
  ssh hhtele@192.168.10.29 'bash /tmp/4090_dflash2_ctl.sh restore' || true
  bash "$ROOT/scripts/ensure_tunnel.sh" || true
}
trap cleanup EXIT

echo "DFLASH2_PI_START $(NOW)" | tee "$ROOT/results/dflash2-status.txt"
bash "$ROOT/scripts/ensure_tunnel.sh"
ssh hhtele@192.168.10.29 'bash /tmp/4090_dflash2_ctl.sh start 4 160000'
sleep 2
bash "$ROOT/scripts/ensure_tunnel.sh"

pkill -f log_proxy.py 2>/dev/null || true
mkdir -p "$ROOT/results/dflash2-n4"
python3 "$ROOT/scripts/log_proxy.py" "$ROOT/results/dflash2-n4/proxy.jsonl" \
  >"$ROOT/results/dflash2-n4/proxy.stdout" 2>"$ROOT/results/dflash2-n4/proxy.stderr" &
echo $! >"$ROOT/results/dflash2-n4/proxy.pid"
sleep 1

export LANE=dflash2-n4
echo "dflash2-n4 START $(NOW)" | tee "$ROOT/results/dflash2-n4/status.txt"
bash "$ROOT/scripts/run_pi_task.sh" P-short
echo "P-short done $(NOW)" | tee -a "$ROOT/results/dflash2-n4/status.txt"
bash "$ROOT/scripts/run_pi_task.sh" P-loop
echo "dflash2-n4 OK $(NOW)" | tee -a "$ROOT/results/dflash2-n4/status.txt"
echo "DFLASH2_PI_OK $(NOW)" | tee -a "$ROOT/results/dflash2-status.txt"
