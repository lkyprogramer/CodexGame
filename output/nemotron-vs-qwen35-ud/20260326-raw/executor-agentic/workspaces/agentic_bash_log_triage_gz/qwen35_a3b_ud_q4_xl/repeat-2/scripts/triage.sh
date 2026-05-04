#!/usr/bin/env bash
set -euo pipefail

# Function to read from .log or .log.gz
read_file() {
    if [[ "$1" == *.gz ]]; then
        gzip -dc "$1"
    else
        cat "$1"
    fi
}

# Process all input files
for file in "$@"; do
    read_file "$file"
done | \
# Filter out healthcheck lines
grep -iv 'healthcheck' | \
# Normalize volatile IDs (orderId, providerTxnId, requestId) to a placeholder
sed -E 's/(orderId=)[0-9]+/\1XXX/g; s/(providerTxnId=)[0-9]+/\1XXX/g; s/(requestId=)[0-9]+/\1XXX/g' | \
# Extract the error signature (everything after the log level)
grep -E '^.*ERROR.*' | \
# Extract the message part (after ERROR and before any key=value that might be part of signature)
# We want to group by the full error message pattern
awk '{
    # Find the first key=value pattern or end of line to define the signature
    # Actually, looking at the test, it groups by the full message text after ERROR
    # But we need to normalize IDs first. The sed above handles that.
    # Now we just need to extract the message part consistently.
    # The format is: TIMESTAMP LEVEL SERVICE message key=value ...
    # We want to group by: SERVICE message key=value ...
    # Let's extract from the 4th field onwards
    sig = ""
    for (i=4; i<=NF; i++) {
        if (sig != "") sig = sig " "
        sig = sig $i
    }
    count[sig]++
}
END {
    for (s in count) {
        print count[s] " " s
    }
}' | \
# Sort by count descending
sort -rn -k1
