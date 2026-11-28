#!/usr/bin/env bash
# T28 dense shadow (GPU, read-only probes): block-sparse far-history attention evaluated against
# the exact attention at decode positions of global layers. astral trace from a build with the
# ASTRAL_TRACE_SPARSE probe (fork df7f95b), prefill up to the first probed step, V cache
# read at every probed position (output error). Positions: the T17 corpus at 32K / 64K / 128K
# (2 positions each, 64 tokens apart) and set-D document d3 (9545 tokens; 2 positions).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
AST="${AST:-$LAB/src/astral/target/release/astral}"; PY="$LAB/venv/bin/python"; T="$LAB/pkg/tools/t28"
I="$LAB/runs/t17/inputs"; D=$(cat "$LAB/runs/t25/LATEST_D")
O="$LAB/runs/t28/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t28/LATEST"
guard || exit 3
{ git -C "$(dirname "$(dirname "$(dirname "$AST")")")" rev-parse HEAD; git -C "$(dirname "$(dirname "$(dirname "$AST")")")" status --short; sha256sum "$AST"; } > "$O/identity.txt"
"$PY" -I - "$I/ids.json" "$D/d3/ids.txt" "$O" <<'EOF'
import json, sys
ids = json.load(open(sys.argv[1])); d3 = open(sys.argv[2]).read().split(); o = sys.argv[3]
with open(o + "/manifest.tsv", "w") as f:
    for c in (32768, 65536, 131072):
        L = [c - 160 + 64 * k for k in range(2)]
        f.write("c%dk\t%s\t%s\n" % (c // 1024, ",".join(map(str, L)), " ".join(map(str, ids[:L[-1] + 1]))))
    L = [len(d3) - 160 + 64 * k for k in range(2)]
    f.write("d3\t%s\t%s\n" % (",".join(map(str, L)), " ".join(d3[:L[-1] + 1])))
EOF
ASTRAL_CTX=131200 ASTRAL_TRACE_SPARSE=1 ASTRAL_TRACE_PREFILL=1 ASTRAL_TRACE_VALIDATE=all ASTRAL_TRACE_LENS=0 \
  "$AST" trace "$A1" "$O/manifest.tsv" "$O/trace" > "$O/trace.log" 2>&1; echo "trace rc=$?" >> "$O/STATUS"
"$PY" -I "$T/t28_summary.py" "$O/trace/trace.jsonl" > "$O/summary.txt" 2>&1; echo "summary rc=$?" >> "$O/STATUS"
guard
cat "$O/summary.txt"
