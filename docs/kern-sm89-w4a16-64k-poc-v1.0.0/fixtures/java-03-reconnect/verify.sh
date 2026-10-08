#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT
mapfile -t FILES < <(find src/main src/test -name '*.java' | sort)
if javac -version 2>&1 | grep -q 'javac 1.8'; then
  javac -source 8 -target 8 -d "$OUT" "${FILES[@]}"
else
  javac --release 8 -d "$OUT" "${FILES[@]}"
fi
java -cp "$OUT" TestMain
