#!/usr/bin/env bash
# T25 long context, stage 1 (GPU): dense diagnosis on the set-D token sequences of T20 (the same
# chat-templated documents, positions FIRST..n-2). Per document: llama.cpp -ub 1 and -ub 512
# (t25_dense), Astral token-by-token and the serving path (prefill of FIRST tokens, then decode;
# dump-logits with ASTRAL_DUMP_FIRST); the prefill path every STEP tokens and at T20's set-D
# lengths (Astral dump-final-logits prefill, llama.cpp final_logits batch). Comparisons with
# t25_kld.py; large files are deleted after each document (their SHA256 is kept).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; T="$LAB/pkg/tools/t25"
LL="$LAB/src/llama.cpp"; FL="$LAB/runs/final_logits"; DENSE="$LAB/runs/t25_dense"
T20=$(cat "$LAB/runs/t20/LATEST"); FIRST=${FIRST:-512}; STEP=${STEP:-64}
O="$LAB/runs/t25/$(date -u +%Y%m%dT%H%M%SZ)-d"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t25/LATEST_D"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard || exit 3; st guard-start 0
if [ ! -x "$DENSE" ] || [ "$T/t25_dense.cpp" -nt "$DENSE" ]; then
  g++ -O2 -std=c++17 -I"$LL/include" -I"$LL/ggml/include" "$T/t25_dense.cpp" -L"$LL/build/bin" -lllama -Wl,-rpath,"$LL/build/bin" -o "$DENSE"; st build-dense $?
fi
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; git -C "$LL" rev-parse HEAD; sha256sum "$AST" "$DENSE" "$FL" "$T20/ids_d.json" "$T20/manifest_d.tsv"; echo "first $FIRST step $STEP"; } > "$O/identity.txt"
ND=$("$PY" -I -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$T20/ids_d.json")
for i in $(seq 0 $((ND - 1))); do
  W="$O/d$i"; mkdir -p "$W/asp" "$W/llb"
  "$PY" -I - "$T20/ids_d.json" "$T20/manifest_d.tsv" $i $FIRST $STEP "$W" <<'EOF'
import json, sys
ids_f, man, i, first, step, w = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
ids = json.load(open(ids_f))[i]["ids"]
lens = set(range(first + step, len(ids), step))
for line in open(man):
    name, ls, _ = line.split("\t", 2)
    if name.startswith("d%02d_" % i):
        lens |= {int(x) for x in ls.split(",") if first < int(x) < len(ids)}
open(w + "/ids.txt", "w").write(" ".join(map(str, ids)) + "\n")
open(w + "/sample.tsv", "w").write("d%d\t%s\t%s\n" % (i, ",".join(map(str, sorted(lens))), " ".join(map(str, ids))))
print("d%d: %d tokens, %d sampled prefill lengths" % (i, len(ids), len(lens)))
EOF
  "$DENSE" "$A1" "$W/ids.txt" $FIRST 1 "$W/ll1.bin" > "$W/ll1.log" 2>&1; st d$i-ll1 $?
  "$DENSE" "$A1" "$W/ids.txt" $FIRST 512 "$W/ll512.bin" > "$W/ll512.log" 2>&1; st d$i-ll512 $?
  ASTRAL_DUMP_FIRST=$FIRST "$AST" dump-logits "$A1" "$W/ll1.bin" "$W/as_step.bin" > "$W/as_step.log" 2>&1; st d$i-as-step $?
  ASTRAL_DUMP_FIRST=$FIRST ASTRAL_DUMP_PREFILL=1 "$AST" dump-logits "$A1" "$W/ll1.bin" "$W/as_serve.bin" > "$W/as_serve.log" 2>&1; st d$i-as-serve $?
  ASTRAL_DUMP_KINDS=prefill "$AST" dump-final-logits "$A1" "$W/sample.tsv" "$W/asp" > "$W/asp.log" 2>&1; st d$i-as-prefill $?
  "$FL" "$A1" "$W/sample.tsv" "$W/llb" batch > "$W/llb.log" 2>&1; st d$i-ll-batch $?
  "$PY" -I "$T/t25_kld.py" "$O/d$i.json" \
    "bin:$W/ll1.bin=bin:$W/ll512.bin" "bin:$W/as_step.bin=bin:$W/as_serve.bin" \
    "bin:$W/ll1.bin=bin:$W/as_step.bin" "bin:$W/ll1.bin=bin:$W/as_serve.bin" "bin:$W/ll512.bin=bin:$W/as_serve.bin" \
    "bin:$W/ll1.bin=f32:$W/llb:d$i:batch" "bin:$W/as_step.bin=f32:$W/asp:d$i:prefill" "bin:$W/ll1.bin=f32:$W/asp:d$i:prefill" \
    > "$O/d$i.txt" 2>&1; st d$i-compare $?
  ( cd "$W" && sha256sum *.bin > bins.sha256 ); rm -rf "$W"/*.bin "$W/asp" "$W/llb"
done
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O"/d*.txt
