#!/usr/bin/env bash
# T15: read-only probes (fork `astral trace`, docs/trace.md). Checks on the 80 set-C positions of
# T19 (manifest_c.tsv): (1) probes off: step / prefill logits of this binary equal T19's
# (fork f8c976e) bit for bit; (2) probes on: the probed steps' logits equal the plain step dump;
# (3) graph vs eager (ASTRAL_NO_GRAPH=1) step logits, reported separately; (4) decode speed with
# probes off. The trace itself is the T15 deliverable for R2 / R3 / R5 / R8.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"
C="$(cat $LAB/runs/t19/LATEST_C)"; M="$C/manifest_c.tsv"; W1="$(cat $LAB/runs/w1/LATEST)"
O="$LAB/runs/t15/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t15/LATEST"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; sha256sum "$M"; echo "baseline: $C/as1 ($(head -1 $C/identity.txt))"; } > "$O/identity.txt"
"$AST" dump-final-logits "$A1" "$M" "$O/off" > "$O/off.log" 2>&1; st off $?
ASTRAL_NO_GRAPH=1 "$AST" dump-final-logits "$A1" "$M" "$O/eager" > "$O/eager.log" 2>&1; st eager $?
ASTRAL_TRACE_VALIDATE=all "$AST" trace "$A1" "$M" "$O/trace" > "$O/trace.log" 2>&1; st trace $?
cmpdir() {  # <label> <dir a> <kind a> <dir b> <kind b>
  local n=0 d=0
  for f in "$2"/*."$3".f32; do b=$(basename "$f" ".$3.f32"); n=$((n+1)); cmp -s "$f" "$4/$b.$5.f32" || d=$((d+1)); done
  echo "$1: $d of $n differ"
}
{ cmpdir "probes off vs T19 baseline, step" "$O/off" step "$C/as1" step
  cmpdir "probes off vs T19 baseline, prefill" "$O/off" prefill "$C/as1" prefill
  cmpdir "probes on (trace) vs probes off, step" "$O/trace" trace "$O/off" step
  cmpdir "eager vs graph, step" "$O/eager" step "$O/off" step
  cmpdir "eager vs graph, prefill (both eager; control)" "$O/eager" prefill "$O/off" prefill; } > "$O/bitwise.txt"
IDS=$(tail -1 "$W1/ids.txt" | tr -d '[],')
for i in 1 2 3; do "$AST" generate "$A1" 128 $IDS 2>&1 | grep "tok/s"; done > "$O/decode.txt"; st decode $?
"$PY" -I "$LAB/pkg/tools/t15/t15_summary.py" "$O/trace/trace.jsonl" > "$O/summary.txt" 2>&1; st summary $?
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O/bitwise.txt" "$O/decode.txt"
