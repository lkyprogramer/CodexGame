#!/usr/bin/env bash
# T21 draft-precision arm: DSpark acceptance in llama.cpp with three draft GGUFs that differ only
# in precision (07, T21): local-q8_0 (all Q8_0, as Astral), local-bf16 (all BF16), both exported
# from mtp.safetensors with the fold taken from A1's Q8_0 head (t21_shim.py), and unsloth's file
# (layers Q8_0, Markov head BF16, fold from the original BF16 head). Fixed 7 drafts per round
# (--spec-draft-n-max 7), the T21 workloads, one greedy pass. usage: t21_llama_acc.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"; R="$LAB/runs"; D="$MODELS/ista-dspark"
T=$(cat "$R/t21/LATEST"); O="$T/llama-acc"; mkdir -p "$O"; PORT=18997
guard || exit 3
sha256sum "$D"/dspark-local-*.gguf "$MODELS/unsloth/Mainline_Support/dspark-Inkling-2-Mini-Q8_0.gguf" > "$O/drafts.sha256"; git -C "$LAB/src/llama.cpp" rev-parse HEAD > "$O/llama.txt"
wait_up() { for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && return 0; sleep 1; done; return 1; }
for C in local-q8_0 local-bf16 unsloth; do
  case $C in unsloth) DS="$MODELS/unsloth/Mainline_Support/dspark-Inkling-2-Mini-Q8_0.gguf";; *) DS="$D/dspark-$C.gguf";; esac
  "$BIN/llama-server" -m "$A1" -ngl 99 -fa on -c 20480 -np 1 --host 127.0.0.1 --port $PORT --spec-type draft-dspark -md "$DS" -ngld 99 --spec-draft-n-max 7 > "$O/$C.log" 2>&1 & SP=$!
  if wait_up; then "$PY" -I "$LAB/pkg/tools/t21/t21_llama_acc.py" http://127.0.0.1:$PORT "$T/ids.json" "$C" "$O/$C.jsonl" > "$O/$C.txt" 2>&1; echo "$C rc=$?"; else echo "$C not up"; tail -5 "$O/$C.log"; fi
  kill $SP 2> /dev/null; wait $SP 2> /dev/null; sleep 3
done
"$PY" -I - "$O" << 'EOF'
import json, os, sys, statistics as st
O = sys.argv[1]
rows = {c: [json.loads(l) for l in open(os.path.join(O, c + ".jsonl"))] for c in ("local-q8_0", "local-bf16", "unsloth") if os.path.exists(os.path.join(O, c + ".jsonl"))}
print("%-11s" % "" + "".join("%22s" % s for s in ("sn", "sc", "ln", "lc", "all")))
for c, rs in rows.items():
    out = []
    for s in ("sn", "sc", "ln", "lc", None):
        x = [r for r in rs if s is None or r["set"] == s]
        dn, da = sum(r["draft_n"] or 0 for r in x), sum(r["draft_acc"] or 0 for r in x)
        out.append("%7.3f acc %6.1f t/s" % (da / dn if dn else float("nan"), st.mean(r["tps"] for r in x)))
    print("%-11s" % c + "".join("%22s" % v for v in out))
EOF
guard
