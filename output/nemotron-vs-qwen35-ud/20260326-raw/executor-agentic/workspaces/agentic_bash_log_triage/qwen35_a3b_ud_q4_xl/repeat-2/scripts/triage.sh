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
# 3. Normalize variable parts (orderId=..., sku=..., providerTxnId=..., email=...) to a placeholder
# 4. Count occurrences of each signature
# 5. Sort by count descending
# 6. Output: "COUNT SIGNATURE"

awk '
    /^ERROR/ {
        # Extract everything after the service name (second field)
        msg = ""
        for (i = 3; i <= NF; i++) {
            if (msg != "") msg = msg " "
            msg = msg $i
        }
        
        # Normalize variable patterns to a placeholder
        gsub(/orderId=[0-9]+/, "ID", msg)
        gsub(/sku=[a-zA-Z0-9]+/, "SKU", msg)
        gsub(/providerTxnId=[A-Z0-9]+/, "TXN", msg)
        gsub(/email=[a-zA-Z0-9.@]+/, "EMAIL", msg)
        
        signatures[msg]++
    }
    END {
        for (sig in signatures) {
            print signatures[sig] " " sig
        }
    }
' "$LOG_FILE" | sort -rn
