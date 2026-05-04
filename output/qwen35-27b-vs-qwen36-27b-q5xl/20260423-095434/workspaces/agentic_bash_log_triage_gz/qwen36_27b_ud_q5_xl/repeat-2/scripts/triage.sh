#!/usr/bin/env bash
set -euo pipefail

# Combine all input files (handling .gz transparently)
combine_logs() {
  for f in "$@"; do
    if [[ "$f" == *.gz ]]; then
      gzip -dc "$f"
    else
      cat "$f"
    fi
  done
}

# Process logs:
# 1. Filter out healthcheck lines
# 2. Normalize volatile IDs (orderId, sku, code, providerTxnId, traceId, requestId, email)
# 3. Extract the error signature (everything after the log level)
# 4. Count occurrences and sort descending
combine_logs "$@" | \
  grep -iv 'healthcheck' | \
  sed -E 's/(orderId|sku|code|providerTxnId|traceId|requestId|email)=[^ ]*/\1=<ID>/g' | \
  awk '{
    # Skip the timestamp and level, take the rest as signature
    sig = ""
    for (i = 3; i <= NF; i++) {
      sig = sig (i > 3 ? " " : "") $i
    }
    if (sig != "") counts[sig]++
  }
  END {
    for (sig in counts) {
      print counts[sig] " " sig
    }
  }' | \
  sort -rn -k1,1
