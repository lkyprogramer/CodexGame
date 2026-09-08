#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$ROOT/scripts/common.sh"; load_bench_env "${1:-}"
PI_RES="$ROOT/results/pi"; WORK="$ROOT/.state/pi-work"; mkdir -p "$PI_RES" "$WORK"
PI_PATH=$(command -v "$PI_BIN" 2>/dev/null || true)
if [ -z "$PI_PATH" ]; then echo "Pi executable not found: $PI_BIN"; exit 9; fi
PI_HOME=$(python3 "$ROOT/scripts/configure_pi_test_home.py")
: > "$ROOT/results/pi_cases.csv"
echo 'case,pi_exit,verify_exit,protected_ok,source_changed,elapsed_s,tool_calls,input_tokens,output_tokens' >> "$ROOT/results/pi_cases.csv"
for src in "$ROOT"/fixtures/java-agent-*; do
  name=$(basename "$src"); dst="$WORK/$name"; rm -rf "$dst"; cp -a "$src" "$dst"
  cd "$dst"; git init -q; git config user.email bench@local; git config user.name bench; git add .; git commit -qm baseline
  before=$( (find src/test -type f -print0; printf '%s\0' verify.sh) | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
  prompt=$(cat TASK.md)
  out="$PI_RES/$name"; mkdir -p "$out"
  start=$(date +%s)
  set +e
  HOME="$PI_HOME" PI_CODING_AGENT_DIR="$PI_HOME/.pi/agent" PI_SKIP_VERSION_CHECK=1 PI_TELEMETRY=0 \
    timeout "${PI_CASE_TIMEOUT_SEC}s" "$PI_PATH" --mode json --no-session \
      --provider "$PI_PROVIDER" --model "$PI_PROVIDER/$PI_MODEL" --thinking "$PI_THINKING" \
      --tools read,bash,edit,write,grep,find,ls "$prompt" > "$out/pi.jsonl" 2> "$out/stderr.log"
  pirc=$?
  ./verify.sh > "$out/verify.log" 2>&1; vrc=$?
  set -e
  elapsed=$(( $(date +%s)-start ))
  after=$( (find src/test -type f -print0; printf '%s\0' verify.sh) | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
  protected=true; [ "$before" = "$after" ] || protected=false
  changed=false; git diff --quiet -- src/main || changed=true
  python3 "$ROOT/bench/parse_pi_json.py" "$out/pi.jsonl" > "$out/metrics.json" || echo '{}' > "$out/metrics.json"
  read tools input output < <(python3 - "$out/metrics.json" <<'PY'
import json,sys
m=json.load(open(sys.argv[1])); u=m.get('usage') or {}
def pick(*ks):
 for k in ks:
  v=u.get(k)
  if isinstance(v,(int,float)): return int(v)
 return 0
print(m.get('tool_calls',0), pick('input','input_tokens','prompt_tokens'), pick('output','output_tokens','completion_tokens'))
PY
)
  echo "$name,$pirc,$vrc,$protected,$changed,$elapsed,$tools,$input,$output" >> "$ROOT/results/pi_cases.csv"
  git diff > "$out/changes.patch" || true
  echo "[pi] $name pi=$pirc verify=$vrc protected=$protected changed=$changed elapsed=${elapsed}s tools=$tools"
done
