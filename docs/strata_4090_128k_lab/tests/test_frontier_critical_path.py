import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("critical_path", ROOT / "tools/frontier/critical_path.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CriticalPathTests(unittest.TestCase):
    def summarize(self, text, suffix=".log", identity=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ("trace" + suffix)
            path.write_text(text)
            return module.summarize_windows([path], identity or {})

    def test_real_native_formats_preserve_source_without_inventing_windows(self):
        text = (
            "strata decode timing: 965 windows, avg T 1.98, 1.59 tokens/window, 13.07 ms/window = adapt wait 0.04 + verify 11.83 (GPU-reach wait 8.95 + per-layer host 2.19 [plan 0.13 actq 0.08 jobs 0.02 CPU 1.85] + stage 0.04)\n"
            "strata serve: prompt 102400 tokens = 0 reused + 102400 read in 26764 ms (3826.0 tok/s), 1538 generated in 12615 ms (121.9 tok/s), drafts accepted 573 of 947, 6 checkpoints\n"
            "[strata] done: 1538 tokens in 43 s (121.9 tok/s) (stop, cancel=False)\n"
            "strata prefill timing: 102400 tokens, GPU timeline 26764 ms\n"
        )
        result = self.summarize(text)
        self.assertEqual(result["WINDOWS"], [])
        self.assertIsNone(result["OBSERVED_WINDOW_UNION_MS"])
        self.assertEqual(result["QUALIFICATION"]["status"], "INSUFFICIENT")
        records = result["TIMING_OBSERVATIONS"]
        self.assertEqual(records[0]["windows"], 965)
        self.assertEqual(records[1]["decode_ms"], 12615)
        self.assertEqual(records[2]["stop_reason"], "stop")
        self.assertEqual([r["source"]["line"] for r in records], [1, 2, 3, 4])
        self.assertEqual(records[0]["source"]["text"], text.splitlines()[0])
        self.assertTrue(all(r["request_id"] is None for r in records))
        self.assertIsNone(result["DEPENDENCIES"]["expert_nt"])

    def test_request_contract_and_legacy_metrics_keep_failures_and_null(self):
        rows = [
            {"request_id": "append_1", "completion_tokens": 18, "decode_ms": None, "execution_status": "FAILED", "failure_kind": "timeout"},
            {"name": "prime", "metrics": {"generated_tokens": 2048, "decode_ms": 13900.3, "read_tokens": 103183}, "response_error": "cancelled"},
        ]
        result = self.summarize("\n".join(map(json.dumps, rows)), ".jsonl")
        self.assertEqual(len(result["REQUESTS"]), 2)
        self.assertIsNone(result["REQUESTS"][0]["decode_ms"])
        self.assertEqual(result["REQUESTS"][1]["response_error"], "cancelled")
        self.assertEqual(result["QUALIFICATION"]["status"], "INSUFFICIENT")

    def windows(self):
        return [{"engine_id": "e", "request_id": "r", "window_id": str(n),
                 "start": start, "end": end, "unit": "ms", "clock_domain": "native_monotonic"}
                for n, (start, end) in enumerate([(0, 10), (5, 15), (20, 25)])]

    def test_clock_attested_overlap_union_is_coverage_not_headroom(self):
        identity = {"clock_evidence": {"verified": True, "engine_id": "e", "clock_domain": "native_monotonic", "evidence_ref": "clock-receipt:1"}}
        result = self.summarize("\n".join(map(json.dumps, self.windows())), ".jsonl", identity)
        self.assertEqual(result["OBSERVED_WINDOW_UNION_MS"], 20)
        self.assertEqual(result["DEPENDENCIES"]["status"], "UNKNOWN")
        self.assertEqual(result["QUALIFICATION"]["status"], "INSUFFICIENT")
        self.assertIsNone(result["QUALIFICATION"]["removable_ms"])

    def test_wrong_or_unverified_clock_never_produces_union(self):
        for proof in ({}, {"verified": True, "clock_domain": "wall", "engine_id": "e", "evidence_ref": "clock:1"}):
            result = self.summarize(json.dumps(self.windows()[0]), ".jsonl", {"clock_evidence": proof})
            self.assertIsNone(result["OBSERVED_WINDOW_UNION_MS"])
            self.assertEqual(result["QUALIFICATION"]["status"], "INSUFFICIENT")

    def test_duplicate_window_or_bad_interval_rejected(self):
        window = self.windows()[0]
        with self.assertRaisesRegex(ValueError, "duplicate window"):
            self.summarize(json.dumps(window) + "\n" + json.dumps(window), ".jsonl")
        for end in (-1, None, float("nan")):
            with self.subTest(end=end), self.assertRaisesRegex(ValueError, "invalid window interval"):
                self.summarize(json.dumps({**window, "end": end}), ".jsonl")

    def test_bad_json_and_missing_input_are_explicit_failures(self):
        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            self.summarize("{broken}", ".jsonl")
        with self.assertRaises(FileNotFoundError):
            module.summarize_windows(["/does-not-exist/p01.jsonl"], {})


if __name__ == "__main__":
    unittest.main()
