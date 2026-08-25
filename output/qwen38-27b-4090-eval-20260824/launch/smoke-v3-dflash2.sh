#!/usr/bin/env bash
# QCB smoke 12×seed42 for V3 200K MTP then analogalok DFlash2.
# Restores WORK on EXIT. Does not overwrite WORK baseline jsonl.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAUNCH="$ROOT/launch"
LOG="$ROOT/logs"
PIDFILE="$LOG/eval.pid"
SUDO_PASS="${SUDO_PASS:-hhtele}"
QCB_ROOT="${QCB_ROOT:-/home/hhtele/qcb-4090}"
OUT_ROOT="${OUT_ROOT:-/home/hhtele/qcb-4090-v3-eval}"
WORK_SMOKE="${WORK_SMOKE:-/home/hhtele/qcb-4090-baseline/results/work/work-udq4xl-optimized-112k-mtp2-optimized-smoke.jsonl}"
V3=/data/models/qwen/qwen38/Qwen3.8-27B-UD-Q4_K_XL-dv3.gguf
EXPECT_V3=3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e
ID_MTP="v3-udq4xl-200k-q4-mtp2"
ID_DF="v3-udq4xl-200k-q4-dflash2-q2"
mkdir -p "$LOG" "$OUT_ROOT/config" "$OUT_ROOT/results" "$OUT_ROOT/reports" "$OUT_ROOT/environment"

log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$LOG/smoke-v3-dflash2.log"; }
sudo_cmd() { echo "$SUDO_PASS" | sudo -S -p "" "$@"; }

stop_eval() {
  if [[ -f "$PIDFILE" ]]; then
    local pid; pid="$(cat "$PIDFILE" || true)"
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      log "stop eval pid=$pid"
      kill "$pid" 2>/dev/null || true
      sleep 2
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PIDFILE"
  fi
  local i
  for i in $(seq 1 60); do
    ss -ltn | grep -q ':18343 ' || return 0
    sleep 1
  done
  log "WARN port 18343 still busy"
}

start_script() {
  local script="$1" name="$2"
  stop_eval
  log "start $name"
  nohup "$script" >>"$LOG/eval-$name.out" 2>&1 &
  echo $! >"$PIDFILE"
  local i
  for i in $(seq 1 180); do
    if curl -sf --max-time 2 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-EVAL'; then
      log "$name up (${i}s)"
      return 0
    fi
    if ! kill -0 "$(cat "$PIDFILE" 2>/dev/null || echo)" 2>/dev/null; then
      log "ERROR $name process died (${i}s)"
      tail -n 40 "$LOG/eval-$name.out" | tee -a "$LOG/smoke-v3-dflash2.log" || true
      return 1
    fi
    sleep 2
  done
  log "ERROR $name did not come up"
  tail -n 40 "$LOG/eval-$name.out" | tee -a "$LOG/smoke-v3-dflash2.log" || true
  return 1
}

restore_work() {
  log "restore WORK"
  stop_eval || true
  sudo_cmd systemctl start openclaw-qwen38-work-64k.service || true
  local i
  for i in $(seq 1 60); do
    if curl -sf --max-time 3 http://127.0.0.1:18343/v1/models | grep -q 'Qwen3.8-27B-WORK'; then
      log "WORK restored"
      return 0
    fi
    sleep 2
  done
  log "WARN WORK restore not confirmed"
}

write_toml() {
  local id="$1" ctx="$2" mtp="$3" notes="$4"
  cat >"$OUT_ROOT/config/${id}.toml" <<EOF
[model]
id = "${id}"
family = "Qwen3.8-27B"
file = "${V3}"
sha256 = "${EXPECT_V3}"
quantization = "UD-Q4_K_XL-Dynamic-V3"
template_id = "official-jinja-medium"
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
context_size = ${ctx}
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
  local want_ctx="$1"
  python3 - "$want_ctx" <<'PY'
import json, sys, urllib.request
want = int(sys.argv[1])
d = json.loads(urllib.request.urlopen("http://127.0.0.1:18343/v1/models", timeout=5).read().decode())
meta = (d.get("data") or [{}])[0].get("meta") or {}
nctx = int(meta.get("n_ctx") or 0)
mid = (d.get("data") or [{}])[0].get("id")
print(f"preflight model={mid} n_ctx={nctx} want>={want}")
if "Qwen3.8-27B-EVAL" not in str(mid):
    raise SystemExit("wrong alias")
if nctx < want:
    raise SystemExit(f"n_ctx {nctx} < {want}")
PY
  nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv | tee -a "$LOG/smoke-v3-dflash2.log"
  python3 "$QCB_ROOT/scripts/collect_environment.py" \
    --server-command "$(tr '\0' ' ' < /proc/"$(cat "$PIDFILE")"/cmdline)" \
    --output "$OUT_ROOT/environment/env-$(date -u +%H%M%S).json" || true
}

