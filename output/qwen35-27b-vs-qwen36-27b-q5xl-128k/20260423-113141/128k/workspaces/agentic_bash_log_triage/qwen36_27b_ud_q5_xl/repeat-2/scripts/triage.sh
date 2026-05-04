#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

logfile="$1"

# Filter ERROR lines, strip timestamp and level, then normalize variable fields
# to produce stable signatures, then count and sort.
grep ' ERROR ' "$logfile" \
  | sed 's/^[^ ]* [^ ]* //' \
  | sed -E 's/ orderId=[^ ]*//g; s/ sku=[^ ]*//g; s/ code=[^ ]*//g; s/ providerTxnId=[^ ]*//g; s/ email=[^ ]*//g' \
  | sort \
  | uniq -c \
  | sort -rn \
  | sed 's/^ *//' \
  | while read -r count signature; do
    echo "$count $signature"
  done
