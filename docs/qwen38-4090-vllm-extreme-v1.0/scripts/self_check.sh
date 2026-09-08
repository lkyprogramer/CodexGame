#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for f in "$ROOT"/scripts/*.sh "$ROOT"/fixtures/*/verify.sh; do bash -n "$f"; done
python3 -m py_compile "$ROOT"/scripts/*.py "$ROOT"/bench/*.py
for d in "$ROOT"/fixtures/java-agent-*; do
  echo "Expecting initial fixture to FAIL: $(basename "$d")"
  set +e; (cd "$d" && ./verify.sh >/tmp/qbench-fixture.log 2>&1); rc=$?; set -e
  if [ "$rc" -eq 0 ]; then echo "ERROR: fixture already passes: $d"; cat /tmp/qbench-fixture.log; exit 3; fi
  echo "PASS: fixture fails before agent as designed"
done
echo 'SELF_CHECK_PASS'
