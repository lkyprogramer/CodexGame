#!/usr/bin/env bash
set -euo pipefail

release_dir="$1"
current_link="./current"

# Run healthcheck first, only switch symlink if it passes
"$release_dir/healthcheck.sh"
ln -sfn "$release_dir" "$current_link"
