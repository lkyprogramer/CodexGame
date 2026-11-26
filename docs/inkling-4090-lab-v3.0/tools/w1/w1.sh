#!/usr/bin/env bash
set -uo pipefail
source "$HOME/inkling-lab-v3/env.sh"
guard || { echo "DRIVER GUARD FAIL"; exit 3; }
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"
NATIVE="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; LL="$LAB/src/llama.cpp"; BIN="$LL/build/bin"
OUT="$LAB/runs/w1/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$OUT"; echo "$OUT" > "$LAB/runs/w1/LATEST"
st() { echo "$1 rc=$2" | tee -a "$OUT/STATUS"; }
gpu() { nvidia-smi --query-gpu=memory.used,clocks.sm,clocks.mem,temperature.gpu,power.draw --format=csv > "$OUT/gpu-$1.csv"; }
gpu start
"$AST" version > "$OUT/version.txt" 2>&1
"$AST" hw --bench > "$OUT/hw.json" 2>&1; st hw $?
"$AST" selftest > "$OUT/selftest.txt" 2>&1; st selftest $?
"$AST" gguf-info "$A1" --tensors > "$OUT/gguf-info.txt" 2>&1; st gguf-info $?
(cd "$LAB/src/astral" && bench/golden_llamacpp.sh "$A1" "$LL" "$OUT/golden") > "$OUT/golden.txt" 2>&1; st golden $?
G=$(ls -d "$OUT"/golden/*-golden | tail -1)
"$AST" verify-embd "$A1" "$G/eval_callback.log" > "$OUT/verify-embd.txt" 2>&1; st verify-embd $?
"$AST" verify-model "$A1" "$G/eval_callback.log" > "$OUT/verify-model.txt" 2>&1; st verify-model $?
# T10 tokenizer parity: llama.cpp (GGUF vocab) vs HF tokenizer.json
[ -x "$LAB/venv/bin/python" ] || python3 -m venv "$LAB/venv"
"$LAB/venv/bin/pip" install -q -i https://pypi.tuna.tsinghua.edu.cn/simple tokenizers > "$OUT/pip.txt" 2>&1; st pip $?
"$LAB/venv/bin/python" -I "$LAB/runs/tokparity.py" "$BIN/llama-tokenize" "$A1" "$NATIVE/tokenizer.json" > "$OUT/tokparity.json" 2> "$OUT/tokparity.err"; st tokparity $?
# T10 greedy: Astral vs llama.cpp on the same prompt ids
"$BIN/llama-tokenize" -m "$A1" -p "The capital of France is" --ids --log-disable > "$OUT/ids.txt" 2>&1
IDS=$(tail -1 "$OUT/ids.txt" | tr -d '[],')
"$AST" generate "$A1" 128 $IDS > "$OUT/astral-generate.txt" 2>&1; st astral-generate $?
"$BIN/llama-server" -m "$A1" -ngl 99 -c 4096 --host 127.0.0.1 --port 18999 -np 1 > "$OUT/llama-server.log" 2>&1 &
SP=$!
for i in $(seq 1 180); do curl -sf http://127.0.0.1:18999/health >/dev/null && break; sleep 1; done
PJ=$(echo $IDS | python3 -c 'import sys,json; print(json.dumps({"prompt":[int(x) for x in sys.stdin.read().split()],"n_predict":128,"temperature":0,"top_k":1,"cache_prompt":False,"return_tokens":True,"n_probs":2}))')
curl -s http://127.0.0.1:18999/completion -H 'Content-Type: application/json' -d "$PJ" > "$OUT/llama-greedy.json"; st llama-greedy $?
kill $SP; wait $SP 2>/dev/null
gpu end
guard; st guard-end $?
echo DONE
