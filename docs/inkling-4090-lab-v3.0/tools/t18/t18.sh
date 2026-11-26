#!/usr/bin/env bash
# T18: configurable pass count (fork ASTRAL_PASSES) and the varloop checkpoint (A4).
# (1) A1 at its default 3 passes is bit-identical to T15's build (step / prefill, set C), also with
#     ASTRAL_PASSES=3 given explicitly; (2) A4's tensor table against A1's; (3) A4 at R = 1..5
#     (training range) and 6, 10 (extrapolation), A1 at R = 1, 2 (truncation control): token-by-token
#     log-probs on the W1 corpus (c512 x 8, 2040 positions) -> perplexity, KL against the same model
#     at R = 3 and against llama.cpp A1; decode speed; 128-token greedy agreement with R = 3;
#     (4) prefill vs step at R != 3 on 4 set-C sequences (the rebuilt slots / KV / conv / messages).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; A4="$MODELS/varloop-native"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; BC="$LAB/src/astral/bench/llamacpp_compare"
W1="$(cat $LAB/runs/w1/LATEST)"; BASE="$(ls -d $W1/golden/*-golden | tail -1)/kld_base_c512x8.bin"
C="$(cat $LAB/runs/t19/LATEST_C)"; T15="$(cat $LAB/runs/t15/LATEST)"
O="$LAB/runs/t18/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t18/LATEST"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard; st guard-start $?
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; } > "$O/identity.txt"
cmpdir() { local n=0 d=0; for f in "$2"/*."$3".f32; do b=$(basename "$f" ".$3.f32"); n=$((n+1)); cmp -s "$f" "$4/$b.$3.f32" || d=$((d+1)); done; echo "$1: $d of $n differ"; }
# (1)
"$AST" dump-final-logits "$A1" "$C/manifest_c.tsv" "$O/a1r3" > "$O/a1r3.log" 2>&1; st a1r3 $?
ASTRAL_PASSES=3 "$AST" dump-final-logits "$A1" "$C/manifest_c.tsv" "$O/a1r3x" > "$O/a1r3x.log" 2>&1; st a1r3x $?
{ for k in step prefill; do cmpdir "A1 default vs T15 build, $k" "$O/a1r3" $k "$T15/off"; cmpdir "A1 ASTRAL_PASSES=3 vs T15 build, $k" "$O/a1r3x" $k "$T15/off"; done; } > "$O/bitwise.txt"
# (2)
"$AST" gguf-info "$A1" --tensors > "$O/a1_tensors.txt" 2>&1; "$AST" gguf-info "$A4" --tensors > "$O/a4_tensors.txt" 2>&1; st tensors $?
# (3)
IDS=$(tail -1 "$W1/ids.txt" | tr -d '[],')
run_r() {  # <label> <model> <R>
  ASTRAL_PASSES=$3 "$AST" dump-logits "$2" "$BASE" "$O/$1_r$3.bin" > "$O/$1_r$3.dump.log" 2>&1; st "$1-r$3-dump" $?
  ASTRAL_PASSES=$3 "$AST" generate "$2" 128 $IDS > "$O/$1_r$3.gen.txt" 2>&1; st "$1-r$3-gen" $?
}
for R in 3 1 2 4 5 6 10; do run_r a4 "$A4" $R; done
for R in 3 1 2; do run_r a1 "$A1" $R; done
for m in a4 a1; do for f in "$O"/${m}_r*.bin; do
  b=$(basename "$f" .bin)
  "$PY" -I "$BC/kld_compare.py" "$O/${m}_r3.bin" "$f" > "$O/$b.vs_r3.json"
  "$PY" -I "$BC/kld_compare.py" "$BASE" "$f" > "$O/$b.vs_llama_a1.json"
done; done; st kld $?
sha256sum "$O"/*.bin > "$O/bins.sha256"; rm -f "$O"/*.bin
# (4)
head -4 "$C/manifest_c.tsv" > "$O/m4.tsv"
for R in 1 5; do ASTRAL_PASSES=$R "$AST" dump-final-logits "$A4" "$O/m4.tsv" "$O/pf_r$R" > "$O/pf_r$R.log" 2>&1; st "prefill-r$R" $?
  "$PY" -I "$BC/logit_compare.py" compare "$O/m4.tsv" "$O/pf_r$R:step" "$O/pf_r$R:prefill" "$O/pf_r$R.jsonl" > "$O/pf_r$R.json"; done
"$PY" -I "$LAB/pkg/tools/t18/t18_report.py" "$O" > "$O/report.txt" 2>&1; st report $?
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O/bitwise.txt" "$O/report.txt"
