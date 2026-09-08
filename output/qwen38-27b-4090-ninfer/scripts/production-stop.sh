#!/usr/bin/env bash
set -euo pipefail
docker rm -f ninfer-4090-prod ninfer-4090 >/dev/null 2>&1 || true
