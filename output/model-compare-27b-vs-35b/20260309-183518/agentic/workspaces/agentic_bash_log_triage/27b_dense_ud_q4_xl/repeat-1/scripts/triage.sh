#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

logfile="$1"

# Filter ERROR lines, extract signature (message without variable key=value pairs), count, sort
grep ' ERROR ' "$logfile" | \
  sed -E 's/^[^ ]+ ERROR //' | \
  sed -E 's/ [a-zA-Z_]+=[^ ]+//g' | \
  sort | uniq -c | sort -rn | \
  awk '{count=$1; $1=""; sub(/^ +/, ""); print count " " $0}'
