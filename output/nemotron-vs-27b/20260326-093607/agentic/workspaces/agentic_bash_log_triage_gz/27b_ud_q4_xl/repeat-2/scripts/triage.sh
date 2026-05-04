#!/usr/bin/env bash
set -euo pipefail

# Process .log and .log.gz files, normalize volatile IDs, ignore healthchecks,
# group by signature, count, and sort descending.

process_file() {
    local file="$1"
    if [[ "$file" == *.gz ]]; then
        zcat "$file"
    else
        cat "$file"
    fi
}

# Collect all lines from input files, filter out healthchecks, normalize volatile IDs
{
    for file in "$@"; do
        process_file "$file"
    done
} | \
    grep -vi 'healthcheck' | \
    sed -E 's/(orderId|providerTxnId|traceId|requestId)=[^ ]*/\1=<ID>/g' | \
    sort | \
    uniq -c | \
    sort -rn | \
    sed 's/^ *\([0-9]*\) \(.*\)/\1 \2/'
