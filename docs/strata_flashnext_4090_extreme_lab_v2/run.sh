#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
exec "${LAB_PYTHON:-python3}" -m lab.cli "$@"
