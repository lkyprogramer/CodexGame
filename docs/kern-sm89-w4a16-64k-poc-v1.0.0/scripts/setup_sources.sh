#!/usr/bin/env bash
# Never pulls floating HEAD. Offline bundles are preferred on the user's workstation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${POC_SOURCE_DIR:-$ROOT/work/source}"
REF=5188aaf8dc992ebe635f111d17c269969706da27
if [[ -e "$DEST" ]]; then echo "Refusing to overwrite existing source: $DEST" >&2; exit 2; fi
mkdir -p "$(dirname "$DEST")"
if [[ -n "${KERN_GIT_BUNDLE:-}" ]]; then
  git clone "$KERN_GIT_BUNDLE" "$DEST"
else
  git clone https://github.com/pegainfer-project/kern.git "$DEST"
fi
git -C "$DEST" checkout --detach "$REF"
test "$(git -C "$DEST" rev-parse HEAD)" = "$REF"
git -C "$DEST" switch -c poc/sm89-w4a16-64k
printf '\nSource prepared only. No Blackwell cubin is executed.\n'
