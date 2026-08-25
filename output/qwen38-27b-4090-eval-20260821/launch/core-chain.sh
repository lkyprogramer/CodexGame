#!/usr/bin/env bash
# Latin-square QCB core for S-list. Seeds 11,29,47 = first 3 latin blocks.
# Restores WORK on exit. Start with nohup.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH="$ROOT/launch"
LOG="$ROOT/logs"
EVAL_DIR="${EVAL_DIR:-/data/models/qwen/qwen38-eval}"
QCB_ROOT="${QCB_ROOT:-/home/hhtele/qcb-4090}"
BASELINE="${BASELINE:-/home/hhtele/qcb-4090-baseline}"
PIDFILE="$LOG/eval.pid"
SUDO_PASS="${SUDO_PASS:-hhtele}"
export CANDIDATE CTX COLDFUSION_GGUF EVAL_DIR
mkdir -p "$LOG" "$BASELINE/results" "$BASELINE/reports"

SEEDS=(11 29 47)
MODELS=(
  original-sharp-udq4xl-optimized-112k-mtp2
  grug-v1.1-q4km-optimized
  fable-q4km-optimized
  salience-r5-q4km-optimized
  coldfusion-v1.1-q4km-mtp-optimized
)

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/core-chain.log"; }

sudo_cmd() {
  echo "$SUDO_PASS" | sudo -S -p "" "$@"
}

port_busy() { ss -ltn | grep -q ':18343 '; }

wait_port_free() {
  local i
  for i in $(seq 1 60); do
    port_busy || return 0
    sleep 1
  done
  log "WARN port 18343 still busy"
  return 1
}

candidate_for() {
  case "$1" in
    original-sharp-udq4xl-optimized-112k-mtp2) echo sharp ;;
    grug-v1.1-q4km-optimized) echo grug ;;
    fable-q4km-optimized) echo fable ;;
    salience-r5-q4km-optimized) echo salience ;;
    coldfusion-v1.1-q4km-mtp-optimized) echo coldfusion ;;
    *) echo "unknown-id $1" >&2; return 1 ;;
  esac
}

stop_eval() {
  if [[ -f "$PIDFILE" ]]; then
    local pid
    pid="$(cat "$PIDFILE" || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      log "stop eval pid=$pid"
      kill "$pid" 2>/dev/null || true
      sleep 2
      if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
      fi
    fi
    rm -f "$PIDFILE"
  fi
  wait_port_free || true
}

start_eval() {
  local cand="$1"
  stop_eval
  export CANDIDATE="$cand"
  if [[ "$cand" == "coldfusion" ]]; then
    export COLDFUSION_GGUF="${COLDFUSION_GGUF:-$EVAL_DIR/cold-fusion-v1.1/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-NEO-MTP-Q4_K_M.gguf}"
  fi
  log "start eval CANDIDATE=$cand"
  nohup "$LAUNCH/production-eval.sh" >>"$LOG/eval-$cand.out" 2>&1 &
  echo $! >"$PIDFILE"
  local i json
  for i in $(seq 1 90); do
    json="$(curl -sf --max-time 2 http://127.0.0.1:18343/v1/models || true)"
    if echo "$json" | grep -q 'Qwen3.8-27B-EVAL'; then
      log "eval up ($i s)"
      return 0
    fi
    sleep 2
  done
  log "ERROR eval did not come up for $cand"
  tail -n 40 "$LOG/eval-$cand.out" | tee -a "$LOG/core-chain.log" || true
  return 1
}

restore_work() {
  log "restore WORK"
  stop_eval || true
  sudo_cmd systemctl start openclaw-qwen38-work-64k.service || true
  local i
  for i in $(seq 1 60); do
    if curl -sf --max-time 2 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-WORK'; then
      log "WORK restored"
      return 0
    fi
    sleep 2
  done
  log "WARN WORK restore not confirmed"
}

preflight() {
  local cand="$1"
  curl -sf --max-time 5 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-EVAL' || {
    log "preflight models fail"
    return 1
  }
  if [[ "$cand" == "sharp" ]]; then
    local props
    props="$(curl -sf --max-time 5 http://127.0.0.1:18343/props || true)"
    echo "$props" | grep -q 'Answer directly' || {
      log "ERROR sharp template not applied"
      return 1
    }
    log "sharp terseness OK"
  fi
  nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv,noheader | tee -a "$LOG/core-chain.log"
}

jsonl_for() {
  local id="$1"
  echo "$BASELINE/results/${id}/${id}-optimized-core.jsonl"
}

seed_count() {
  local jsonl="$1" seed="$2"
  if [[ ! -f "$jsonl" ]]; then
    echo 0
    return
  fi
  python3 - "$jsonl" "$seed" <<'PY'
import json, sys
path, seed = sys.argv[1], int(sys.argv[2])
n = 0
with open(path) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if int(row.get("seed", 0)) == seed:
            n += 1
print(n)
PY
}

run_core_seed() {
  local id="$1" seed="$2"
  local out="$BASELINE/results/${id}"
  local jsonl
  jsonl="$(jsonl_for "$id")"
  mkdir -p "$out"
  local have
  have="$(seed_count "$jsonl" "$seed")"
  if [[ "$have" -ge 32 ]]; then
    log "skip $id seed=$seed, already $have rows"
    return 0
  fi
  log "run $id core seed=$seed (have $have)"
  (cd "$QCB_ROOT" && PYTHONUNBUFFERED=1 python3 scripts/run_suite.py \
    --config "$BASELINE/config/${id}.toml" \
    --suite core --seeds "$seed" --resume \
    --output "$out") | tee -a "$LOG/qcb-${id}-core-s${seed}.out"
  log "done $id seed=$seed lines=$(wc -l <"$jsonl" | tr -d ' ')"
}

report_model() {
  local id="$1"
  local jsonl
  jsonl="$(jsonl_for "$id")"
  [[ -f "$jsonl" ]] || return 0
  python3 "$QCB_ROOT/scripts/audit_results.py" \
    --root "$QCB_ROOT" --results "$jsonl" --check-artifacts \
    --json "$BASELINE/reports/${id}-core-audit.json" \
    | tee -a "$LOG/core-chain.log" || true
  python3 "$QCB_ROOT/scripts/generate_report.py" \
    --results "$jsonl" \
    --output "$BASELINE/reports/${id}-core.md" \
    --json "$BASELINE/reports/${id}-core.json" \
    | tee -a "$LOG/core-chain.log" || true
}

latin_block() {
  local offset="$1"
  local i n=${#MODELS[@]}
  for ((i = 0; i < n; i++)); do
    echo "${MODELS[$(( (i + offset) % n ))]}"
  done
}

CURRENT_CAND=""

ensure_eval() {
  local id="$1"
  local cand
  cand="$(candidate_for "$id")"
  if [[ "$CURRENT_CAND" != "$cand" ]]; then
    start_eval "$cand"
    preflight "$cand"
    CURRENT_CAND="$cand"
  fi
}

trap restore_work EXIT

log "core-chain start latin seeds=${SEEDS[*]}"
sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
wait_port_free || true

offset=0
for seed in "${SEEDS[@]}"; do
  log "==== block seed=$seed offset=$offset ===="
  while read -r id; do
    ensure_eval "$id" || { log "WARN skip $id seed=$seed eval failed"; continue; }
    run_core_seed "$id" "$seed" || log "WARN core failed $id seed=$seed"
  done < <(latin_block "$offset")
  offset=$((offset + 1))
done

for id in "${MODELS[@]}"; do
  report_model "$id" || true
done

log "all core blocks attempted"
# EXIT trap restores WORK
