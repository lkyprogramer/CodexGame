#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <logfile>" >&2
    exit 1
fi

logfile="$1"

declare -A counts

while IFS= read -r line; do
    if [[ "$line" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z[[:space:]]+ERROR[[:space:]]+ ]]; then
        signature=$(echo "$line" | sed 's/^[0-9-]*T[0-9:]*Z[[:space:]]*ERROR[[:space:]]*//')
        counts["$signature"]=$((${counts["$signature"]:-0} + 1))
    fi
done < "$logfile"

for signature in "${!counts[@]}"; do
    echo "${counts[$signature]} $signature"
done | sort -n
