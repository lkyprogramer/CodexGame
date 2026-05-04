#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

logfile="$1"

# Process the log file:
# 1. Filter only ERROR lines
# 2. Extract the message part (after timestamp, level, and service name)
# 3. Normalize by removing variable key=value pairs
# 4. Count occurrences and sort by count descending
awk '
/^.*ERROR / {
  # Remove timestamp and level prefix
  # Format: 2026-03-08T10:00:02Z ERROR OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409
  # We want to keep the service name and the static message, but strip variable fields
  
  # Remove the timestamp (first field) and ERROR (second field)
  $1 = ""
  $2 = ""
  # Rebuild the line without leading spaces
  sub(/^  +/, "")
  
  # Now line looks like: "OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409"
  # Remove all key=value pairs (variable fields)
  gsub(/[[:space:]]+[a-zA-Z_]+=[^[:space:]]*/, "")
  
  # Trim trailing whitespace
  sub(/[[:space:]]+$/, "")
  
  count[$0]++
}
END {
  for (sig in count) {
    print count[sig], sig
  }
}
' "$logfile" | sort -rn
