#!/usr/bin/env bash
set -euo pipefail

# Process log files (handles both plain and gzipped)
process_log() {
    local file="$1"
    if [[ "$file" == *.gz ]]; then
        gunzip -c "$file"
    else
        cat "$file"
    fi
}

# Normalize volatile IDs to prevent false grouping
normalize_ids() {
    sed -E '
        s/orderId=[^ ]+/orderId=[ID]/g
        s/providerTxnId=[^ ]+/providerTxnId=[ID]/g
        s/traceId=[^ ]+/traceId=[ID]/g
        s/requestId=[^ ]+/requestId=[ID]/g
        s/sku=[^ ]+/sku=[ID]/g
        s/email=[^ ]+/email=[ID]/g
    '
}

# Main processing
for file in "$@"; do
    process_log "$file" | normalize_ids
done | grep -v 'healthcheck' | sed 's/^[^ ]* // ' | sort | uniq -c | sort -rn | awk '{print $1, $2}'