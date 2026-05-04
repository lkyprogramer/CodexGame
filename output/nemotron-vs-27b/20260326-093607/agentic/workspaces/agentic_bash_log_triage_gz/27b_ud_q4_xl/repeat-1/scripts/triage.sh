#!/usr/bin/env bash
set -euo pipefail

# Process all provided log files (both .log and .log.gz)
process_logs() {
    for file in "$@"; do
        if [[ "$file" == *.gz ]]; then
            gunzip -c "$file"
        else
            cat "$file"
        fi
    done
}

# Read all logs, filter out healthchecks, normalize volatile IDs, count and sort
process_logs "$@" | \
    grep -v -i 'healthcheck' | \
    sed -E 's/orderId=[0-9]+/orderId=NORMALIZED/g; s/providerTxnId=[A-Z0-9-]+/providerTxnId=NORMALIZED/g; s/traceId=[A-Z0-9-]+/traceId=NORMALIZED/g; s/requestId=[A-Z0-9-]+/requestId=NORMALIZED/g' | \
    sed -E 's/email=[^ ]+/email=NORMALIZED/g' | \
    sort | uniq -c | sort -rn | \
    sed 's/^[ ]*//' 
