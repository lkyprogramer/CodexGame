#!/usr/bin/env bash
set -euo pipefail

log_file="$1"

# Filter out healthcheck lines, extract error signatures (without key=value params), count occurrences
grep -v "healthcheck" "$log_file" | \
  grep -E "ERROR|WARN" | \
  sed 's/^[^ ]* [^ ]* //' | \
  sed 's/ [a-zA-Z_]*=[^ ]*//g' | \
  sort | uniq -c | \
  awk '{count=$1; $1=""; sub(/^ /, ""); print count " " $0}'
