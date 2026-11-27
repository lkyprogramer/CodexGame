#!/usr/bin/env bash
# T22 (fork 744e32a): the self-test's grouped tensor-core GEMM cases check their inputs. Run in the
# fork tree at 744e32a: (1) regression first, the new self-test with the old quantize (fork
# 02259e1's gemv.cu and ops.rs) must fail; (2) with the fix it must pass; (3) the model paths are
# unchanged: dump-final-logits of the previous binary and the new one, compared bit for bit.
set -u
source "$HOME/inkling-lab-v3/env.sh"; cd "$LAB/src/astral"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; M="$LAB/runs/t19nd/20261126T095409Z/m.tsv"
O="$LAB/runs/t22/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O/keep"
guard || exit 3
cp crates/kernels-src/cu/gemv.cu crates/kernels/src/ops.rs "$O/keep/"
git show 02259e1:crates/kernels-src/cu/gemv.cu > crates/kernels-src/cu/gemv.cu
git show 02259e1:crates/kernels/src/ops.rs > crates/kernels/src/ops.rs
nice -n 10 cargo build --release > "$O/build_oldquant.log" 2>&1
./target/release/astral selftest > "$O/selftest_oldquant.txt" 2>&1; echo "old quantize: rc=$? $(tail -1 "$O/selftest_oldquant.txt")"
cp "$O/keep/gemv.cu" crates/kernels-src/cu/gemv.cu; cp "$O/keep/ops.rs" crates/kernels/src/ops.rs
nice -n 10 cargo build --release > "$O/build.log" 2>&1
./target/release/astral selftest > "$O/selftest.txt" 2>&1; echo "fixed: rc=$? $(tail -1 "$O/selftest.txt")"
sha256sum target/release/astral "$LAB/bin/astral-02259e1" > "$O/bin.sha256"
"$LAB/bin/astral-02259e1" dump-final-logits "$A1" "$M" "$O/dfl_old" > "$O/dfl_old.log" 2>&1
./target/release/astral dump-final-logits "$A1" "$M" "$O/dfl_new" > "$O/dfl_new.log" 2>&1
n=0; d=0; for f in "$O"/dfl_old/*.f32; do n=$((n+1)); cmp -s "$f" "$O/dfl_new/$(basename "$f")" || d=$((d+1)); done
echo "real model, previous vs new binary: $d of $n files differ"
guard
