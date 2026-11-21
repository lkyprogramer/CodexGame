#!/bin/bash
# b2 -> ts0 -> pairs + quality_gate; production is restarted on exit whatever happens
set -u
cd /data/strata-data/v0217-gate-20261120
PY=/home/hhtele/anaconda3/bin/python
trap 'sudo -n /usr/bin/systemctl start openclaw-qwen38-next.service; echo "$(date +%T) production start rc=$?"' EXIT
complete() { $PY -c "import json;p=json.load(open('PREREG.json'));r=[json.loads(l) for l in open('arms/$1/rows.jsonl')];import sys;sys.exit(0 if len(r)==p['n'] and not any('error' in x for x in r) else 1)"; }
$PY -B gate17.py arm b2 STRATA_ROUTE_TAIL_SKIP=7 > b2.log 2>&1
grep -q PILOT_STOP b2.log && { echo "$(date +%T) PILOT_STOP"; exit 0; }
complete b2 || { echo "$(date +%T) b2 incomplete"; exit 1; }
$PY -B gate17.py arm ts0 STRATA_ROUTE_TAIL_SKIP=0 > ts0.log 2>&1
complete ts0 || { echo "$(date +%T) ts0 incomplete"; exit 1; }
$PY -B gate17.py pairs ts0 b2 > pairs.txt 2>&1
$PY -B quality_gate.py --input PAIRS-b2-vs-ts0.json --output GATE-b2-vs-ts0.json > gate.txt 2>&1; echo "$(date +%T) quality_gate rc=$?"
echo "$(date +%T) DONE"
