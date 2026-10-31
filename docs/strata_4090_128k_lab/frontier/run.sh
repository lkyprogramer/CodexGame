#!/usr/bin/env bash
set -euo pipefail
task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd -- "$task_root"
case "${1:-help}" in
  validate) exec python3 -B tools/validate.py --root . ;;
  test) exec python3 -B -m unittest discover -s tests -v ;;
  manifest) exec python3 -B tools/verify_manifest.py --root . --manifest MANIFEST.sha256 ;;
  plan) cat START_HERE_AI.md ;;
  help) printf '%s\n' 'Offline only: ./run.sh validate | test | manifest | plan' ;;
  *) printf '%s\n' 'Unknown action. No live or deploy command is provided.' >&2; exit 2 ;;
esac
