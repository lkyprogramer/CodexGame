#!/usr/bin/env python3
"""True A-B-B-A x8 (W3 vs W5), plus NOSPEC negative. Restore prod in finally."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from abba import aa_noise_from_a_legs, abba_mean_uplift_pct, abba_pair_means
from http_client import chat_completion, metrics_snapshot

HOST = "hhtele@192.168.10.29"
BASE = "http://127.0.0.1:18030/v1"
MODEL = "qwen3.8-27b"
PAD = "Java reconnect invariant token pad. " * 120
USER = "Write one Java identifier: reconnectTimeoutMs"
ROOT = Path(__file__).resolve().parent


def sh(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True)


def ssh(remote: str, check: bool = True) -> subprocess.CompletedProcess:
    return sh(["ssh", "-o", "ConnectTimeout=25", HOST, remote], check=check)


def tunnel() -> None:
    subprocess.run(["pkill", "-f", "ssh .*18030:127.0.0.1:18030"], check=False)
    time.sleep(0.4)
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


def start_profile(spec: str, draft: int, ctx: int = 200192) -> subprocess.CompletedProcess:
    env = (
        f"NINFER_SPEC={spec} DRAFT_TOKENS={draft} NINFER_CTX={ctx} NINFER_KV=rk4v4-e8 "
        "bash /tmp/4090_test_start.sh"
    )
    cp = ssh(env, check=False)
    if cp.returncode == 0:
        tunnel()
    return cp


def sample() -> dict:
    r = chat_completion(
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
    if not r.get("ok") or not r.get("decode_tps"):
        raise RuntimeError(r.get("error") or "empty decode_tps")
    return r


class Arm:
    def __init__(self) -> None:
        self.spec: str | None = None
        self.draft: int | None = None

    def ensure(self, spec: str, draft: int) -> None:
        if self.spec == spec and self.draft == draft:
            return
        cp = start_profile(spec, draft)
        if cp.returncode != 0:
            raise RuntimeError(f"boot {spec} draft={draft} failed rc={cp.returncode}")
        sample()  # warmup
        self.spec, self.draft = spec, draft


def tps(r: dict) -> float:
    return float(r["decode_tps"])


def main() -> int:
    out = Path(sys.argv[1])
    sh(["scp", "-o", "ConnectTimeout=15", str(ROOT / "4090_test_start.sh"), f"{HOST}:/tmp/4090_test_start.sh"])
    ssh("chmod +x /tmp/4090_test_start.sh")
    payload: dict = {"ok": False, "pattern": "ABBA x8", "A": "mtp W=3", "B": "mtp W=5", "ctx": 200192}
    arm = Arm()
    pairs: list[dict] = []
    try:
        for i in range(8):
            arm.ensure("mtp", 3)
            a1 = sample()
            arm.ensure("mtp", 5)
            b1 = sample()
            b2 = sample()
            arm.ensure("mtp", 3)
            a2 = sample()
            pair = {
                "i": i,
                "a1": tps(a1),
                "b1": tps(b1),
                "b2": tps(b2),
                "a2": tps(a2),
                "rows": {"a1": a1, "b1": b1, "b2": b2, "a2": a2},
            }
            pairs.append(pair)
            print(
                f"ABBA[{i}] A1={pair['a1']:.3f} B1={pair['b1']:.3f} "
                f"B2={pair['b2']:.3f} A2={pair['a2']:.3f}",
                flush=True,
            )
        a_means, b_means = abba_pair_means(pairs)
        uplift = abba_mean_uplift_pct(a_means, b_means)
        aa = aa_noise_from_a_legs(pairs)
        # negative: one NOSPEC boot, 8 samples after warm
        arm.ensure("off", 0)
        ns = []
        for i in range(8):
            ns.append(tps(sample()))
            print(f"NOSPEC[{i}] {ns[-1]:.3f}", flush=True)
        mean_a = sum(a_means) / len(a_means)
        mean_ns = sum(ns) / len(ns)
        neg = (mean_a - mean_ns) / mean_a * 100.0
        payload.update(
            {
                "ok": True,
                "pairs": [{k: p[k] for k in ("i", "a1", "b1", "b2", "a2")} | {"cached_a1": p["rows"]["a1"].get("cached_tokens")} for p in pairs],
                "pair_rows": pairs,
                "a_means": a_means,
                "b_means": b_means,
                "W5_vs_W3_uplift_pct": uplift,
                "aa_noise_pct_from_A_legs": aa,
                "aa_ok": aa <= 3.0,
                "NOSPEC": ns,
                "NOSPEC_mean": mean_ns,
                "negative_control_mtp_vs_nospec_pct": neg,
                "negative_control_pass": neg >= 15.0,
                "candidate": "reject_w5_as_default" if uplift <= 3.0 else "w5_candidate_keep_200192",
                "note": "zero bridge; existing MTP; W<=6; no prod switch",
            }
        )
        print(
            json.dumps(
                {
                    "W5_vs_W3_uplift_pct": uplift,
                    "aa_noise_pct_from_A_legs": aa,
                    "aa_ok": aa <= 3.0,
                    "negative_control_pass": payload["negative_control_pass"],
                    "candidate": payload["candidate"],
                },
                indent=2,
            ),
            flush=True,
        )
    finally:
        restore()
        out.write_text(json.dumps(payload, indent=2, default=str))
        print("wrote", out, flush=True)
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
