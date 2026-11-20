#!/bin/sh
# Read-only production observation (2026-11-20): request summary since the current engine start + the engine's memory/THP/swap.
# Usage: observe.sh [all]   ("all" = every engine start in the log, not only the current one)
L=/home/hhtele/strata-0.2.17/strata-iq3_xxs.log
D=/data/strata-data/prod-observe
PY=/home/hhtele/strata-0.2.17/python/bin/python3
echo "unit: $(systemctl is-active openclaw-qwen38-next.service)"
if [ "$1" = all ]; then
  "$PY" -B "$D/prodlog.py" "$L" --json "$D/last-all.json"
else
  SINCE=$(grep -a "engine started:" "$L" | tail -1 | cut -c10-28)
  echo "since: $SINCE"
  "$PY" -B "$D/prodlog.py" "$L" --since "$SINCE" --json "$D/last.json"
fi
P=$(pgrep -f "^/home/hhtele/strata-0.2.17/engine/strata --serve" | head -1)
if [ -n "$P" ]; then
  echo "engine pid $P:"; grep -E "^(Rss|Anonymous|AnonHugePages|Swap):" "/proc/$P/smaps_rollup"
fi
grep -E "^(MemAvailable|SwapFree):" /proc/meminfo
