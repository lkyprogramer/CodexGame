#!/usr/bin/env bash
set -euo pipefail
# Only stop this task's optional interpreter download if still present.
if test -r /proc/6300/cmdline; then
    command_line=$(tr '\0' ' ' < /proc/6300/cmdline)
    if [[ "$command_line" == *"uv python install 3.12"* ]]; then
        kill -TERM 6300
    fi
fi
python3.12 --version
gcc-13 --version
/work/releases/tools/bin/uv --version
sha256sum /usr/bin/python3.12 /work/releases/tools/bin/uv
date -u +%FT%TZ > /work/evidence/bootstrap-complete.txt
