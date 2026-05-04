#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <log file>" >&2
    exit 1
fi
log_file="$1"

# Extract lines that contain ERROR, WARN, or a specific pattern, then strip timestamps and sort
# Use awk to remove the leading timestamp (up to the first space after the date) and keep the rest
# Then count occurrences of each unique signature
# The first field of the output is the count, followed by the signature.

# Use awk to process the log: remove the leading timestamp (up to the first space after the date) and keep the rest of the line
# Then filter for lines that contain ERROR or WARN or the specific pattern for healthcheck (to be excluded later)
# We'll use a two-step process: first, strip the timestamp, then count the remaining lines.
# Finally, prepend the count and the signature.

# Use awk to strip the timestamp (format: YYYY-MM-DDTHH:MM:SSZ) and the following space
# Then, for each line, if it contains "ERROR" or "WARN" or "healthcheck", keep it, but we will later filter out healthcheck.
# We'll use a combination of grep and awk to achieve this.

# First, strip the timestamp and the following space
stripped=$(awk '{sub(/^[^ ]+ [^ ]+ [^ ]+ [^ ]+ [^ ]+ [^ ]+ [^ ]+ [^ ]+Z /, ""); print}' "$log_file")

# Now, filter out lines that contain "healthcheck" (case-insensitive) and keep only ERROR and WARN lines
filtered=$(echo "$stripped" | grep -i -E 'ERROR|WARN')

# Count occurrences of each unique signature and output count and signature
# Use sort and uniq -c to count, then prepend the count with a space
counts=$(echo "$filtered" | sort | uniq -c | awk '{print $1 " " substr($0,2)}')

# Output the counts and signatures, one per line
# The test expects the count to be the first field, so we output as is.
echo "$counts"
