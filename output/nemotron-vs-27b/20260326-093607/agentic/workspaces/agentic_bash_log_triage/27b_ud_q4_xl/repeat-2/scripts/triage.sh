#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

logfile="$1"

# Extract ERROR lines, remove timestamp and level to get signature, count occurrences, sort by count desc
grep '^.* ERROR ' "$logfile" | \
  sed 's/^[^ ]* ERROR //' | \
  sort | uniq -c | \
  sort -rn | \
  sed 's/^[[:space:]]*//' > /dev/stdout
