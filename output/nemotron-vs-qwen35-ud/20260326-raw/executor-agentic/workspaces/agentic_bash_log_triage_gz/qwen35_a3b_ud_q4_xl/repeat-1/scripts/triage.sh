#!/usr/bin/env bash
set -euo pipefail

# Function to read a file (handles .gz)
read_file() {
  local file="$1"
  if [[ "$file" == *.gz ]]; then
    gzip -dc "$file"
  else
    cat "$file"
  fi
}

# Collect all lines from all input files
all_lines=""
for file in "$@"; do
  all_lines+=$(read_file "$file")
  all_lines+=$'\n'
done

# Process lines:
# 1. Filter out healthcheck lines (case-insensitive)
# 2. Normalize volatile IDs (orderId, providerTxnId, traceId, requestId)
# 3. Extract the error signature (message part after ERROR)
# 4. Count occurrences
# 5. Sort by count descending
echo "$all_lines" | \
  grep -iv 'healthcheck' | \
  grep 'ERROR' | \
  sed -E 's/(orderId=)[0-9]+/\1X/g; s/(providerTxnId=)[0-9]+/\1X/g; s/(traceId=)[0-9]+/\1X/g; s/(requestId=)[0-9]+/\1X/g' | \
  sed -E 's/^[^ ]+ [^ ]+ //' | \
  sort | uniq -c | sort -rn | \
  awk '{print $1 " " substr($0, index($0,$2))}'
