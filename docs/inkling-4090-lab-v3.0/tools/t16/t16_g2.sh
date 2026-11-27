#!/usr/bin/env bash
# T16: G2 / G3 after a numeric change, with the existing scripts in order (each writes its own
# run and LATEST pointer): w2.sh (V4 against N0, V5 / V6), t13.sh (V8, DSpark teacher-forced),
# t19c.sh + t19c_judge.sh (V3 verify-model, num-3 on hold-out set C, repeatability), t14.sh with
# the two Astral configurations (G3; llama.cpp is unchanged and not re-run), then T20 (t20.sh +
# t20_judge.sh: num-3 for set B prefill / decode / verify k = 1, 3, 7; set D is a known FAIL).
# T20 was missing in T16 round 1, which hid a decode regression (07, T16 round 2).
set -u
source "$HOME/inkling-lab-v3/env.sh"; P="$LAB/pkg/tools"; R="$LAB/runs"
echo "binary: $(sha256sum "$LAB/src/astral/target/release/astral")"
bash "$P/w2/w2.sh"; W=$(cat "$R/w2/LATEST"); cat "$W/n0.json" "$W/astral_vs_llama.json"; head -c 300 "$W/v567.json"; echo
bash "$P/w2/t13.sh"; for f in "$W"/t13/spec_*.txt; do tail -1 "$f"; done
bash "$P/t19/t19c.sh" > "$R/t16/t19c.out" 2>&1; C=$(cat "$R/t19/LATEST_C"); cat "$C/STATUS"; tail -3 "$C/verify-model.txt"
bash "$P/t19/t19c_judge.sh" "$C"
CONFIGS="astral-ar astral-dspark" bash "$P/t14/t14.sh"
"$LAB/venv/bin/python" -I "$R/t14_report.py" "$(cat "$R/t14/LATEST")"
bash "$P/t20/t20.sh" > "$R/t16/t20.out" 2>&1; bash "$P/t20/t20_judge.sh" | grep -E "repeat|num-3"
guard
