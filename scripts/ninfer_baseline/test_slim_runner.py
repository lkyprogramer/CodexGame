import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import runner
import slim_plan
import slim_runner


class SlimTests(unittest.TestCase):
    def test_reduced_plan_keeps_all_contexts_and_pi_priority_without_p95_claim(self):
        pairs = slim_plan.measurement_pairs()
        self.assertEqual(len(pairs), 93)
        self.assertEqual(sum(p["kind"] == "core" for p in pairs), 87)
        self.assertEqual(len(slim_plan.state_ids()), 48)
        self.assertEqual({p["p"] for p in pairs if p["o"] == 512 and p["track"] == slim_plan.PRODUCTION},
                         set(runner.LENGTHS))
        self.assertEqual(2*len(pairs)+44+len(slim_plan.state_ids()), 278)

    def save_record(self, root, ident, cache, stamp, request=None, failures=None):
        body = request or runner.synthetic("free_java", "fixture")
        body["max_tokens"] = 512
        path = root / "requests" / ident
        path.mkdir(parents=True)
        runner.atomic(path / "request.json", body)
        with gzip.open(path / "raw.json.gz", "wb") as f:
            f.write(b'{}')
        row = {"id": ident, "start_utc": stamp, "group": "core", "cache": cache,
               "prompt_tokens": 1024, "target_prompt_tokens": 1024, "requested_output_tokens": 512,
               "request_sha256": runner.sha(runner.encode(body)),
               "raw_sha256": runner.sha((path / "raw.json.gz").read_bytes()),
               "failures": failures or [], "extra": {"workload": "free_java", "track": slim_plan.PRODUCTION},
               "result": {"computed_prefill_tokens": 1024 if cache == "request_cold" else 1,
                          "prefix_cache_hit_tokens": 0 if cache == "request_cold" else 1023}}
        runner.atomic(path / "record.json", row)
        return row

    def test_reuse_earliest_intact_pair_not_fastest_or_mismatched_warm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cold = self.save_record(root, "early-cold", "request_cold", "01")
            wrong = runner.synthetic("free_java", "different")
            rows = [self.save_record(root, "later-cold", "request_cold", "03"),
                    self.save_record(root, "wrong-warm", "warm_prefix", "00", wrong), cold,
                    self.save_record(root, "right-warm", "warm_prefix", "02")]
            chosen = slim_runner.choose_legacy_pair(root, rows, slim_plan.pair("core", 1024, 512, "free_java", slim_plan.PRODUCTION))
            self.assertEqual(chosen[0]["id"], "early-cold")
            self.assertEqual(chosen[1]["id"], "right-warm")

    def test_corrupt_raw_is_not_reused_and_missing_warm_remains_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bad = self.save_record(root, "bad", "request_cold", "00")
            (root / "requests/bad/raw.json.gz").write_bytes(b"")
            good = self.save_record(root, "good", "request_cold", "01")
            chosen = slim_runner.choose_legacy_pair(root, [bad, good], slim_plan.pair("core", 1024, 512, "free_java", slim_plan.PRODUCTION))
            self.assertEqual(chosen[0]["id"], "good")
            self.assertIsNone(chosen[1])
            self.assertFalse(slim_runner.intact(root, bad))

    def test_pi_budget_preserved_and_mutated_frozen_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            body = runner.synthetic("free_java", "frozen")
            body["max_tokens"] = 32768
            path = root / "wire.json"
            runner.atomic(path, body)
            case = {"payload_file": path.name, "payload_sha256": runner.sha(path.read_bytes())}
            transformed = slim_runner.pi_body(root, case, 20261020)
            self.assertEqual(transformed["max_tokens"], 32768)
            self.assertEqual(transformed["temperature"], 1)
            self.assertEqual(transformed["seed"], 20261020)
            body["max_tokens"] = 512
            runner.atomic(path, body)
            with self.assertRaisesRegex(RuntimeError, "hash"):
                slim_runner.pi_body(root, case, 20261020)

    def test_remaining_requires_all_known_coding_results_for_this_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = {"coding_case_ids": [f"case-{i}" for i in range(8)]}
            receipt = {"manifest_sha256": "frozen", "known_completed_cases": 8,
                       "unknown_outcomes": False,
                       "cases": [{"id": ident, "repeat": 1, "status": "FAIL"}
                                 for ident in manifest["coding_case_ids"]]}
            runner.atomic(root / "coding-handoff.json", receipt)
            self.assertEqual(slim_runner.check_coding_handoff(root, manifest, "frozen"), receipt)
            for field, value in [("manifest_sha256", "changed"), ("known_completed_cases", 7),
                                 ("unknown_outcomes", True)]:
                changed = {**receipt, field: value}
                runner.atomic(root / "coding-handoff.json", changed)
                with self.assertRaises(RuntimeError):
                    slim_runner.check_coding_handoff(root, manifest, "frozen")

    def test_reused_cold_is_primed_before_collecting_missing_warm(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            old = root / "old"
            cold = self.save_record(old, "old-cold", "request_cold", "01")
            pair = slim_plan.pair("core", 1024, 512, "free_java", slim_plan.PRODUCTION)
            obj = slim_runner.SlimRunner.__new__(slim_runner.SlimRunner)
            obj.root = root
            obj.resolutions = {pair["id"]+"-cold": {"source_root": str(old), "source_id": "old-cold"}}
            obj.results = {}
            obj.status = {}
            calls = []
            def request(ident, body, **kw):
                calls.append((ident, body, kw))
                return {"id": ident}
            obj.request = request
            obj.resolve = lambda *args: None
            obj.collect_pair(pair)
            self.assertEqual([c[2]["group"] for c in calls], ["resume_priming", "core"])
            self.assertEqual(calls[1][2]["cache"], "warm_prefix")
            self.assertEqual(runner.sha(runner.encode(calls[1][1])), cold["request_sha256"])


if __name__ == "__main__":
    unittest.main()
