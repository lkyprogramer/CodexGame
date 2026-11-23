set -u
cd /data/strata-data/upgrade-gate
P=/home/hhtele/anaconda3/bin/python
LB=b2-adapt-long-20261123
LOG=/home/hhtele/strata-0.2.17/strata-iq3_xxs.log
waitidle() { for i in $(seq 1 360); do
  h=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:18343/health); age=$(( $(date +%s) - $(stat -c %Y $LOG) ))
  if [ "$h" = 200 ] && [ $age -ge 90 ]; then echo "$(date +%T) idle (log age ${age}s)"; return 0; fi; sleep 10; done; echo "$(date +%T) never idle"; return 1; }
for R in C0a L1a L1b C0b; do
  waitidle || exit 4
  echo "$(date +%T) start $R"
  $P -B upgrade_gate.py replay $LB --run $R > $LB-$R.log 2>&1 < /dev/null; rc=$?
  echo "$(date +%T) end $R rc=$rc"; tail -2 $LB-$R.log
  if [ $rc -ne 0 ] || ! grep -q " valid {" $LB-$R.log; then echo "STOP_CHAIN at $R"; exit 5; fi
done
$P -B upgrade_gate.py replay $LB --eval > $LB-eval.log 2>&1; cat $LB-eval.log
echo "$(date +%T) chain done"
