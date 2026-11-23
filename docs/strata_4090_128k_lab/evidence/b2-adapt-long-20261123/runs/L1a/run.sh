cd "/home/hhtele/strata-0.2.17"
export STRATA_REPLY_REUSE=1 STRATA_PRESERVE_THINKING=0
export STRATA_DATA_DIR="/data/strata-data/upgrade-gate/b2-adapt-long-20261123/runs/L1a/state/data" STRATA_DRAFT_COSTS_DIR="/data/strata-data/upgrade-gate/b2-adapt-long-20261123/runs/L1a/state/draft-costs"
export XDG_DATA_HOME="/data/strata-data/upgrade-gate/b2-adapt-long-20261123/runs/L1a/state/xdg-data" XDG_CONFIG_HOME="/data/strata-data/upgrade-gate/b2-adapt-long-20261123/runs/L1a/state/xdg-config" XDG_CACHE_HOME="/data/strata-data/upgrade-gate/b2-adapt-long-20261123/runs/L1a/state/xdg-cache"
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
exec "/home/hhtele/strata-0.2.17/python/bin/python3" -B "/home/hhtele/strata-0.2.17/terminal/serve/server.py" --engine strata --config "/data/strata-data/upgrade-gate/b2-adapt-long-20261123/runs/L1a/config.json" --port 18089
