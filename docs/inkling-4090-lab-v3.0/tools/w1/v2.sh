#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
guard || exit 3
O=$(cat $LAB/runs/w1/LATEST); A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; BIN="$LAB/src/llama.cpp/build/bin"
P="$LAB/src/astral/bench/serving/prompts_set_a.json"
"$AST" serve "$A1" --checkpoint "$MODELS/inkling-native" --no-draft --host 127.0.0.1 --port 18998 --ctx 4096 > "$O/astral-serve.log" 2>&1 &
SP=$!; for i in $(seq 1 240); do curl -sf http://127.0.0.1:18998/health >/dev/null && break; sleep 1; done
"$LAB/venv/bin/python" -I "$LAB/runs/v2.py" astral http://127.0.0.1:18998 "$P" > "$O/v2-astral.json"; echo "astral rc=$?"
kill $SP; wait $SP 2>/dev/null
"$BIN/llama-server" -m "$A1" -ngl 99 -c 4096 --jinja --host 127.0.0.1 --port 18999 -np 1 > "$O/llama-server-v2.log" 2>&1 &
SP=$!; for i in $(seq 1 240); do curl -sf http://127.0.0.1:18999/health >/dev/null && break; sleep 1; done
"$LAB/venv/bin/python" -I "$LAB/runs/v2.py" llama http://127.0.0.1:18999 "$P" > "$O/v2-llama.json"; echo "llama rc=$?"
kill $SP; wait $SP 2>/dev/null
guard
