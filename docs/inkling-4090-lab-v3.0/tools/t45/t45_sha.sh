#!/usr/bin/env bash
# T45 regression: with decode = a one-row verify pass, speculative decoding must give exactly the
# plain greedy tokens. For 3 prompts (T13's p00 / p05 / p10), 256 tokens: spec-generate with
# DSpark at fixed k = 1, 3, 6 (ASTRAL_SPEC_FIXED=1), DSpark adaptive (k <= 6) and DFlash2 (k = 7),
# each also decoding plainly; the SHA-256 of every token list (spec and plain) must be one value
# per prompt, and each run must report "equals plain greedy for the first 256 / 256".
# usage: t45_sha.sh; exit 0 all equal, 1 a difference, 3 guard.
set -u
source "$HOME/inkling-lab-v3/env.sh"
A1="$MODELS/unsloth/Mainline_Support/Inkling-2-Mini-UD-Q4_K_XL.gguf"; AST="$LAB/src/astral/target/release/astral"
O="$LAB/runs/t45/$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$O"; echo "$O" > "$LAB/runs/t45/LATEST"
guard || exit 3
{ git -C "$LAB/src/astral" rev-parse HEAD; git -C "$LAB/src/astral" status --short; sha256sum "$AST"; } > "$O/identity.txt"
W=$(cat "$LAB/runs/w2/LATEST")/t13
rc=0
for p in p00 p05 p10; do
  for c in k1 k3 k6 burst df2; do
    case $c in
      k*) e=(ASTRAL_SPEC_FIXED=1); d="$MODELS/inkling-native"; k=${c#k};;
      burst) e=(X=1); d="$MODELS/inkling-native"; k=6;;
      df2) e=(X=1); d="$MODELS/dflash2"; k=7;;
    esac
    env "${e[@]}" "$AST" spec-generate "$A1" "$d" $k 256 "@$W/$p.ids" > "$O/$p.$c.txt" 2>&1 || { echo "$p $c rc=$?"; rc=1; continue; }
    grep -q "equals plain greedy for the first 256 / 256" "$O/$p.$c.txt" || { echo "$p $c: spec differs from plain"; rc=1; }
    grep -o "spec tokens: \[[^]]*\]" "$O/$p.$c.txt" | sha256sum | cut -c1-16 > "$O/$p.$c.sha"
  done
  n=$(cat "$O"/$p.*.sha | sort -u | wc -l); echo "$p: $n distinct token SHA over k1 k3 k6 burst df2 ($(cat "$O/$p.k1.sha"))"; [ "$n" = 1 ] || rc=1
done
guard || exit 3
echo "rc=$rc" | tee "$O/STATUS"
exit $rc
