#!/usr/bin/env bash
# Investigation-only build. Never starts a server, downloads weights or uses a GPU.
set -euo pipefail
if [[ "$#" -ne 2 ]]; then
  printf 'Usage: %s PINNED_REPO NEW_OUTPUT_DIRECTORY\n' "$0" >&2
  exit 2
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd -- "$1" && pwd)"
OUT="$2"
if [[ -e "$OUT" ]]; then echo 'Output directory must not already exist.' >&2; exit 2; fi
python3 "$ROOT/tools/check_source_pin.py" --repo "$REPO" >/dev/null
PIN=44a2c6c3392c9d51e76a895ed97bf1867530d252
# Compilation uses the worktree, so require the relevant worktree blobs, not just historical objects.
for path in \
  src/targets/qwen3_8/impl/frontend/tokenizer.cpp \
  src/targets/qwen3_8/impl/frontend/tokenizer.h \
  src/targets/qwen3_8/impl/frontend/chat_template.cpp \
  src/targets/qwen3_8/impl/frontend/chat_template.h \
  src/targets/qwen3_8/impl/frontend/digest.cpp \
  src/text/unicode.cpp; do
  expected="$(git -C "$REPO" rev-parse "$PIN:$path")"
  actual="$(git -C "$REPO" hash-object -- "$REPO/$path")"
  [[ "$expected" == "$actual" ]] || { echo "Worktree differs at $path" >&2; exit 2; }
done
mkdir -p -- "$OUT"
OUT="$(cd -- "$OUT" && pwd)"
CC="${CC:-gcc}"
CXX="${CXX:-g++}"
"$CC" --version > "$OUT/compiler-c.txt"
"$CXX" --version > "$OUT/compiler-cxx.txt"
"$CC" -O3 -DUTF8PROC_STATIC -c "$REPO/third_party/utf8proc/utf8proc.c" -o "$OUT/utf8proc.o"
"$CXX" -std=c++20 -O3 -DNDEBUG -DUTF8PROC_STATIC \
  -I"$REPO/include" -I"$REPO/src" -I"$REPO/third_party" -I"$REPO/third_party/utf8proc" \
  -I"$REPO/src/targets/qwen3_8/export" \
  "$ROOT/evidence/review-assets/bench_ftc.cpp" \
  "$REPO/src/targets/qwen3_8/impl/frontend/chat_template.cpp" \
  "$REPO/src/targets/qwen3_8/impl/frontend/digest.cpp" \
  "$REPO/src/text/unicode.cpp" "$OUT/utf8proc.o" -o "$OUT/bench_ftc"
echo 'Review harness built; not a NInfer product validation. Supply audited resources and synthetic inputs separately.'
