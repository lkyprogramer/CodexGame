#!/usr/bin/env bash
set -euo pipefail

# Process each log file (plain or .gz)
for file in "$@"; do
    # Use zcat if file ends with .gz, otherwise cat
    if [[ "$file" == *.gz ]]; then
        input="zcat $file"
    else
        input="cat $file"
    fi

    # Extract error lines, ignore healthcheck, extract signature
    while IFS= read -r line; do
        # Skip healthcheck lines (case-insensitive)
        if [[ "${line,,}" == *"healthcheck"* ]]; then
            continue
        fi
        # Only consider ERROR lines
        if [[ "$line" == *"ERROR "* ]]; then
            # Extract the part after "ERROR " and before the first space
            # This gives us the signature (e.g., "OrderService failed to reserve inventory")
            signature="${line#*ERROR }"
            # Remove everything after the first space in the signature to normalize volatile IDs
            # Example: "OrderService failed to reserve inventory orderId=991 sku=abc code=INV-409" -> "OrderService failed to reserve inventory"
            normalized="${signature%% *}"
            # Count this normalized signature
            ((count["$normalized"]++))
        fi
    done < <(eval "$input")
done

# Output counts sorted by descending count, then alphabetically
for key in "${!count[@]}"; do
    echo "${count[$key]} $key"
done | sort -k1,1nr -k2,2 | awk '{print $2 " " $1}'
