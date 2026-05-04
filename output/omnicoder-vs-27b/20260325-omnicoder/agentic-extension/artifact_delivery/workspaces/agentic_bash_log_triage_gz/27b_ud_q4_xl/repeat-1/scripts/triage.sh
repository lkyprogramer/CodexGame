#!/usr/bin/env bash
set -euo pipefail

# Process all log files (both .log and .log.gz)
process_logs() {
    for file in "$@"; do
        if [[ "$file" == *.gz ]]; then
            zcat "$file"
        else
            cat "$file"
        fi
    done
}

# Main processing
process_logs "$@" | \
    grep -v -i "healthcheck" | \
    sed -E 's/(orderId|providerTxnId|traceId|requestId)=[^ ]*/\1=ID/g' | \
    awk '{
        $1 = ""
        $2 = ""
        msg = $0
        gsub(/^[ \t]+/, "", msg)
        count[msg]++
    }
    END {
        for (msg in count) {
            print count[msg], msg
        }
    }' | \
    sort -rn -k1
