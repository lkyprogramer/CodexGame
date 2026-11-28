#!/usr/bin/env bash
# T43 Phase 0-A: DFlash2 (A5) vs DSpark acceptance and speed in llama.cpp b12823 (first release with
# PR #33073 is b12785) on A1, greedy, fixed 7 drafts per round, the T21 workloads (sn / sc / ln / lc),
# one pass each. Arms: none (no draft), dspark (local Q8_0 export, the same weights as Astral's draft),
# dflash2-q8_0, dflash2-bf16 (t43_shim.py + convert_hf_to_gguf.py). usage: t43_llama_acc.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; LL="$LAB/src/llama.cpp-b12823"; BIN="$LL/build/bin"
PY="$LAB/venv/bin/python"; R="$LAB/runs"; G="$MODELS/dflash2/gguf"; PORT=18996
O="$R/t43/$(date -u +%Y%m%dT%H%M%SZ)-acc"; mkdir -p "$O"; echo "$O" > "$R/t43/LATEST_acc"
IDS="$(cat "$R/t21/LATEST")/ids.json"
guard || exit 3
{ echo "llama.cpp b12823"; sha256sum "$BIN/llama-server" "$A1" "$G"/dflash2-*.gguf "$MODELS/ista-dspark/dspark-local-q8_0.gguf" "$IDS"; } > "$O/identity.txt"
wait_up() { for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && return 0; sleep 1; done; return 1; }
rc_all=0
for C in ${ARMS:-none dspark dflash2-q8_0 dflash2-bf16}; do
  case $C in
    none) X=();;
    dspark) X=(--spec-type draft-dspark -md "$MODELS/ista-dspark/dspark-local-q8_0.gguf" -ngld 99 --spec-draft-n-max 7);;
    dflash2-*) X=(--spec-type draft-dflash2 -md "$G/$C.gguf" -ngld 99 --spec-draft-n-max 7);;
  esac
  "$BIN/llama-server" -m "$A1" -ngl 99 -fa on -c 20480 -np 1 --host 127.0.0.1 --port $PORT "${X[@]}" > "$O/$C.log" 2>&1 & SP=$!
  if wait_up; then "$PY" -I "$LAB/pkg/tools/t43/t43_llama_acc.py" http://127.0.0.1:$PORT "$IDS" "$C" "$O/$C.jsonl" > "$O/$C.txt" 2>&1; r=$?; echo "$C rc=$r" | tee -a "$O/STATUS"; [ $r -eq 0 ] || rc_all=1
  else echo "$C not up" | tee -a "$O/STATUS"; tail -5 "$O/$C.log"; rc_all=1; fi
  kill $SP 2> /dev/null; wait $SP 2> /dev/null; sleep 3
done
"$PY" -I "$LAB/pkg/tools/t43/t43_summary.py" "$O" | tee "$O/summary.txt"
guard || exit 3
exit $rc_all
