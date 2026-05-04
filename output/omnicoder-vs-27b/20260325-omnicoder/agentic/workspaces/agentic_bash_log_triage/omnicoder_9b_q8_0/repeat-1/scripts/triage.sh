#!/usr/bin/env bash
set -euo pipefail

awk '
/ERROR/ {
    # Extract message after " ERROR "
    idx = index($0, " ERROR ")
    if (idx > 0) {
        msg = substr($0, idx + 7)
        count[msg]++
    }
}
END {
    for (sig in count) {
        printf "%d %s\n", count[sig], sig
    }
}
' "$1"