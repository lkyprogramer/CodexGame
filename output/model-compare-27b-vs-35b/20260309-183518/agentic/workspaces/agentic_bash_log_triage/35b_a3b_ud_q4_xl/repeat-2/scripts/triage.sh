#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="${1:-}"

if [[ -z "$LOG_FILE" || ! -f "$LOG_FILE" ]]; then
    echo "Usage: $0 <log_file>" >&2
    exit 1
fi

# Process log file:
# 1. Filter only ERROR lines
# 2. Extract service name and message pattern (remove variable parts like orderId, sku, providerTxnId, email)
# 3. Count occurrences of each signature
# 4. Sort by count descending
# 5. Output in format: "COUNT SIGNATURE"

awk '
    /^ERROR/ {
        # Extract service name (second field)
        service = $2
        
        # Extract message parts (fields 3 onwards)
        msg = ""
        for (i = 3; i <= NF; i++) {
            field = $i
            # Replace variable values with placeholders
            # orderId=XXX -> orderId=
            # sku=XXX -> sku=
            # providerTxnId=XXX -> providerTxnId=
            # email=XXX -> email=
            gsub(/orderId=[^ ]+/, "orderId=", field)
            gsub(/sku=[^ ]+/, "sku=", field)
            gsub(/providerTxnId=[^ ]+/, "providerTxnId=", field)
            gsub(/email=[^ ]+/, "email=", field)
            
            if (msg != "") msg = msg " "
            msg = msg field
        }
        
        # Create signature: service + message
        signature = service " " msg
        count[signature]++
    }
    END {
        for (sig in count) {
            print count[sig] " " sig
        }
    }
' "$LOG_FILE" | sort -rn
