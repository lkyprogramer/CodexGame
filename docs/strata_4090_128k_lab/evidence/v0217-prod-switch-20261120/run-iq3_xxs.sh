#!/bin/sh
# Strata v0.2.17 production tree (2026-11-20): tag v0.2.17 (commit 12d491da4) + PT0/#1536 port (v0216-pt0-reply-reuse.patch,
# identical to CodexGame patches/v0217-pt0-reply-reuse.patch), engine 0.1.63 self-built with CUDA 12.3 for sm_89.
# Config = lab baseline B2: production args + --lookup-max-t 0 --conversation-spill-mib 0 --ple-io direct, env STRATA_ROUTE_TAIL_SKIP=7
# (0.2.17 turned the tail skip off by default; 0.2.3 and B1 ran with rank 7).  State dirs are private to this tree.
# Rollback: /home/hhtele/strata-0.2.3/run-iq3_xxs.sh.pre-0217-20261120 back over /home/hhtele/strata-0.2.3/run-iq3_xxs.sh.
cd "/home/hhtele/strata-0.2.17"
export STRATA_REPLY_REUSE=1        # #1536: the next turn reuses the reply's own token ids
export STRATA_PRESERVE_THINKING=0  # CFG-PT: earlier turns' thinking is not rendered (a request's chat_template_kwargs wins)
export STRATA_DATA_DIR="/home/hhtele/strata-0.2.17/state/data" STRATA_DRAFT_COSTS_DIR="/home/hhtele/strata-0.2.17/state/draft-costs"
export XDG_DATA_HOME="/home/hhtele/strata-0.2.17/state/xdg-data" XDG_CONFIG_HOME="/home/hhtele/strata-0.2.17/state/xdg-config" XDG_CACHE_HOME="/home/hhtele/strata-0.2.17/state/xdg-cache"
export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
exec "/home/hhtele/strata-0.2.17/python/bin/python3" -B "/home/hhtele/strata-0.2.17/terminal/serve/server.py" "--engine" "strata" "--config" "/home/hhtele/strata-0.2.17/strata-iq3_xxs.json" "--port" "18343"
