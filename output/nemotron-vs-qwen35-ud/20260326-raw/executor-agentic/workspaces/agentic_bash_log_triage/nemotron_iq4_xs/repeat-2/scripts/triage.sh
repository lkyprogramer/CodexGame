#!/usr/bin/env bash
set -euo pipefail

# Read the log file provided as the first argument
log_file="$1"

# Associative array to hold signature counts
declare -A counts

# Process each line in the log file
while IFS= read -r line; do
    # Skip empty lines
    [[ -z "$line" ]] && continue
    # Extract the log level (second field after timestamp)
    # Example line: 2026-03-08T10:00:02Z ERROR OrderService failed to reserve inventory ...
    # We want everything after the level
    level=$(echo "$line" | awk '{print $3}')
    # Skip healthcheck messages entirely
    if [[ "$level" == "healthcheck" ]]; then
        continue
    fi
    # Extract the message (everything after the level)
    # Using sed to remove the first three fields (timestamp, level, possibly level number)
    # The timestamp is in ISO format and may contain 'T', but it is always the first field.
    # The level is the second field.
    # The rest is the message.
    message=$(echo "$line" | cut -d' ' -f4-)
    # Trim leading/trailing whitespace
    message=$(echo "$message" | xargs)
    # Use the message as the signature key
    ((counts["$message"]++))
done < "$log_file"

# Output each signature with its count, sorted by count descending
for sig in "${!counts[@]}"; do
    echo "${counts[$sig]} $sig"
done
