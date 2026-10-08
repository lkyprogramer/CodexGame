"""Live HTTP tests against production 18343: cache negative control + usage shape.

Skip if the server is down. These call the real Chat Completions path.
"""
from __future__ import annotations

import os
import unittest
import uuid

from http_client import chat_completion

BASE = os.environ.get("NINFER_BASE", "http://127.0.0.1:18343/v1")
MODEL = os.environ.get("NINFER_MODEL", "openclaw/Qwen3.8-27B-WORK")


def _pad_messages(user: str) -> list[dict[str, str]]:
    pad = ("Java reconnect invariant token pad. " * 200)
    return [
        {"role": "system", "content": "You are a coding agent. " + pad},
        {"role": "user", "content": user},
    ]


class TestLiveHttpNegative(unittest.TestCase):
    def test_usage_has_openai_cached_tokens_field(self) -> None:
        r = chat_completion(
            BASE,
            model=MODEL,
            messages=_pad_messages("Reply with PONG."),
            max_tokens=8,
            stream=False,
        )
        if not r["ok"]:
            self.skipTest(f"server not reachable: {r['error']}")
        usage = r["usage"]
        self.assertIsInstance(usage, dict)
        self.assertIn("prompt_tokens_details", usage)
        self.assertIn("cached_tokens", usage["prompt_tokens_details"])

    def test_unique_prompt_is_cold_vs_exact_repeat_hits(self) -> None:
        nonce = uuid.uuid4().hex
        cold = chat_completion(
            BASE,
            model=MODEL,
            messages=_pad_messages(f"Nonce {nonce}. Reply PONG."),
            max_tokens=8,
            stream=False,
        )
        if not cold["ok"]:
            self.skipTest(f"server not reachable: {cold['error']}")
        # Negative control: first unique prompt must not report a full-prefix hit.
        pt = cold["prompt_tokens"] or 0
        cached = cold["cached_tokens"] if cold["cached_tokens"] is not None else 0
        self.assertLess(cached, max(pt * 0.5, 1), f"unique prompt was hot: cached={cached} pt={pt}")

        exact = chat_completion(
            BASE,
            model=MODEL,
            messages=_pad_messages(f"Nonce {nonce}. Reply PONG."),
            max_tokens=8,
            stream=False,
        )
        self.assertTrue(exact["ok"], exact["error"])
        hit = exact["cached_tokens"] if exact["cached_tokens"] is not None else 0
        self.assertGreater(hit, 0, "exact repeat reported no cache hit (negative control would be indistinguishable)")


if __name__ == "__main__":
    unittest.main()
