#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

LOGFILE="$1"

# Filter ERROR lines, normalize variable fields, count and sort
awk '
  /^.*ERROR/ {
    # Remove timestamp and level prefix
    sub(/^[^ ]+ [^ ]+ /, "")
    
    # Normalize key=value pairs that look like IDs or emails
    # Replace orderId=... with orderId=<id>
    gsub(/orderId=[^ ]+/, "orderId=<id>")
    # Replace sku=... with sku=<sku>
    gsub(/sku=[^ ]+/, "sku=<sku>")
    # Replace code=... with code=<code>
    gsub(/code=[^ ]+/, "code=<code>")
    # Replace providerTxnId=... with providerTxnId=<id>
    gsub(/providerTxnId=[^ ]+/, "providerTxnId=<id>")
    # Replace email=... with email=<email>
    gsub(/email=[^ ]+/, "email=<email>")
    
    sigs[$0]++
  }
  END {
    for (sig in sigs) {
      printf "%d %s\n", sigs[sig], sig
    }
  }
' "$LOGFILE" | sort -rn
