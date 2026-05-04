#!/usr/bin/env bash
set -euo pipefail

# Process all provided log files (.log and .log.gz)
# 1. Decompress .gz files on the fly
# 2. Filter out healthcheck lines
# 3. Normalize volatile IDs (orderId, providerTxnId, traceId, requestId, sku, email, code)
# 4. Extract error signature (everything after the log level)
# 5. Count occurrences and sort descending

process_log() {
    local file="$1"
    if [[ "$file" == *.gz ]]; then
        gzip -dc "$file"
    else
        cat "$file"
    fi
}

# Combine all input files, filter, normalize, count, and sort
for file in "$@"; do
    process_log "$file"
done | \
    grep -iv 'healthcheck' | \
    sed -E 's/(orderId|providerTxnId|traceId|requestId|sku|email|code)=[^ ]*/\1=<ID>/g' | \
    awk '{
        # Remove timestamp and log level to get signature
        # Format: TIMESTAMP LEVEL MESSAGE...
        # We want everything from the 3rd field onward
        sig = ""
        for (i = 3; i <= NF; i++) {
            sig = sig (i > 3 ? " " : "") $i
        }
        counts[sig]++
    }
    END {
        for (sig in counts) {
            print counts[sig] " " sig
        }
    }' | \
    sort -rn -k1,1
