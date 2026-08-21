#!/usr/bin/env python3
"""Pick the largest passing probe row and write production-text-18343.sh."""

from __future__ import annotations

import json
import sys
from pathlib import Path

MIN_FREE = 1000.0
# 256-token probe is colder than 1024-token fill; gate VRAM here, judge speed in text_eval.
MIN_TPS = 40.0

# Prefer bigger ctx, then q8 over q4 at same ctx, then more free VRAM.
ORDER = [
    ("q4_0", 192000),
    ("q4_0", 170000),
    ("q4_0", 160000),
    ("q8_0", 128000),
    ("q4_0", 128000),
    ("q8_0", 112000),
]


def main() -> None:
    probe = Path(sys.argv[1])
    dest = Path(sys.argv[2])
    llama = Path(sys.argv[3])
    rows = [json.loads(line) for line in probe.read_text().splitlines() if line.strip()]
    passing = [
        r
        for r in rows
        if r.get("ok")
        and (r.get("vram_free_mib") or 0) >= MIN_FREE
        and (r.get("fill256_tps") or 0) >= MIN_TPS
    ]
    chosen = None
    for ctk, ctx in ORDER:
        for r in passing:
            if r.get("ctk") == ctk and int(r.get("ctx") or 0) == ctx:
                chosen = r
                break
        if chosen:
            break
    if chosen is None and passing:
        chosen = sorted(passing, key=lambda r: (int(r["ctx"]), 1 if r["ctk"] == "q8_0" else 0), reverse=True)[0]
    if chosen is None:
        raise SystemExit("no probe row passed gates")
    ctx = int(chosen["ctx"])
    ctk = chosen["ctk"]
    text = f"""#!/usr/bin/env bash
# Frozen TEXT production command. Selected from probe: {chosen.get("name")}
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
source "$ROOT/common.env"
export TRIAL_PORT="${{PORT}}"
export TRIAL_CTX="{ctx}"
export TRIAL_CTK="{ctk}"
export TRIAL_CTV="{ctk}"
exec "$ROOT/llama-text.sh"
"""
    dest.write_text(text)
    dest.chmod(0o755)
    Path(dest.parent / "chosen.json").write_text(json.dumps({"chosen": chosen, "passing": passing, "all": rows}, indent=2) + "\n")
    print(json.dumps({"chosen": chosen}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
