#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${1:-}"

if [[ -z "$LOG_FILE" || ! -f "$LOG_FILE" ]]; then
    echo "Usage: $0 <log_file>" >&2
    exit 1
fi

# Process log file:
# 1. Filter only ERROR lines
# 2. Extract the message part (after the service name)
# 3. Normalize variable parts (orderId=..., sku=..., providerTxnId=..., email=...)
# 4. Count occurrences of each signature
# 5. Sort by count descending
# 6. Output with count prefix
grep ' ERROR ' "$LOG_FILE" | \
    sed -E 's/^.* ERROR ([^ ]+) (.*)$/\2/' | \
    sed -E 's/orderId=[0-9]+/orderId=XXX/g' | \
    sed -E 's/sku=[a-zA-Z0-9]+/sku=XXX/g' | \
    sed -E 's/providerTxnId=[^ ]+/providerTxnId=XXX/g' | \
    sed -E 's/email=[^ ]+/email=XXX/g' | \
    sort | uniq -c | sort -rn | \
    while read -r count signature; do
        printf "%s %s\n" "$count" "$signature"
    done
