#!/usr/bin/env python3
"""Exclusive GPU: MTP W=3 vs W=6 vs spec-off (negative), ctx=200192. Always restore prod."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from abba import aa_noise_pct, abba_mean_uplift_pct
from http_client import chat_completion, metrics_delta, metrics_snapshot

HOST = "hhtele@192.168.10.29"
BASE = "http://127.0.0.1:18030/v1"
METRICS = "http://127.0.0.1:18030/metrics"
MODEL = "qwen3.8-27b"
PAD = "Java reconnect invariant token pad. " * 120
USER = "Write one Java identifier: reconnectTimeoutMs"
ROOT = Path(__file__).resolve().parent


def sh(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=False)


def ssh(remote: str) -> None:
    sh(["ssh", "-o", "ConnectTimeout=20", HOST, remote])


def tunnel() -> None:
    subprocess.run(["pkill", "-f", "ssh .*18030:127.0.0.1:18030"], check=False)
    time.sleep(0.5)
    sh(
        [
            "ssh",
            "-f",
            "-N",
            "-o",
            "ExitOnForwardFailure=yes",
            "-o",
            "ServerAliveInterval=30",
            "-L",
            "127.0.0.1:18030:127.0.0.1:18030",
            HOST,
        ]
    )
    time.sleep(1)


def restore() -> None:
    ssh(
        "WRAP=/home/hhtele/qwen38-dflash2-20260819/launch/sudo-wrap.sh; "
        "docker rm -f ninfer-4090 >/dev/null 2>&1 || true; "
        "$WRAP systemctl start openclaw-qwen38-ninfer.service || true"
    )
    subprocess.run(["pkill", "-f", "ssh .*18030:127.0.0.1:18030"], check=False)


def start_profile(spec: str, draft: int, ctx: int = 200192) -> None:
    env = (
        f"NINFER_SPEC={spec} DRAFT_TOKENS={draft} NINFER_CTX={ctx} NINFER_KV=rk4v4-e8 "
        "bash /tmp/4090_test_start.sh"
    )
    ssh(env)
    tunnel()


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


def eight(tag: str) -> dict:
    warm = sample()
    print(tag, "WARM", warm.get("ok"), warm.get("decode_tps"), warm.get("error"), flush=True)
    before = metrics_snapshot(METRICS)
    rows = []
    tps = []
    for i in range(8):
        r = sample()
        rows.append(r)
        if not r["ok"] or not r.get("decode_tps"):
            raise RuntimeError(f"{tag} sample {i} failed: {r.get('error')}")
        tps.append(float(r["decode_tps"]))
        print(f"{tag}[{i}] {tps[-1]:.3f} ttft={r['ttft_s']} cached={r['cached_tokens']}", flush=True)
    after = metrics_snapshot(METRICS)
    noise = aa_noise_pct(tps)
    return {
        "tag": tag,
        "decode_tps": tps,
        "aa_noise_pct": noise,
        "aa_ok": noise <= 3.0,
        "mean": sum(tps) / len(tps),
        "metrics_delta": metrics_delta(before, after),
        "warm": warm,
        "rows": rows,
    }


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("suffix_mtp_v1.json")
    sh(["scp", "-o", "ConnectTimeout=15", str(ROOT / "4090_test_start.sh"), f"{HOST}:/tmp/4090_test_start.sh"])
    ssh("chmod +x /tmp/4090_test_start.sh")
    payload: dict = {"ok": False}
    try:
        start_profile("mtp", 3)
        a = eight("W3")
        start_profile("mtp", 5)
        b = eight("W5")
        start_profile("off", 0)
        n = eight("NOSPEC")
        uplift = abba_mean_uplift_pct(a["decode_tps"], b["decode_tps"])
        neg = (a["mean"] - n["mean"]) / a["mean"] * 100.0
        payload = {
            "ok": True,
            "ctx": 200192,
            "kv": "rk4v4-e8",
            "W3": a,
            "W5": b,
            "NOSPEC": n,
            "W5_vs_W3_uplift_pct": uplift,
            "negative_control_mtp_vs_nospec_pct": neg,
            "negative_control_pass": neg >= 15.0,
            "aa_all_pass": a["aa_ok"] and b["aa_ok"] and n["aa_ok"],
            "candidate": "reject_w6_as_default" if uplift <= 3.0 else "w6_candidate_keep_200192",
            "note": "zero bridge; existing MTP only; W<=6; prod not switched",
        }
        print(
            json.dumps(
                {
                    k: payload[k]
                    for k in (
                        "W5_vs_W3_uplift_pct",
                        "negative_control_mtp_vs_nospec_pct",
                        "negative_control_pass",
                        "aa_all_pass",
                        "candidate",
                    )
                },
                indent=2,
            )
        )
    finally:
        restore()
        out.write_text(json.dumps(payload, indent=2, default=str))
        print("wrote", out, flush=True)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
