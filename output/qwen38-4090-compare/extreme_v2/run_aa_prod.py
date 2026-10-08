#!/usr/bin/env python3
"""A/A noise on production 18343 after one warmup. thinking=none for a stable decode clock."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from abba import aa_noise_pct
from http_client import chat_completion, metrics_delta, metrics_snapshot

BASE = "http://127.0.0.1:18343/v1"
METRICS = "http://127.0.0.1:18343/metrics"
MODEL = "openclaw/Qwen3.8-27B-WORK"
PAD = "Java reconnect invariant token pad. " * 120
USER = "Write one Java identifier: reconnectTimeoutMs"


def sample() -> dict:
    return chat_completion(
        BASE,
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a terse Java agent. " + PAD},
            {"role": "user", "content": USER},
        ],
        max_tokens=32,
        stream=True,
        reasoning_effort="none",
    )


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("aa_prod.json")
    warm = sample()
    print("WARM", warm.get("ok"), warm.get("decode_tps"), warm.get("error"), flush=True)
    before = metrics_snapshot(METRICS)
    rows = []
    tps = []
    ttfts = []
    for i in range(8):
        r = sample()
        rows.append(r)
        if not r["ok"] or not r.get("decode_tps"):
            print("FAIL sample", i, r.get("error"), flush=True)
            out.write_text(json.dumps({"ok": False, "rows": rows, "warm": warm}, indent=2))
            return 1
        tps.append(float(r["decode_tps"]))
        if r.get("ttft_s") is not None:
            ttfts.append(float(r["ttft_s"]))
        print(
            f"AA[{i}] decode_tps={r['decode_tps']:.3f} ttft={r['ttft_s']} cached={r['cached_tokens']}",
            flush=True,
        )
    after = metrics_snapshot(METRICS)
    noise = aa_noise_pct(tps)
    ttft_noise = aa_noise_pct(ttfts) if len(ttfts) >= 2 else None
    payload = {
        "ok": True,
        "n": 8,
        "decode_tps": tps,
        "ttft_s": ttfts,
        "aa_noise_pct_decode": noise,
        "aa_noise_pct_ttft": ttft_noise,
        "aa_noise_gate_3pct_decode": noise <= 3.0,
        "mean_decode_tps": sum(tps) / len(tps),
        "metrics_delta": metrics_delta(before, after),
        "warm": warm,
        "rows": rows,
        "reasoning_effort": "none",
        "profile": "prod 262144 rk4v4-e8 MTP3",
    }
    out.write_text(json.dumps(payload, indent=2))
    print(
        json.dumps(
            {
                k: payload[k]
                for k in (
                    "ok",
                    "aa_noise_pct_decode",
                    "aa_noise_gate_3pct_decode",
                    "aa_noise_pct_ttft",
                    "mean_decode_tps",
                    "metrics_delta",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
