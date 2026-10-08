#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ $# -eq 3 ]] || { echo 'usage: run_qualification.sh local.json ready-plan.json output-directory' >&2; exit 2; }
[[ "${ALLOW_PRODUCTION_PAUSE:-0}" == 1 ]] || { echo 'No approval; production unchanged.' >&2; exit 2; }
python3 -u -m tools.session --config "$1" --plan "$2" --out "$3" --allow-prod-pause
