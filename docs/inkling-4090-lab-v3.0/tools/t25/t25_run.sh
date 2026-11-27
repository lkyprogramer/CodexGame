#!/usr/bin/env bash
# T25 long context (GPU): dense comparison on chat-templated long documents (generalises
# t25_d.sh, which ran set D). IDS: ids.json of t20_ids.py (default T20's set D); TAG: case prefix
# (d / e); MAN: a dump manifest whose lengths for case TAG<i> are added to the prefill sample
# (default T20's set-D manifest; "none" for none); GEN: greedy llama.cpp tokens appended to every
# prompt first (t25_dense gen; their positions are then teacher-forced like the prompt's).
# Positions FIRST..n-2. NEGS: optional negative controls "name:VAR=value ..." (the serving path with
# that environment, compared with llama.cpp ub1 as pairs 8, 9, ...; names in negs.txt). Per document: llama.cpp -ub 1 and -ub 512
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
NEGS=${NEGS:-}; IDS=${IDS:-$T20/ids_d.json}; TAG=${TAG:-d}; MAN=${MAN:-$T20/manifest_d.tsv}; GEN=${GEN:-0}
O="$LAB/runs/t25/$(date -u +%Y%m%dT%H%M%SZ)-$TAG"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t25/LATEST_$TAG"
st() { echo "$1 rc=$2" >> "$O/STATUS"; }
guard || exit 3; st guard-start 0
for ng in $NEGS; do echo "${ng%%:*}"; done > "$O/negs.txt"
if [ ! -x "$DENSE" ] || [ "$T/t25_dense.cpp" -nt "$DENSE" ]; then
  g++ -O2 -std=c++17 -I"$LL/include" -I"$LL/ggml/include" "$T/t25_dense.cpp" -L"$LL/build/bin" -lllama -Wl,-rpath,"$LL/build/bin" -o "$DENSE"; st build-dense $?
fi
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; git -C "$LL" rev-parse HEAD; sha256sum "$AST" "$DENSE" "$FL" "$IDS" "$T/t25_kld.py"; [ "$MAN" = none ] || sha256sum "$MAN"; echo "tag $TAG first $FIRST step $STEP gen $GEN"; } > "$O/identity.txt"
ND=$("$PY" -I -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$IDS")
for i in $(seq 0 $((ND - 1))); do
  W="$O/$TAG$i"; mkdir -p "$W/asp" "$W/llb"
  "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[int(sys.argv[2])]['ids'])))" "$IDS" $i > "$W/prompt.txt"
  if [ "$GEN" -gt 0 ]; then "$DENSE" "$A1" "$W/prompt.txt" gen "$GEN" "$W/full.txt" > "$W/gen.log" 2>&1; st $TAG$i-gen $?; else cp "$W/prompt.txt" "$W/full.txt"; fi
  "$PY" -I - "$W/prompt.txt" "$W/full.txt" "$MAN" $TAG $i $FIRST $STEP "$W" <<'EOF'
import json, sys
pf, ff, man, tag, i, first, step, w = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7]), sys.argv[8]
plen = len(open(pf).read().split())
ids = open(ff).read().split()
lens = set(range(first + step, len(ids), step)) | {plen}
if man != "none":
    for line in open(man):
        name, ls, _ = line.split("\t", 2)
        if name.startswith("%s%02d_" % (tag, i)):
            lens |= {int(x) for x in ls.split(",") if first < int(x) < len(ids)}
open(w + "/ids.txt", "w").write(" ".join(ids) + "\n")
open(w + "/sample.tsv", "w").write("%s%d\t%s\t%s\n" % (tag, i, ",".join(map(str, sorted(lens))), " ".join(ids)))
json.dump({"prompt_len": plen, "len": len(ids)}, open(w + "/lens.json", "w"))
print("%s%d: %d prompt + %d generated tokens, %d sampled prefill lengths" % (tag, i, plen, len(ids) - plen, len(lens)))
EOF
  "$DENSE" "$A1" "$W/ids.txt" $FIRST 1 "$W/ll1.bin" > "$W/ll1.log" 2>&1; st $TAG$i-ll1 $?
  "$DENSE" "$A1" "$W/ids.txt" $FIRST 512 "$W/ll512.bin" > "$W/ll512.log" 2>&1; st $TAG$i-ll512 $?
  ASTRAL_DUMP_FIRST=$FIRST "$AST" dump-logits "$A1" "$W/ll1.bin" "$W/as_step.bin" > "$W/as_step.log" 2>&1; st $TAG$i-as-step $?
  ASTRAL_DUMP_FIRST=$FIRST ASTRAL_DUMP_PREFILL=1 "$AST" dump-logits "$A1" "$W/ll1.bin" "$W/as_serve.bin" > "$W/as_serve.log" 2>&1; st $TAG$i-as-serve $?
  ASTRAL_DUMP_KINDS=prefill "$AST" dump-final-logits "$A1" "$W/sample.tsv" "$W/asp" > "$W/asp.log" 2>&1; st $TAG$i-as-prefill $?
  "$FL" "$A1" "$W/sample.tsv" "$W/llb" batch > "$W/llb.log" 2>&1; st $TAG$i-ll-batch $?
  NP=()
  for ng in $NEGS; do
    env "${ng#*:}" ASTRAL_DUMP_FIRST=$FIRST ASTRAL_DUMP_PREFILL=1 "$AST" dump-logits "$A1" "$W/ll1.bin" "$W/neg_${ng%%:*}.bin" > "$W/neg_${ng%%:*}.log" 2>&1; st $TAG$i-neg-${ng%%:*} $?
    NP+=("bin:$W/ll1.bin=bin:$W/neg_${ng%%:*}.bin")
  done
  "$PY" -I "$T/t25_kld.py" "$O/$TAG$i.json" \
    "bin:$W/ll1.bin=bin:$W/ll512.bin" "bin:$W/as_step.bin=bin:$W/as_serve.bin" \
    "bin:$W/ll1.bin=bin:$W/as_step.bin" "bin:$W/ll1.bin=bin:$W/as_serve.bin" "bin:$W/ll512.bin=bin:$W/as_serve.bin" \
    "bin:$W/ll1.bin=f32:$W/llb:$TAG$i:batch" "bin:$W/as_step.bin=f32:$W/asp:$TAG$i:prefill" "bin:$W/ll1.bin=f32:$W/asp:$TAG$i:prefill" "${NP[@]}" \
    > "$O/$TAG$i.txt" 2>&1; st $TAG$i-compare $?
  ( cd "$W" && sha256sum *.bin > bins.sha256 ); rm -rf "$W"/*.bin "$W/asp" "$W/llb"
done
guard; st guard-end $?
echo DONE >> "$O/STATUS"
cat "$O"/$TAG*.txt
