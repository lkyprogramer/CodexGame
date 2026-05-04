#!/usr/bin/env bash
set -euo pipefail

chmod +x deploy.sh releases/good/healthcheck.sh releases/bad/healthcheck.sh
rm -f current
ln -s releases/good current

./deploy.sh releases/good
test "$(readlink current)" = "releases/good"

./deploy.sh releases/bad || true
test "$(readlink current)" = "releases/good"
