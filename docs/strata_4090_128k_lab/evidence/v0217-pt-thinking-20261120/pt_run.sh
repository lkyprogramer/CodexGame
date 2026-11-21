#!/bin/bash
# waits for the gate run to end, then PT0 and PT1 agent loads on lab servers; production restarted on exit
set -u
cd /data/strata-data/v0217-pt-20261120
while pgrep -f "gate_run.sh" >/dev/null; do sleep 30; done
sleep 60
sudo -n /usr/bin/systemctl stop openclaw-qwen38-next.service; echo "$(date +%T) production stop rc=$?"
trap 'sudo -n /usr/bin/systemctl start openclaw-qwen38-next.service; echo "$(date +%T) production start rc=$?"' EXIT
sleep 15
PY=/home/hhtele/anaconda3/bin/python
for a in pt0:STRATA_PRESERVE_THINKING=0 pt1:STRATA_PRESERVE_THINKING=1; do
  n=${a%%:*}; e=${a#*:}
  $PY -u -B pisim2.py $n $e > $n.log 2>&1; echo "$(date +%T) $n rc=$?"
  sleep 20
done
echo "$(date +%T) DONE"
