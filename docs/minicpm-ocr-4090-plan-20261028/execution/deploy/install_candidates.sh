#!/usr/bin/env bash
set -euo pipefail
for _ in $(seq 1 900); do
    test -f /work/evidence/bootstrap-complete.txt && break
    sleep 1
done
test -f /work/evidence/bootstrap-complete.txt
python3 /work/deploy/run_job.py --root /work --name install-ovis -- bash /work/deploy/install_ovis.sh &
ovis_job=$!
python3 /work/deploy/run_job.py --root /work --name install-mini -- bash /work/deploy/install_mini.sh &
mini_job=$!
ovis_status=0
mini_status=0
wait "$ovis_job" || ovis_status=$?
wait "$mini_job" || mini_status=$?
test "$ovis_status" -eq 0
test "$mini_status" -eq 0
