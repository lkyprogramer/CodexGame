#!/usr/bin/env bash
set -euo pipefail

log_file="$1"

grep " ERROR " "$log_file" | \
awk '{
    sig = $3
    for (i = 4; i <= NF; i++) {
        if ($i ~ /=/) break
        sig = sig " " $i
    }
    count[sig]++
}
END {
    for (sig in count) {
        print count[sig], sig
    }
}'
