#!/usr/bin/env bash
set -euo pipefail

# Collect all log lines from .log and .log.gz files
process_logs() {
    for file in "$@"; do
        if [[ "$file" == *.gz ]]; then
            gunzip -c "$file"
        else
            cat "$file"
        fi
    done
}

# Main logic
process_logs "$@" | \
    grep -v -i 'healthcheck' | \
    grep -E '^.* (ERROR|WARN) ' | \
    sed -E 's/orderId=[^ ]+/orderId=ID/g' | \
    sed -E 's/providerTxnId=[^ ]+/providerTxnId=ID/g' | \
    sed -E 's/traceId=[^ ]+/traceId=ID/g' | \
    sed -E 's/requestId=[^ ]+/requestId=ID/g' | \
    sed -E 's/email=[^ ]+/email=USER/g' | \
    sed -E 's/sku=[^ ]+/sku=SKU/g' | \
    sed -E 's/code=[^ ]+/code=CODE/g' | \
    awk '{
        # Remove timestamp and level to get signature
        $1 = ""
        $2 = ""
        sig = $0
        gsub(/^[ \t]+/, "", sig)
        count[sig]++
    }
    END {
        for (sig in count) {
            print count[sig] " " sig
        }
    }' | \
    sort -rn
