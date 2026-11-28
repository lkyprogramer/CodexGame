#!/usr/bin/env bash
# Regenerate PACKAGE_MANIFEST.sha256 from git-visible files only (tracked, plus untracked files that
# are not ignored), so a fresh clone verifies cleanly. Run from anywhere inside a git checkout.
set -euo pipefail
cd "$(dirname "$0")/.."
git ls-files -co --exclude-standard \
  | grep -v -e '^PACKAGE_MANIFEST\.sha256$' -e '/__pycache__/' \
  | while IFS= read -r f; do [ -f "$f" ] && printf '%s\n' "$f"; done \
  | LC_ALL=C sort -u | xargs -d '\n' sha256sum > PACKAGE_MANIFEST.sha256
sha256sum --quiet -c PACKAGE_MANIFEST.sha256
wc -l < PACKAGE_MANIFEST.sha256
