set -u
cd /data/strata-data/upgrade-gate
P=/home/hhtele/anaconda3/bin/python
LOG=/home/hhtele/strata-0.2.17/strata-iq3_xxs.log
waitidle() { for i in $(seq 1 360); do
  h=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:18343/health); age=$(( $(date +%s) - $(stat -c %Y $LOG) ))
  if [ "$h" = 200 ] && [ $age -ge 90 ]; then echo "$(date +%T) idle (log age ${age}s)"; return 0; fi; sleep 10; done; echo "$(date +%T) never idle"; return 1; }
run() { name=$1; shift; waitidle || exit 4; echo "$(date +%T) start $name $*"; $P -B upgrade_gate.py probe b2-adapt-20261123 --limit 40 "$@" > b2-adapt-20261123-$name.log 2>&1 < /dev/null; echo "$(date +%T) end $name rc=$?"; }
run A1 --arg adapt-every=2
run A2 --arg adapt-decay=0.92
run P1 --arg expert-profile=/data/strata-data/upgrade-gate/b2-adapt-20261123/profile-b2arm-learned.bin
echo "$(date +%T) chain done"
