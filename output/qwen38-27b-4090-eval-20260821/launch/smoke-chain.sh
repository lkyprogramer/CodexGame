#!/usr/bin/env bash
# Sequential QCB smoke for S-list. Downloads run in parallel elsewhere.
# Restores WORK on exit. Long-running: start with nohup.
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
mkdir -p "$LOG" "$BASELINE/config" "$BASELINE/results" "$BASELINE/reports"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/smoke-chain.log"; }

sudo_cmd() {
  echo "$SUDO_PASS" | sudo -S -p "" "$@"
}

port_busy() {
  ss -ltn | grep -q ':18343 '
}

wait_port_free() {
  local i
  for i in $(seq 1 60); do
    port_busy || return 0
    sleep 1
  done
  log "WARN port 18343 still busy"
  return 1
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
  tail -n 40 "$LOG/eval-$cand.out" | tee -a "$LOG/smoke-chain.log" || true
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

wait_file() {
  local path="$1" name="$2"
  local i=0
  while [[ ! -f "$path" ]]; do
    if (( i % 30 == 0 )); then
      log "waiting for $name ($path)"
    fi
    sleep 10
    i=$((i + 1))
    if (( i > 720 )); then
      log "ERROR timeout waiting for $name"
      return 1
    fi
  done
  # aria2c uses .aria2 sidecar until finished
  while [[ -f "${path}.aria2" ]]; do
    sleep 10
  done
  log "have $name"
}

file_sha() {
  sha256sum "$1" | awk '{print $1}'
}

write_toml() {
  local id="$1" file="$2" sha="$3" quant="$4" template="$5" mtp="$6" notes="$7"
  cat >"$BASELINE/config/${id}.toml" <<EOF
[model]
id = "${id}"
family = "Qwen3.8-27B"
file = "${file}"
sha256 = "${sha}"
quantization = "${quant}"
template_id = "${template}"
notes = "${notes}"

[endpoint]
base_url = "http://127.0.0.1:18343/v1"
model = "openclaw/Qwen3.8-27B-EVAL"
api_key = "not-needed"
timeout_seconds = 900

[inference]
lane = "optimized"
temperature = 1.0
top_p = 0.95
top_k = 20
min_p = 0.0
seed = 42
max_tokens = 8192
context_size = 112000
reasoning_effort = "medium"
mtp_enabled = ${mtp}
tool_mode = true
max_tool_calls = 40
max_retries = 1
system_prompt_file = "config/system-prompt.txt"
extra_body = { chat_template_kwargs = { enable_thinking = true, reasoning_effort = "medium", preserve_thinking = false } }
EOF
}

preflight() {
  local cand="$1"
  local models props
  models="$(curl -sf --max-time 5 http://127.0.0.1:18343/v1/models)"
  echo "$models" | grep -q 'Qwen3.8-27B-EVAL' || { log "preflight models fail"; return 1; }
  props="$(curl -sf --max-time 5 http://127.0.0.1:18343/props || true)"
  if [[ "$cand" == "sharp" ]]; then
    echo "$props" | grep -q 'Answer directly' || {
      log "ERROR sharp template not applied (no terseness in /props)"
      echo "$props" | head -c 400 | tee -a "$LOG/smoke-chain.log" || true
      return 1
    }
    log "sharp terseness OK"
  fi
  nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv,noheader | tee -a "$LOG/smoke-chain.log"
}

run_smoke() {
  local id="$1"
  local out="$BASELINE/results/${id}"
  local jsonl="$out/${id}-optimized-smoke.jsonl"
  mkdir -p "$out"
  if [[ -f "$jsonl" ]]; then
    local n
    n="$(wc -l <"$jsonl" | tr -d ' ')"
    if [[ "$n" -ge 12 ]]; then
      log "skip $id smoke, already $n lines"
      return 0
    fi
    log "resume $id smoke ($n lines)"
    (cd "$QCB_ROOT" && PYTHONUNBUFFERED=1 python3 scripts/run_suite.py \
      --config "$BASELINE/config/${id}.toml" \
      --suite smoke --seeds 42 --resume \
      --output "$out") | tee -a "$LOG/qcb-${id}-smoke.out"
  else
    log "run $id smoke"
    (cd "$QCB_ROOT" && PYTHONUNBUFFERED=1 python3 scripts/run_suite.py \
      --config "$BASELINE/config/${id}.toml" \
      --suite smoke --seeds 42 \
      --output "$out") | tee -a "$LOG/qcb-${id}-smoke.out"
  fi
  python3 "$QCB_ROOT/scripts/audit_results.py" \
    --root "$QCB_ROOT" --results "$jsonl" --check-artifacts \
    --json "$BASELINE/reports/${id}-smoke-audit.json" \
    | tee -a "$LOG/smoke-chain.log" || true
  python3 "$QCB_ROOT/scripts/generate_report.py" \
    --results "$jsonl" \
    --output "$BASELINE/reports/${id}-smoke.md" \
    --json "$BASELINE/reports/${id}-smoke.json" \
    | tee -a "$LOG/smoke-chain.log" || true
}

trap restore_work EXIT

log "smoke-chain start"
sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
wait_port_free || true

# --- Sharp (jinja only) ---
wait_file "$EVAL_DIR/templates/chat_template.jinja" "sharp jinja"
write_toml \
  "original-sharp-udq4xl-optimized-112k-mtp2" \
  "/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL.gguf" \
  "bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372" \
  "UD-Q4_K_XL" \
  "sharp-v22.1-terse-medium" \
  "true" \
  "Same WORK GGUF; --chat-template-file Sharp v22.1"
start_eval sharp
preflight sharp
run_smoke original-sharp-udq4xl-optimized-112k-mtp2 || log "WARN sharp smoke failed"

# --- grug ---
wait_file "$EVAL_DIR/grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf" "grug Q4_K_M"
write_toml \
  "grug-v1.1-q4km-optimized" \
  "$EVAL_DIR/grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf" \
  "$(file_sha "$EVAL_DIR/grug-v1.1/grug-27b-v1.1-Q4_K_M.gguf")" \
  "Q4_K_M" \
  "grug-native" \
  "false" \
  "grug-v1.1 Q4_K_M; MTP off first round; medium via chat_template_kwargs"
start_eval grug
preflight grug
run_smoke grug-v1.1-q4km-optimized || log "WARN grug smoke failed"

# --- Fable ---
wait_file "$EVAL_DIR/fable-distill/Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf" "fable Q4_K_M"
write_toml \
  "fable-q4km-optimized" \
  "$EVAL_DIR/fable-distill/Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf" \
  "$(file_sha "$EVAL_DIR/fable-distill/Qwen3.8-27B-Fable-Distill-Q4_K_M.gguf")" \
  "Q4_K_M" \
  "fable-native-medium-override" \
  "true" \
  "Fable-Distill Q4_K_M; author default xhigh overridden to medium; MTP n=2"
start_eval fable
preflight fable
run_smoke fable-q4km-optimized || log "WARN fable smoke failed"

# --- Salience ---
wait_file "$EVAL_DIR/salience-r5/vectionlabs_Salience-27B-R5-Q4_K_M.gguf" "salience Q4_K_M"
write_toml \
  "salience-r5-q4km-optimized" \
  "$EVAL_DIR/salience-r5/vectionlabs_Salience-27B-R5-Q4_K_M.gguf" \
  "$(file_sha "$EVAL_DIR/salience-r5/vectionlabs_Salience-27B-R5-Q4_K_M.gguf")" \
  "Q4_K_M" \
  "salience-native" \
  "true" \
  "Salience-27B-R5 bartowski Q4_K_M; --jinja; MTP n=2; medium"
start_eval salience
preflight salience
run_smoke salience-r5-q4km-optimized || log "WARN salience smoke failed"

# --- Cold Fusion MTP ---
CF="$EVAL_DIR/cold-fusion-v1.1/Qwen3.8-27B-Cold-Fusion-GAIN-V1.1-NM-DAU-NEO-MAX-NEO-MTP-Q4_K_M.gguf"
wait_file "$CF" "coldfusion MTP Q4_K_M"
export COLDFUSION_GGUF="$CF"
write_toml \
  "coldfusion-v1.1-q4km-mtp-optimized" \
  "$CF" \
  "$(file_sha "$CF")" \
  "Q4_K_M-MTP" \
  "coldfusion-native-medium-override" \
  "true" \
  "Cold Fusion V1.1 NEO-MAX MTP Q4_K_M; author default xhigh overridden to medium"
start_eval coldfusion
preflight coldfusion
run_smoke coldfusion-v1.1-q4km-mtp-optimized || log "WARN coldfusion smoke failed"

log "all smokes attempted"
# EXIT trap restores WORK
