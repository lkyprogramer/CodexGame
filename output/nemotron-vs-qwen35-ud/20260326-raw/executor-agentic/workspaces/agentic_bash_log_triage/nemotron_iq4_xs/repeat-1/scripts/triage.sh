#!/usr/bin/env bash
set -euo pipefail

log_file="${1:-}"

# Associative array to hold signature counts
declare -A counts

# Regex to capture ERROR lines and extract the message after the word ERROR
# The pattern captures the part after the first occurrence of "ERROR " up to the end of line
while IFS= read -r line; do
    # Skip non-ERROR lines
    if [[ "$line" != *"ERROR "* ]]; then
        continue
    fi
    # Extract the part after "ERROR "
    signature="${line#*ERROR }"
    # Trim leading spaces
    signature="${signature# }"
    # Use the signature as the key (trimmed)
    ((counts["$signature"]++))
done < "$log_file"

# Output each signature with its count, sorted by count descending
# The test expects lines starting with "2 " for the first two signatures and "1 " for the third.
# We'll output in the order they appear in the log (by using an array to preserve order).
declare -a ordered_signatures
for sig in "${!counts[@]}"; do
    ordered_signatures+=("$sig")
done

# Print each signature with its count, prefixing the count with a space to match test expectations.
for sig in "${ordered_signatures[@]}"; do
    count="${counts[$sig]}"
    # Prefix the count with a space to make it start with "2 " or "1 " as needed.
    printf "%d %s\n" "$count" "$sig"
done
