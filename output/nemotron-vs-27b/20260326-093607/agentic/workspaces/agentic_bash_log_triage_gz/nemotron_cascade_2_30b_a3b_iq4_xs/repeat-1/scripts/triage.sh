#!/usr/bin/env bash
set -euo pipefail

# Function to process a single log file (plain or .gz)
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
        # Extract ERROR lines
        if [[ "$line" == *"ERROR "* ]]; then
            # Extract service name (first word after timestamp and level)
            # Example: "2026-03-08T10:00:02Z ERROR OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409"
            # We want "OrderService"
            service=$(echo "$line" | awk -F' ' '{print $4}')
            # Extract the message after the service name (starting from the 6th field)
            message=$(echo "$line" | cut -d' ' -f6-)
            # Output a key that combines service and a normalized message (replace non-alphanumeric with underscore, lower case)
            # This groups similar errors together
            normalized_msg=$(echo "$message" | tr -c '[:alnum:]_' '_' | tr '[:upper:]' '[:lower:]')
            key="${service}_${normalized_msg}"
            echo "$key"
        fi
    done
}

# Temporary file for counts
counts_file=$(mktemp)
trap 'rm -f "$counts_file"' EXIT

# Process each argument (could be .log or .log.gz)
for f in "$@"; do
    if [[ -f "$f" ]]; then
        while IFS= read -r key; do
            [[ -z "$key" ]] && continue
            echo "$key" >> "$counts_file"
        done < <(process_file "$f")
    else
        echo "Warning: File $f not found" >&2
    fi
done

# Count occurrences, sort by count descending, and format output
if [[ -s "$counts_file" ]]; then
    sort "$counts_file" | uniq -c | sort -rn | awk '{print $2 " " $1}'
else
    echo "No relevant errors found" >&2
fi
