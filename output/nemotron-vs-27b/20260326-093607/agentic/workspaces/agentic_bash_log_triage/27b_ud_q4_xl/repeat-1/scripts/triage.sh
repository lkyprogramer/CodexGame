#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <logfile>" >&2
  exit 1
fi

logfile="$1"

# Filter ERROR lines, extract signature (everything after level), count, sort by count desc
awk '
  $2 == "ERROR" {
    # Reconstruct signature from field 3 onwards
    sig = ""
    for (i = 3; i <= NF; i++) {
      if (i > 3) sig = sig " "
      sig = sig $i
    }
    count[sig]++
  }
  END {
    for (sig in count) {
      print count[sig], sig
    }
  }
' "$logfile" | sort -rn -k1,1
