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
    grep -vi 'healthcheck' | \
    sed -E 's/orderId=[0-9]+/orderId=NORMALIZED/g; s/providerTxnId=P-[0-9]+/providerTxnId=NORMALIZED/g; s/traceId=T-[0-9]+/traceId=NORMALIZED/g; s/requestId=R-[0-9]+/requestId=NORMALIZED/g' | \
    sed -E 's/^[^ ]+ [^ ]+ //' | \
    sort | uniq -c | sort -rn | \
    sed 's/^[ ]*//' 
