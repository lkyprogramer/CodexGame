#!/usr/bin/env bash
set -euo pipefail

# Function to process a single log file (plain or gzipped)
process_file() {
    local file="$1"
    local ext="${file##*.}"
    if [[ "$ext" == "gz" ]]; then
        gzip -dc "$file" 2>/dev/null || return 1
    else
        cat "$file"
    fi | while IFS= read -r line; do
        # Skip healthcheck lines (case-insensitive)
        if [[ "${line,,}" == *"healthcheck"* ]]; then
            continue
        fi
        # Extract the first word after the timestamp (service name)
        # Expected format: 2026-03-08T10:00:02Z ERROR OrderService failed ...
        # We take the third field (service) and the rest as message
        read -r _ _ service message <<< "$line"
        if [[ -n "$service" && -n "$message" ]]; then
            echo "$service $message"
        fi
    done
}

# Temporary file for counts
counts_file=$(mktemp)
trap 'rm -f "$counts_file"' RETURN

# Process each argument (file can be .log or .log.gz)
for f in "$@"; do
    while IFS= read -r line; do
        # Skip empty lines
        [[ -z "$line" ]] && continue
        # Write to counts file: "service" "count"
        echo "$line"
    done < <(process_file "$f")
    # If process_file failed (e.g., unreadable gzip), still continue
    true

done | sort | awk '{count[$1]++} END {for (s in count) print count[s], s}' | sort -rn
