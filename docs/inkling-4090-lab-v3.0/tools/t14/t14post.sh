O=$(cat ~/inkling-lab-v3/runs/t14/LATEST)
~/inkling-lab-v3/venv/bin/python -I ~/inkling-lab-v3/runs/t14_report.py $O
cd $O
for f in pair_*.csv; do b=$(basename $f .csv); python3 ~/inkling-lab-v3/pkg/tools/paired_stats.py --input $f --output $b.json >/dev/null && echo "== $f" && head -c 900 $b.json; echo; done
echo "clock/temp:"; awk -F, '{print $4}' gpu.csv | sort | uniq -c | sort -rn | head -3; awk -F, '{print $5}' gpu.csv | sort -n | tail -1
