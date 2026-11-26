#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
guard || exit 3
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"; R="$LAB/runs"
W1=$(cat "$R/w1/LATEST"); O=$(cat "$R/w2/LATEST")
mkdir -p "$O/seq-old" && cp "$O"/seq/*.ids "$O/seq/ref.json" "$O/seq-old/"
"$BIN/llama-server" -m "$A1" -ngl 99 -c 4096 --host 127.0.0.1 --port 18999 -np 1 > "$O/llama-server-2.log" 2>&1 &
SP=$!; for i in $(seq 1 240); do curl -sf http://127.0.0.1:18999/health >/dev/null && break; sleep 1; done
"$PY" -I "$R/refseq.py" http://127.0.0.1:18999 "$W1/v2-llama.json" "$O/seq" 500; echo "refseq rc=$?"
kill $SP; wait $SP 2>/dev/null
for f in "$O"/seq-old/*.ids; do cmp -s "$f" "$O/seq/$(basename $f)" || echo "SEQ CHANGED $f"; done
for f in "$O"/seq/*.ids; do i=$(basename "$f" .ids); "$AST" cmp-prefill "$A1" $(cat "$f") > "$O/seq/cmp_$i.txt" 2>&1; done
"$PY" -I "$R/v567.py" "$O/seq" > "$O/v567.json"; echo "v567 rc=$?"
guard
