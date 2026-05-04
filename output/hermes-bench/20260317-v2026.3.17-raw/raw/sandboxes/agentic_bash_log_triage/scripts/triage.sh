#!/usr/bin/env bash
set -euo pipefail

log_file="${1:-}"

if [[ -z "$log_file" || ! -f "$log_file" ]]; then
    echo "Usage: $0 <log_file>" >&2
    exit 1
fi

# Filter out healthcheck lines, extract error signatures, count occurrences
grep -v "healthcheck" "$log_file" | \
    grep -E "ERROR|WARN" | \
    sed 's/^[^ ]* [^ ]* //' | \
    sed 's/ [a-zA-Z]*=[^ ]*//g' | \
    sort | uniq -c | \
    awk '{print $1, substr($0, index($0,$2))}'
