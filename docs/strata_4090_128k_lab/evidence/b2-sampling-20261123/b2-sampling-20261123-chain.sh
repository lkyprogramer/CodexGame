set -u
cd /data/strata-data/upgrade-gate
P=/home/hhtele/anaconda3/bin/python
LB=b2-sampling-20261123
LOG=/home/hhtele/strata-0.2.17/strata-iq3_xxs.log
waitidle() { for i in $(seq 1 360); do
  h=$(curl -s -o /dev/null -w "%{http_code}" -m 3 http://127.0.0.1:18343/health || true); age=$(( $(date +%s) - $(stat -c %Y $LOG) ))
  if [ "$h" = 200 ] && [ $age -ge 90 ]; then echo "$(date +%T) idle (log age ${age}s)"; return 0; fi; sleep 10; done; echo "$(date +%T) never idle"; return 1; }
step() { name=$1; shift; waitidle || exit 4; echo "$(date +%T) start $name"; $P -B upgrade_gate.py "$@" > $LB-$name.log 2>&1 < /dev/null; rc=$?; echo "$(date +%T) end $name rc=$rc"; tail -1 $LB-$name.log | cut -c1-600; return $rc; }
step C0c replay $LB --run C0c || { echo STOP_CHAIN; exit 5; }
$P -B - <<'PY' || { echo "STOP_ENV or invalid control"; exit 6; }
import json, sys
c = json.load(open("b2-sampling-20261123/RUN-C0c.json")); o = [json.load(open("b2-adapt-long-20261123/RUN-%s.json" % n))["ge32k"] for n in ("C0a", "C0b")]
d = {k: c["ge32k"][k] / (sum(x[k] for x in o) / 2) - 1 for k in ("ms_win", "decode_tok_s")}
print("C0c valid", c["valid"], "drift", d); sys.exit(0 if c["valid"] and all(abs(v) <= 0.03 for v in d.values()) else 1)
PY
step T06 replay $LB --run T06 || { echo STOP_CHAIN; exit 5; }
step T08 replay $LB --run T08 || { echo STOP_CHAIN; exit 5; }
step S06 probe $LB --limit 40 --sampling temperature=0.6 || { echo STOP_CHAIN; exit 5; }
step S08 probe $LB --limit 40 --sampling temperature=0.8 || { echo STOP_CHAIN; exit 5; }
$P -B upgrade_gate.py replay $LB --eval > $LB-eval.log 2>&1; cat $LB-eval.log | cut -c1-3000
T=$($P -B -c "import json; v=json.load(open('$LB/VERDICT.json')); s=v.get('stage2'); print({'T06': '0.6', 'T08': '0.8'}.get(s, ''))")
if [ -n "$T" ]; then step FULL probe $LB --sampling temperature=$T; else echo "no stage 2"; fi
echo "$(date +%T) chain done"
