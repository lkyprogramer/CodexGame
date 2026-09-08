#!/usr/bin/env bash
# Pi Java x3 against SERVER_URL via PI_CODING_AGENT_DIR. BACKEND=work|ninfer
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIX="$(cd "$ROOT/../../docs/qwen38-4090-vllm-extreme-v1.0/fixtures" && pwd)"
export PATH="/Users/luo/.nvm/versions/node/v22.19.0/bin:$PATH"
BACKEND="${BACKEND:?}"
THINKING="${THINKING:-off}"
RES="${RESULTS_ROOT:-$ROOT/results}/$BACKEND"
WORK="$ROOT/.state/pi-work/${BACKEND}-${THINKING}"
mkdir -p "$RES" "$WORK"
export PI_CODING_AGENT_DIR="${PI_CODING_AGENT_DIR:-$ROOT/pi-config/$BACKEND}"
export PI_OFFLINE=1 PI_SKIP_VERSION_CHECK=1 PI_TELEMETRY=0
MODEL="${PI_MODEL:?}"
PROVIDER="${PI_PROVIDER:?}"
echo 'case,pi_exit,verify_exit,protected_ok,source_changed,elapsed_s,tool_calls,turns,prompt_tokens_sum,completion_tokens_sum' > "$RES/pi_cases.csv"

for src in "$FIX"/java-agent-*; do
  name=$(basename "$src")
  dst="$WORK/$name"
  rm -rf "$dst"
  cp -a "$src" "$dst"
  (cd "$dst" && git init -q && git config user.email bench@local && git config user.name bench && git add . && git commit -qm baseline)
  before=$(cd "$dst" && { find src/test -type f; echo verify.sh; } | sort | xargs shasum -a 256 | shasum -a 256 | awk '{print $1}')
  out="$RES/pi/$name"
  mkdir -p "$out"
  start=$(date +%s)
  set +e
  (
    cd "$dst"
    perl -e 'alarm 3600; exec @ARGV' pi --print --mode json --no-session \
      --provider "$PROVIDER" --model "$PROVIDER/$MODEL" \
      --no-extensions --no-skills --thinking "$THINKING" --approve \
      --tools read,bash,edit,write,grep,find,ls \
      --session-dir "$out/sessions" --name "$name" \
      -- "$(cat TASK.md)"
  ) >"$out/pi.jsonl" 2>"$out/stderr.log"
  pirc=$?
  (cd "$dst" && ./verify.sh) >"$out/verify.log" 2>&1
  vrc=$?
  set -e
  elapsed=$(( $(date +%s) - start ))
  after=$(cd "$dst" && { find src/test -type f; echo verify.sh; } | sort | xargs shasum -a 256 | shasum -a 256 | awk '{print $1}')
  protected=true; [[ "$before" == "$after" ]] || protected=false
  changed=false; (cd "$dst" && git diff --quiet -- src/main) || changed=true
  python3 "$ROOT/bench/parse_pi_json.py" "$out/pi.jsonl" >"$out/metrics.json" || echo '{}' >"$out/metrics.json"
  read tools turns < <(python3 - "$out/metrics.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1]))
print(int(m.get("tool_calls") or 0), int(m.get("turns") or 0))
PY
)
  echo "$name,$pirc,$vrc,$protected,$changed,$elapsed,$tools,$turns,," | tee -a "$RES/pi_cases.csv"
  (cd "$dst" && git diff -- src/main) >"$out/changes.patch" || true
  echo "[pi] $name pi=$pirc verify=$vrc protected=$protected changed=$changed elapsed=${elapsed}s tools=$tools turns=$turns"
done
