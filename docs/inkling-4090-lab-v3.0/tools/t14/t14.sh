#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
guard || { echo "DRIVER GUARD FAIL"; exit 3; }
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; DS="$MODELS/unsloth/Mainline_Support/dspark-Inkling-2-Mini-Q8_0.gguf"
AST="$LAB/src/astral/target/release/astral"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"; R="$LAB/runs"
SV="$LAB/src/astral/bench/serving"; O="$R/t14/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$R/t14/LATEST"
REPS=$(printenv REPS || echo 5); PORT=18997
CONFIGS=$(printenv CONFIGS || echo "astral-ar astral-dspark llama-ar llama-dspark-k3 llama-dspark-k6")
gpu() { nvidia-smi --query-gpu=timestamp,memory.used,clocks.sm,clocks.mem,temperature.gpu,power.draw --format=csv,noheader >> "$O/gpu.csv"; }
wait_up() { for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health >/dev/null && return 0; sleep 1; done; return 1; }
mon() { while true; do gpu; sleep 5; done; }
mon & MON=$!
stop() { kill $1 2>/dev/null; wait $1 2>/dev/null; sleep 3; }
LL="-m $A1 -ngl 99 -fa on -c 8192 -np 1 --host 127.0.0.1 --port $PORT"
# prompt ids via Astral /tokenize (V2: identical to llama.cpp)
"$AST" serve "$A1" --checkpoint "$MODELS/inkling-native" --no-draft --host 127.0.0.1 --port $PORT --ctx 8192 > "$O/ids-server.log" 2>&1 & SP=$!
wait_up && "$PY" -I "$R/t14_ids.py" http://127.0.0.1:$PORT "$O/ids.json" "$SV/prompts_set_a.json" "$SV/prompts_set_b.json"
stop $SP
for C in $CONFIGS; do
  EXTRA='{}'
  case $C in
    astral-ar) "$AST" serve "$A1" --checkpoint "$MODELS/inkling-native" --no-draft --host 127.0.0.1 --port $PORT --ctx 8192 > "$O/$C.log" 2>&1 & SP=$!; EXTRA='{"speculative": false}';;
    astral-dspark) "$AST" serve "$A1" --checkpoint "$MODELS/inkling-native" --host 127.0.0.1 --port $PORT --ctx 8192 > "$O/$C.log" 2>&1 & SP=$!;;
    llama-ar) "$BIN/llama-server" $LL > "$O/$C.log" 2>&1 & SP=$!;;
    llama-dspark-k*) "$BIN/llama-server" $LL --spec-type draft-dspark -md "$DS" -ngld 99 --spec-draft-n-max "$(echo $C | sed 's/.*-k//')" > "$O/$C.log" 2>&1 & SP=$!;;
  esac
  if wait_up; then
    "$PY" -I "$R/t14_bench.py" http://127.0.0.1:$PORT "$O/ids.json" $C $REPS "$O/$C.jsonl" "$EXTRA" > "$O/$C.txt" 2>&1; echo "$C rc=$?"
  else
    echo "$C not up"; tail -5 "$O/$C.log"
  fi
  stop $SP
done
kill $MON
guard; echo "guard-end rc=$?"
echo DONE
