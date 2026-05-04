#!/usr/bin/env bash
set -euo pipefail

# Filter ERROR lines, remove variable parameters (key=value), count signatures
grep " ERROR " "$1" | \
  sed 's/ [^ ]*=[^ ]*//g' | \
  sort | \
  uniq -c | \
  sed 's/^ *//'
