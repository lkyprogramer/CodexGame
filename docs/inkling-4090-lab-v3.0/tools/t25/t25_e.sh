#!/usr/bin/env bash
# T25 long context, set E (unseen; the num-4L rule was frozen before this ran): six documents of
# other kinds than set D, chat-templated like D by t20_ids.py (first 24000 characters, the same
# instruction), each followed by 64 greedy llama.cpp tokens; then t25_run.sh and t25_judge.py.
# Negative controls: the serving path with the withdrawn dp4a decode (T16 round 1, failed T20 set B)
# and with two loop passes instead of three (a different model).
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; NATIVE="$MODELS/inkling-native"
AST="$LAB/src/astral/target/release/astral"; PY="$LAB/venv/bin/python"; T="$LAB/pkg/tools/t25"; PORT=18998
LL="$LAB/src/llama.cpp"; AS="$LAB/src/astral"
DOCS=("$LL/tools/server/README.md" "$LL/docs/backend/SYCL.md" "$LL/tools/completion/README.md" \
      /usr/share/common-licenses/GPL-3 "$AS/crates/model/src/dspark.rs" /usr/share/common-licenses/GFDL-1.3)
E="$LAB/runs/t25/inputs-e"; mkdir -p "$E"
guard || exit 3
sha256sum "${DOCS[@]}" > "$E/docs.sha256"
"$AST" serve "$A1" --checkpoint "$NATIVE" --no-draft --host 127.0.0.1 --port $PORT --ctx 16384 > "$E/ids-server.log" 2>&1 & SP=$!
for i in $(seq 1 300); do curl -sf http://127.0.0.1:$PORT/health > /dev/null && break; sleep 1; done
"$PY" -I "$LAB/pkg/tools/t20/t20_ids.py" http://127.0.0.1:$PORT "$E/ids_e.json" d "${DOCS[@]}" | tee "$E/ids.txt"; rc=$?
kill $SP; wait $SP 2> /dev/null; sleep 3
[ $rc -eq 0 ] || exit 1
IDS="$E/ids_e.json" TAG=e MAN=none GEN=64 NEGS="dp4a:ASTRAL_DECODE_DP4A=1 r2:ASTRAL_PASSES=2" bash "$T/t25_run.sh"; rr=$?
O=$(cat "$LAB/runs/t25/LATEST_e")
# T41: any failed step makes the run incomplete; the judge's exit code is the script's exit code.
if [ $rr -ne 0 ] || grep -q ' rc=[1-9]' "$O/STATUS"; then echo "run incomplete (t25_run rc=$rr)" | tee -a "$O/STATUS"; exit 2; fi
"$PY" -I "$T/t25_judge.py" "$O" e "$T/rule_num4l.json" --cases 6 > "$O/verdict.json"; jr=$?; echo "judge rc=$jr" | tee -a "$O/STATUS"
sha256sum "$T/rule_num4l.json" "$T/t25_judge.py" "$T/negs_expect.json" > "$O/rule.sha256"
cat "$O/verdict.json"
guard || exit 3
exit $jr
