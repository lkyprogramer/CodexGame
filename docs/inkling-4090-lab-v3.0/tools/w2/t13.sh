#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
guard || exit 3
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST="$LAB/src/astral/target/release/astral"; R="$LAB/runs"
W1=$(cat "$R/w1/LATEST"); O="$(cat "$R/w2/LATEST")/t13"; mkdir -p "$O"
python3 -c 'import json,sys; [open(f"{sys.argv[2]}/p{i:02d}.ids","w").write(" ".join(map(str,x["ids"]))) for i,x in enumerate(json.load(open(sys.argv[1])))]' "$W1/v2-llama.json" "$O"
for f in "$O"/p*.ids; do i=$(basename "$f" .ids); "$AST" spec-generate "$A1" "$MODELS/inkling-native" 6 512 "@$f" > "$O/spec_$i.txt" 2>&1; echo "$i rc=$?"; done
guard
