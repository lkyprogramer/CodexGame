#!/usr/bin/env bash
set -euo pipefail

# Collect all lines from .log and .log.gz files
process_file() {
    local file="$1"
    if [[ "$file" == *.gz ]]; then
        gunzip -c "$file"
    else
        cat "$file"
    fi
}

# Read all input files, filter, normalize, count, and sort
{
    for file in "$@"; do
        process_file "$file"
    done
} | \
# Ignore healthcheck lines
grep -vi 'healthcheck' | \
# Normalize volatile IDs (orderId, providerTxnId, traceId, requestId, sku, email)
sed -E 's/(orderId|providerTxnId|traceId|requestId|sku|email)=[^ ]+/\1=<ID>/g' | \
# Extract the message part (after timestamp and level)
sed -E 's/^[0-9T:-]+Z[[:space:]]+(INFO|ERROR|WARN)[[:space:]]+//' | \
# Sort and count unique lines
sort | uniq -c | \
# Sort by count descending
sort -rn | \
# Format output as "count message"
sed 's/^[[:space:]]*//' 
