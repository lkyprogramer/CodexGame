#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${1:-}"

if [[ -z "$LOG_FILE" || ! -f "$LOG_FILE" ]]; then
    echo "Usage: $0 <log_file>" >&2
    exit 1
fi

# Extract ERROR lines, normalize variable parts, count signatures
awk '
/ERROR/ {
    # Remove timestamp and level
    $1 = ""
    $2 = ""
    msg = $0
    gsub(/^[ \t]+/, "", msg)
    
    # Normalize variable parts: orderId=..., sku=..., providerTxnId=..., email=...
    gsub(/orderId=[0-9]+/, "orderId=XXX", msg)
    gsub(/sku=[a-zA-Z0-9]+/, "sku=XXX", msg)
    gsub(/providerTxnId=[A-Za-z0-9]+/, "providerTxnId=XXX", msg)
    gsub(/email=[^ \t]+/, "email=XXX", msg)
    
    signatures[msg]++
}
END {
    for (sig in signatures) {
        print signatures[sig] " " sig
    }
}
' "$LOG_FILE" | sort -rn
