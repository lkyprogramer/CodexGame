#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

logfile="$1"

# Extract ERROR lines, remove timestamp and level, group by signature, count occurrences
grep '^.* ERROR ' "$logfile" | \
  sed 's/^[^ ]* ERROR //' | \
  sort | \
  uniq -c | \
  awk '{count=$1; $1=""; sub(/^ /, ""); print count " " $0}'
