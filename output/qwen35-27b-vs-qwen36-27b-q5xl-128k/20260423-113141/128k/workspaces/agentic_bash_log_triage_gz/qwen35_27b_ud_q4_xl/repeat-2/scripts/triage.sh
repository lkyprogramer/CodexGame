#!/usr/bin/env bash
set -euo pipefail

# Collect all lines from .log and .log.gz files
process_file() {
    local f="$1"
    if [[ "$f" == *.gz ]]; then
        gzip -dc "$f"
    else
        cat "$f"
    fi
}

# Read all inputs, filter healthchecks, normalize volatile ids, count, sort
cat <(for f in "$@"; do process_file "$f"; done) | \
    grep -vi 'healthcheck' | \
    sed -E 's/orderId=[0-9]+/orderId=NORMALIZED/g; s/providerTxnId=P-[0-9]+/providerTxnId=NORMALIZED/g; s/traceId=T-[0-9]+/traceId=NORMALIZED/g; s/requestId=R-[0-9]+/requestId=NORMALIZED/g' | \
    sed -E 's/^([^ ]+ [^ ]+ [^ ]+) .*/\1/' | \
    sort | uniq -c | sort -rn | \
    awk '{count=$1; $1=""; sub(/^ +/, ""); print count, $0}'
