#!/usr/bin/env bash
set -euo pipefail

# Collect all lines from .log and .log.gz files
process_file() {
    local file="$1"
    if [[ "$file" == *.gz ]]; then
        gzip -dc "$file"
    else
        cat "$file"
    fi
}

# Read all input files, decompress if needed, filter health checks, normalize IDs, extract signatures, count and sort
for file in "$@"; do
    process_file "$file"
done | \
    grep -iv 'healthcheck' | \
    sed -E 's/orderId=[^ ]*/orderId=<ID>/g; s/traceId=[^ ]*/traceId=<ID>/g; s/providerTxnId=[^ ]*/providerTxnId=<ID>/g; s/requestId=[^ ]*/requestId=<ID>/g' | \
    awk '{
        # Remove timestamp and level to get signature
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
