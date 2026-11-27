#!/usr/bin/env bash
# T17 pass-key retrieval through astral serve (--no-draft, capacity 132096) at 32K / 64K / 128K,
# depths 0.1 / 0.5 / 0.9; results appended to <run dir>/needle.jsonl, peak memory.used to
# needle_peak.txt. Called by t17b.sh; can be rerun on its own. usage: t17_needle.sh <run dir>
set -u
source "$HOME/inkling-lab-v3/env.sh"
O=$1
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; CK="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"
U="$LAB/pkg/tools/t17/t17_util.py"; I="$LAB/runs/t17/inputs"
rm -f "$O/needle.jsonl" "$O/needle_time.txt"
"$AST" serve "$A1" --checkpoint "$CK" --no-draft --ctx 132096 --port 8790 > "$O/serve.log" 2>&1 & SP=$!
up=1; for i in $(seq 1 180); do curl -sf localhost:8790/health > /dev/null && { up=0; break; }; kill -0 $SP 2>/dev/null || break; sleep 2; done
if [ $up != 0 ]; then echo "server did not come up:"; tail -5 "$O/serve.log"; kill $SP 2>/dev/null; exit 1; fi
nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits -lms 200 > "$O/needle.mem" & MP=$!
rc=0
for C in 32768 65536 131072; do for d in 0.1 0.5 0.9; do
  key=$((10000 + (C / 1024) * 97 + ${d#0.} * 131))
  t0=$(date +%s.%N); "$PY" -I "$U" needle http://localhost:8790 "$I/corpus.txt" "$I/ids.json" $((C - 600)) $d $key >> "$O/needle.jsonl" || rc=1
  echo "$C $d $(awk -v a="$t0" -v b="$(date +%s.%N)" 'BEGIN {print b - a}')" >> "$O/needle_time.txt"
done; done
kill $MP; kill $SP; wait $SP 2>/dev/null
sort -n "$O/needle.mem" | tail -1 > "$O/needle_peak.txt"
exit $rc
