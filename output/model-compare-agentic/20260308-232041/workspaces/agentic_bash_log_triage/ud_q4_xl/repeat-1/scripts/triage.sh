#!/usr/bin/env bash
set -euo pipefail

log_file="$1"

# Filter ERROR lines, extract message, remove variable key=value pairs, count signatures
grep " ERROR " "$log_file" | \
  sed 's/^[^ ]* ERROR //' | \
  sed 's/ [a-zA-Z_][a-zA-Z0-9_]*=[^ ]*//g' | \
  sed 's/^ *//;s/ *$//' | \
  sort | uniq -c | \
  sed 's/^[ ]*//'
