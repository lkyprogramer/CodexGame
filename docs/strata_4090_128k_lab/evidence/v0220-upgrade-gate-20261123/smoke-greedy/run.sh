cd "/home/hhtele/strata-0.2.20"
export STRATA_REPLY_REUSE=1 STRATA_PRESERVE_THINKING=0
export STRATA_DATA_DIR="/data/strata-data/upgrade-gate/v0.2.20/smoke/arms/v0220-adapt_lag1-verify_device_hits0/state/data" STRATA_DRAFT_COSTS_DIR="/data/strata-data/upgrade-gate/v0.2.20/smoke/arms/v0220-adapt_lag1-verify_device_hits0/state/draft-costs"
export XDG_DATA_HOME="/data/strata-data/upgrade-gate/v0.2.20/smoke/arms/v0220-adapt_lag1-verify_device_hits0/state/xdg-data" XDG_CONFIG_HOME="/data/strata-data/upgrade-gate/v0.2.20/smoke/arms/v0220-adapt_lag1-verify_device_hits0/state/xdg-config" XDG_CACHE_HOME="/data/strata-data/upgrade-gate/v0.2.20/smoke/arms/v0220-adapt_lag1-verify_device_hits0/state/xdg-cache"
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
exec "/home/hhtele/strata-0.2.20/python/bin/python3" -B "/home/hhtele/strata-0.2.20/terminal/serve/server.py" --engine strata --config "/data/strata-data/upgrade-gate/v0.2.20/smoke/arms/v0220-adapt_lag1-verify_device_hits0/config.json" --port 18089
