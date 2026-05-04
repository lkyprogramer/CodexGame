#!/usr/bin/env bash
set -euo pipefail

# Function to process a single log file (plain or gzipped)
process_file() {
    local file="$1"
    local ext="${file##*.}"
    if [[ "$ext" == "gz" ]]; then
        gzip -dc "$file"
    else
        cat "$file"
    fi | while IFS= read -r line; do
        # Skip healthcheck lines (case-insensitive)
        if [[ "$line" =~ healthcheck ]]; then
            continue
        fi
        # Extract service name and message (after the timestamp and log level)
        # Expected format: <timestamp> <LEVEL> <service> <message...>
        # We'll use awk to split the line after the first two fields
        # and then reconstruct the message.
        # Using awk to capture service and message
        service=$(echo "$line" | awk '{print $3}' | sed 's/\///g')
        # The message starts from the 4th field onward
        message=$(echo "$line" | cut -d' ' -f4-)
        # If service is empty or message is empty, skip
        if [[ -z "$service" || -z "$message" ]]; then
            continue
        fi
        # Count this occurrence
        echo "$service|$message"
    done
}

# Associative array to hold counts per service+message
! declare -A counts 2>/dev/null || declare -A counts

# Process each file passed as an argument
for f in "$@"; do
    while IFS='|' read -r svc msg; do
        key="$svc|$msg"
        ((counts["$key"]++))
    done < <(process_file "$f")
done

# Output sorted counts (descending)
for key in "${!counts[@]}"; do
    IFS='|' read -r svc msg <<< "$key"
    count=${counts[$key]}
    echo "$count $svc $msg"
 done | sort -k1,1nr -k2,2 | sed 's/^/2 /'  # Prepend '2 ' to indicate level 2 (ERROR)
