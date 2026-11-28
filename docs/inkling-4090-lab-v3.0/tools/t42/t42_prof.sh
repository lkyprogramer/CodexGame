#!/usr/bin/env bash
# T42 (MTB-01): hot-spot tables on the current fork for ranking K12-K15, T44, T47. nsys CUDA trace with
# graph nodes, no probes. Plain decode at 1K / 32K / 128K context (t16_kernels.py: per-step busy,
# span, kernel table), one DSpark spec-generate run (k = 7, 512 tokens, short prompt), and prefill at
# 2K / 32K (kernel sums). usage: t42_prof.sh [binary]
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST=${1:-$LAB/src/astral/target/release/astral}; PY="$LAB/venv/bin/python"
O="$LAB/runs/t42/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t42/LATEST"
guard || exit 3
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; sha256sum "$AST"; nsys --version; } > "$O/identity.txt"
ids() { "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[int(sys.argv[3]):int(sys.argv[3])+int(sys.argv[2])])))" "$LAB/runs/t17/inputs/ids.json" "$1" "$2"; }
NS=(nsys profile --trace=cuda --cuda-graph-trace=node --sample=none --cpuctxsw=none -f true)
rc=0
for L in 1000 32768 130944; do
  off=$([ $L -le 1000 ] && echo 200000 || echo 0); n=$([ $L -le 1000 ] && echo 256 || echo 64)
  env ASTRAL_CTX=$((L + 320)) "${NS[@]}" -o "$O/dec$L" "$AST" generate "$A1" $n $(ids $L $off) > "$O/dec$L.log" 2>&1 || rc=1
  nsys export --type sqlite -o "$O/dec$L.sqlite" -f true "$O/dec$L.nsys-rep" > /dev/null 2>&1
  "$PY" -I "$LAB/pkg/tools/t16/t16_kernels.py" "$O/dec$L.sqlite" > "$O/dec$L.kernels.txt" || rc=1; head -14 "$O/dec$L.kernels.txt"
done
ASTRAL_SPEC_NO_CHECK=1 ASTRAL_SPEC_REPS=1 "${NS[@]}" -o "$O/spec" "$AST" spec-generate "$A1" "$MODELS/inkling-native" 7 512 "@$(cat "$LAB/runs/w2/LATEST")/t13/p00.ids" > "$O/spec.log" 2>&1 || rc=1
nsys stats -r cuda_gpu_kern_sum -f csv -o "$O/spec" "$O/spec.nsys-rep" > /dev/null 2>&1
for L in 2048 32768; do
  env ASTRAL_CTX=$((L + 64)) "${NS[@]}" -o "$O/pf$L" "$AST" generate "$A1" 1 $(ids $L 0) > "$O/pf$L.log" 2>&1 || rc=1
  nsys stats -r cuda_gpu_kern_sum -f csv -o "$O/pf$L" "$O/pf$L.nsys-rep" > /dev/null 2>&1
done
rm -f "$O"/*.sqlite
guard || exit 3
exit $rc
