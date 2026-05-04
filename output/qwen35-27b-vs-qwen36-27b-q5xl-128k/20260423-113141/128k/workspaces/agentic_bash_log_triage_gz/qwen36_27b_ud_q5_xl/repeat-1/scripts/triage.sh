#!/usr/bin/env bash
set -euo pipefail

# Combine all input files (decompress .gz if needed), filter health checks,
# normalize volatile IDs, extract signatures, count and sort descending.

process_file() {
  local file="$1"
  if [[ "$file" == *.gz ]]; then
    gzip -dc "$file"
  else
    cat "$file"
  fi
}

# Process all files, skip healthcheck lines, normalize volatile fields, extract signature
for file in "$@"; do
  process_file "$file"
done | \
  grep -iv 'healthcheck' | \
  sed -E 's/(orderId|providerTxnId|traceId|requestId|sku|code|email)=[^ ]*/\1=<ID>/g' | \
  sed -E 's/[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z //' | \
  sed -E 's/^(INFO|ERROR|WARN) //' | \
  sort | \
  uniq -c | \
  sort -rn | \
  sed 's/^ *//'