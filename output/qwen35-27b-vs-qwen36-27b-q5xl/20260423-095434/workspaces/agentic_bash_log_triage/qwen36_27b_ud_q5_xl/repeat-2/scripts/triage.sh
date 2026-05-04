#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

LOGFILE="$1"

# Process the log file:
# 1. Filter only ERROR lines
# 2. Remove the timestamp and level prefix to get the message
# 3. Normalize variable fields by replacing key=value pairs with key=*
# 4. Sort, count unique signatures, and format output

grep ' ERROR ' "$LOGFILE" | \
  sed 's/^[^ ]* [^ ]* //' | \
  sed -E 's/([a-zA-Z_][a-zA-Z0-9_]*)=[^ ]*/\1=*/g' | \
  sort | \
  uniq -c | \
  sort -rn | \
  sed 's/^ *//'
