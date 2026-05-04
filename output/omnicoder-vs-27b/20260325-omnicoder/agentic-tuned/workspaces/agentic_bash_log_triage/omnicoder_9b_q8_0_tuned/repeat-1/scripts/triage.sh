#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE="$1"

if [[ -z "$INPUT_FILE" || ! -f "$INPUT_FILE" ]]; then
    echo "Usage: $0 <log_file>" >&2
    exit 1
fi

# Filter ERROR lines
error_lines=()
while IFS= read -r line; do
    if [[ "$line" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T.*ERROR ]]; then
        error_lines+=("$line")
    fi
done < "$INPUT_FILE"

# Group by signature (remove timestamp and level)
declare -A counts
for line in "${error_lines[@]}"; do
    # Extract signature: remove timestamp (first 20 chars) and " ERROR "
    signature="${line:20}"
    signature="${signature#ERROR }"
    ((counts["$signature"]++)) || true
done

# Output sorted by signature
for sig in "${!counts[@]}"; do
    echo "${counts["$sig"]} $sig"
done | sort
