#!/usr/bin/env bash
# T17 inputs: a long corpus (llama.cpp's markdown, then its Python sources, in path order, up to
# 900,000 characters), its token ids (llama-tokenize, no BOS, as llama-perplexity reads it), the
# manifests (t17_util.py manifests) and the token-only bases of the perplexity ladder.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; BIN="$LAB/src/llama.cpp/build/bin"; PY="$LAB/venv/bin/python"
U="$LAB/pkg/tools/t17/t17_util.py"; W1=$(cat "$LAB/runs/w1/LATEST"); REF="$(ls -d $W1/golden/*-golden | tail -1)/kld_base_c512x8.bin"
I="$LAB/runs/t17/inputs"; mkdir -p "$I"
( cd "$LAB/src/llama.cpp" && { git ls-files '*.md'; git ls-files '*.py'; } ) > "$I/files.txt"
: > "$I/corpus.txt"
while read -r f; do
  [ "$(wc -c < "$I/corpus.txt")" -ge 900000 ] && break
  { cat "$LAB/src/llama.cpp/$f"; printf '\n\n'; } >> "$I/corpus.txt"
done < "$I/files.txt"
"$BIN/llama-tokenize" -m "$A1" -f "$I/corpus.txt" --ids --no-bos --log-disable 2>/dev/null | tail -1 > "$I/ids.json"
"$PY" -I -c "import json,sys; print(len(json.load(open(sys.argv[1]))), 'tokens')" "$I/ids.json"
"$PY" -I "$U" manifests "$I/ids.json" "$I"
for c in 16384 32768 65536 131072; do "$PY" -I "$U" base "$I/ids.json" "$REF" $c "$I/tok$((c / 1024))k.bin"; done
sha256sum "$I"/corpus.txt "$I"/ids.json "$I"/*.tsv > "$I/SHA256"
wc -c "$I/corpus.txt"
