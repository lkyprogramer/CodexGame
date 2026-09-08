#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import http_bench as hb

ROOT = Path(__file__).resolve().parents[1]
RES = Path(os.environ.get("RESULTS_ROOT", str(ROOT / "results"))) / os.environ.get("BACKEND", "work")
RES.mkdir(parents=True, exist_ok=True)


def main() -> None:
    target = int(os.getenv("CACHE_PROMPT_TOKENS", "100000"))
    corpus, meta = hb.prompt_for(target)
    base = "This is a Java repository snapshot. Remember the release marker and analyze reconnect invariants.\n" + corpus
    m1 = [{"role": "user", "content": base}]
    print("[cache] cold", flush=True)
    outn = int(os.getenv("CACHE_OUTPUT_TOKENS", "96"))
    r1 = hb.stream_chat(m1, outn, "cache-cold")
    print("[cache] exact", flush=True)
    r2 = hb.stream_chat(m1, outn, "cache-exact")
    tail = "\n".join(f"TOOL_RESULT line={i} reconnectAttempt={i%3} status=OK" for i in range(300))
    m3 = m1 + [
        {"role": "assistant", "content": r1.get("text") or ""},
        {
            "role": "user",
            "content": "A tool just returned the following new tail. Re-evaluate only what changed and state the original RELEASE_NEEDLE exactly.\n"
            + tail,
        },
    ]
    print("[cache] append", flush=True)
    r3 = hb.stream_chat(m3, max(outn, 128), "cache-append")
    rows = [r1, r2, r3]
    for r in rows:
        r["needle"] = meta["needle"]
        r["needle_ok"] = meta["needle"] in (r.get("text") or "")
        print(
            f"[cache] {r['tag']} pt={r.get('prompt_tokens')} cached={r.get('cached_tokens')} "
            f"ttft={r.get('ttft_s')} wall={r.get('wall_s')}",
            flush=True,
        )
    (RES / "cache_bench.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