run_smoke() {
  local id="$1"
  local out="$OUT_ROOT/results/${id}"
  local jsonl="$out/${id}-optimized-smoke.jsonl"
  mkdir -p "$out"
  local extra=()
  if [[ -f "$jsonl" ]]; then
    local n; n="$(wc -l <"$jsonl" | tr -d ' ')"
    if [[ "$n" -ge 12 ]]; then
      log "skip $id smoke, already $n lines"
    else
      log "resume $id smoke ($n lines)"
      extra=(--resume)
      (cd "$QCB_ROOT" && PYTHONUNBUFFERED=1 python3 scripts/run_suite.py \
        --config "$OUT_ROOT/config/${id}.toml" \
        --suite smoke --seeds 42 "${extra[@]}" \
        --output "$out") | tee -a "$LOG/qcb-${id}-smoke.out"
    fi
  else
    log "run $id smoke"
    (cd "$QCB_ROOT" && PYTHONUNBUFFERED=1 python3 scripts/run_suite.py \
      --config "$OUT_ROOT/config/${id}.toml" \
      --suite smoke --seeds 42 \
      --output "$out") | tee -a "$LOG/qcb-${id}-smoke.out"
  fi
  python3 "$QCB_ROOT/scripts/audit_results.py" \
    --root "$QCB_ROOT" --results "$jsonl" --check-artifacts \
    --json "$OUT_ROOT/reports/${id}-smoke-audit.json" \
    | tee -a "$LOG/smoke-v3-dflash2.log" || true
  python3 "$QCB_ROOT/scripts/generate_report.py" \
    --results "$jsonl" \
    --output "$OUT_ROOT/reports/${id}-smoke.md" \
    --json "$OUT_ROOT/reports/${id}-smoke.json" \
    | tee -a "$LOG/smoke-v3-dflash2.log" || true
  if [[ -f "$WORK_SMOKE" ]]; then
    python3 "$QCB_ROOT/scripts/compare_models.py" \
      --model-a "$WORK_SMOKE" \
      --model-b "$jsonl" \
      --output "$OUT_ROOT/reports/compare-work-vs-${id}.md" \
      --json "$OUT_ROOT/reports/compare-work-vs-${id}.json" \
      | tee -a "$LOG/smoke-v3-dflash2.log" || true
  fi
}

trap restore_work EXIT
log "smoke-v3-dflash2 start"
got="$(sha256sum "$V3" | awk '{print $1}')"
log "V3 sha $got"
if [[ "$got" != "$EXPECT_V3" ]]; then
  log "ERROR V3 sha mismatch, abort"
  exit 1
fi

sudo_cmd systemctl stop openclaw-qwen38-work-64k.service
for i in $(seq 1 40); do ss -ltn | grep -q ':18343 ' || break; sleep 1; done

write_toml "$ID_MTP" 200000 true "Dynamic V3 UD-Q4_K_XL; 200K q4 KV; native MTP n=2; same OpenClaw sampling as WORK"
if start_script "$LAUNCH/production-200k-mtp.sh" "mtp-c200000"; then
  preflight 200000
  run_smoke "$ID_MTP" || log "WARN smoke $ID_MTP failed"
else
  log "ERROR 200k MTP did not start — skip its smoke"
fi

write_toml "$ID_DF" 200000 false "Dynamic V3 + analogalok DFlash2 Q2_K; PR27342 binary; 200K q4 KV n-max 3 (250K load-verified; smoke uses 200K for VRAM margin)"
export CTX=200000
export DFLASH2_DRAFT=/data/models/qwen/qwen38/Qwen3.8-27B-DFlash2-Q2_K.gguf
if start_script "$LAUNCH/production-alok-dflash2-pr27342.sh" "dflash2-q2-c200000"; then
  preflight 200000
  run_smoke "$ID_DF" || log "WARN smoke $ID_DF failed"
else
  log "ERROR DFlash2 200k did not start — skip its smoke"
fi

log "smoke-v3-dflash2 done"
