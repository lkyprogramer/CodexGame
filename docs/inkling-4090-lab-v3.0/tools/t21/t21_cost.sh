#!/usr/bin/env bash
# T21 stage 1: DSpark cost table and acceptance on four workloads (short chat prompts, code /
# natural language; 16K-token raw continuations, code / natural language). One Astral server per
# configuration, the T14 client (512 tokens, greedy, ignore_eos), REPS repetitions after one
# warm-up; per-round logs with ASTRAL_SPEC_LOG. Configurations: plain (no draft), the default
# adaptive policy (burst, k <= 6), the expected-tokens-per-ms policy (ASTRAL_SPEC_POLICY=model),
# fixed k = 1..7 (ASTRAL_SPEC_FIXED=1; the draft then proposes k tokens); burst7 (burst, k <= 7) and
# burstf32 (burst with ASTRAL_DRAFT_KV_F32=1; FP16 draft K/V is the default from fork df7f95b); for T26, burstdh / k7dh (the draft's base head
# run twice: ASTRAL_T26_DUP_HEAD=1) and burstdf / k7df (fold + argmax twice), when named in CONFIGS.
# MODEL / CKPT: another target and draft checkpoint (default A1 and inkling-native); DRAFT: a draft
# directory other than CKPT (serve --draft, e.g. the DFlash2 checkpoint; CKPT keeps the tokenizer); ALT /
# ALT_FROM: a second draft for prompts of >= ALT_FROM tokens (serve --draft-alt, T43 Phase 2); OUTROOT: the
# directory for the run (default $LAB/runs/t21). The code corpus is always tokenised with A1's GGUF
# (the same tokenizer). usage: t21_cost.sh
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="${MODEL:-$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf}"; CK="${CKPT:-$MODELS/inkling-native}"; AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; R="$LAB/runs"; BIN="$LAB/src/llama.cpp/build/bin"
OR="${OUTROOT:-$R/t21}"; O="$OR/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$OR/LATEST"
REPS=$(printenv REPS || echo 2); PORT=18998; CTX=20480
CONFIGS=$(printenv CONFIGS || echo "plain burst model k1 k2 k3 k4 k5 k6 k7")
guard || exit 3
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; sha256sum "$AST"; [ -f "$A1" ] && sha256sum "$A1"; echo "model $A1 checkpoint $CK draft ${DRAFT:-$CK} alt ${ALT:-none} from ${ALT_FROM:-4096}"; echo "ctx $CTX reps $REPS"; } > "$O/identity.txt"
# Code corpus: llama.cpp's Python sources in path order, up to 300,000 characters.
: > "$O/code.txt"
( cd "$LAB/src/llama.cpp" && git ls-files '*.py' ) | while read -r f; do
  [ "$(wc -c < "$O/code.txt")" -ge 300000 ] && break
  { cat "$LAB/src/llama.cpp/$f"; printf '\n\n'; } >> "$O/code.txt"
done
"$BIN/llama-tokenize" -m "$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf" -f "$O/code.txt" --ids --no-bos --log-disable 2> /dev/null | tail -1 > "$O/code_ids.json"
"$PY" -I "$LAB/pkg/tools/t21/t21_ids.py" "$(cat "$R/t14/LATEST")/ids.json" "$R/t17/inputs/ids.json" "$O/code_ids.json" "$O/ids.json" | tee "$O/ids.txt" || exit 1
wait_up() { for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && return 0; sleep 1; done; return 1; }
for C in $CONFIGS; do
  e=(X=1); a=(--k 6)
  case $C in
    plain) a=(--no-draft);;
    model) e=(ASTRAL_SPEC_POLICY=model);;
    burst7) a=(--k 7);;
    burstf32) e=(ASTRAL_DRAFT_KV_F32=1);;
    burstdh) e=(ASTRAL_T26_DUP_HEAD=1);;
    burstdf) e=(ASTRAL_T26_DUP_FOLD=1);;
    k7dh) e=(ASTRAL_SPEC_FIXED=1 ASTRAL_T26_DUP_HEAD=1); a=(--k 7);;
    k7df) e=(ASTRAL_SPEC_FIXED=1 ASTRAL_T26_DUP_FOLD=1); a=(--k 7);;
    k*) e=(ASTRAL_SPEC_FIXED=1); a=(--k "${C#k}");;
  esac
  : > "$O/$C.rounds.jsonl"
  env "${e[@]}" ASTRAL_SPEC_LOG="$O/$C.rounds.jsonl" "$AST" serve "$A1" --checkpoint "$CK" ${DRAFT:+--draft "$DRAFT"} ${ALT:+--draft-alt "$ALT" --alt-from "${ALT_FROM:-4096}"} "${a[@]}" --host 127.0.0.1 --port $PORT --ctx $CTX > "$O/$C.log" 2>&1 & SP=$!
  if wait_up; then
    "$PY" -I "$R/t14_bench.py" http://127.0.0.1:$PORT "$O/ids.json" "$C" "$REPS" "$O/$C.jsonl" > "$O/$C.txt" 2>&1; echo "$C rc=$?"
  else
    echo "$C not up"; tail -5 "$O/$C.log"
  fi
  kill $SP 2> /dev/null; wait $SP 2> /dev/null; sleep 3
done
"$PY" -I "$LAB/pkg/tools/t21/t21_analyze.py" "$O" | tee "$O/report.txt"
guard
