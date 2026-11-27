#!/usr/bin/env bash
# T16 hot-spot table: host-side step timing (ASTRAL_STEP_TIMING) and per-kernel GPU time of decode
# at 1K / 7K tokens of context and of a 2048-token prefill (nsys 2023.3, CUDA trace with graph
# nodes; kernel tracing needs no profiling permission). t16_kernels.py splits off the prefill
# and the first decode step and prints the per-step table. usage: t16_prof.sh [binary]
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST=${1:-$LAB/src/astral/target/release/astral}; PY="$LAB/venv/bin/python"
O="$LAB/runs/t16/prof-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t16/LATEST_PROF"
guard || exit 3
{ git -C "$LAB/src/astral" rev-parse HEAD; sha256sum "$AST"; nsys --version; } > "$O/identity.txt"
ids() { "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[200000:200000+int(sys.argv[2])])))" "$LAB/runs/t17/inputs/ids.json" "$1"; }
ASTRAL_STEP_TIMING=1 "$AST" generate "$A1" 256 $(ids 1000) > "$O/steptiming.log" 2>&1
grep '^step copy' "$O/steptiming.log" | tail -200 | awk '{c+=$3; l+=$6; s+=$9; r+=$12; n++} END {printf "steps %d: copy %.1f us, launch %.1f us, sync %.1f us, read %.1f us (means)\n", n, c/n, l/n, s/n, r/n}'
for L in 1000 7000; do
  nsys profile --trace=cuda --cuda-graph-trace=node --sample=none --cpuctxsw=none -o "$O/dec$L" -f true "$AST" generate "$A1" 256 $(ids $L) > "$O/dec$L.log" 2>&1
  nsys export --type sqlite -o "$O/dec$L.sqlite" -f true "$O/dec$L.nsys-rep" > /dev/null 2>&1
  "$PY" -I "$LAB/pkg/tools/t16/t16_kernels.py" "$O/dec$L.sqlite" > "$O/dec$L.kernels.txt"; head -12 "$O/dec$L.kernels.txt"
done
nsys profile --trace=cuda --cuda-graph-trace=node --sample=none --cpuctxsw=none -o "$O/pf2048" -f true "$AST" generate "$A1" 1 $(ids 2048) > "$O/pf2048.log" 2>&1
nsys stats -r cuda_gpu_kern_sum -f csv -o "$O/pf2048" "$O/pf2048.nsys-rep" > /dev/null 2>&1
guard
