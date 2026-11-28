#!/usr/bin/env bash
# T25 / T21 follow-up: FP16 draft K/V (ASTRAL_DRAFT_KV_F16=1) against FP32 at long context. DSpark
# greedy generation (astral spec-generate: two DSpark runs, plain decode and a teacher-forced check) of 256 tokens after a 100,000-token prompt (T17 corpus) at ctx 106496, and after
# a 16K prompt at ctx 20480: generated tokens must be identical (the target verifies every draft),
# acceptance and speed compared.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; CK="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; I="$LAB/runs/t17/inputs"
O="$LAB/runs/t25/$(date -u +%Y%m%dT%H%M%SZ)-f16"; mkdir -p "$O"
guard || exit 3
for n in 16384 100000; do
  "$PY" -I -c "import json,sys; print(' '.join(map(str, json.load(open(sys.argv[1]))[:int(sys.argv[2])])))" "$I/ids.json" $n > "$O/p$n.ids"
  ctx=20480; [ $n -gt 20000 ] && ctx=106496
  for kv in f32 f16; do
    e=X=1; [ $kv = f16 ] && e=ASTRAL_DRAFT_KV_F16=1
    env $e ASTRAL_CTX=$ctx "$AST" spec-generate "$A1" "$CK" 6 256 @"$O/p$n.ids" > "$O/g$n-$kv.txt" 2>&1; echo "g$n-$kv rc=$?" >> "$O/STATUS"
  done
done
guard
for n in 16384 100000; do echo "== $n"; for kv in f32 f16; do echo "-- $kv"; grep -E "^run|equals|teacher" "$O/g$n-$kv.txt"; done
  if diff <(grep "^spec tokens:" "$O/g$n-f32.txt") <(grep "^spec tokens:" "$O/g$n-f16.txt") > /dev/null; then echo "spec tokens f32 = f16"; else echo "spec tokens f32 != f16"; fi; done | tee "$O/summary.txt"
