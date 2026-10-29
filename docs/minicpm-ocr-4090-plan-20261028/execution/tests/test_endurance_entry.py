"""E0 entry validation only; no model, Docker or long-running workload is used."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


SPEC = importlib.util.spec_from_file_location("endurance_entry", Path(__file__).parents[1] / "deploy/run_endurance.py")
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


class EnduranceEntryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "images").mkdir()
        self.manifest = self.root / "formal.json"
        self.warmup = self.root / "warmup.json"
        self.policy = self.root / "policy.json"
        self.argv = ["python", "vllm", "serve", "--standard"]
        self.policy_data = {"policy": {"dtype": "bfloat16", "max_model_len": 16384,
                                       "gpu_memory_utilization": .65, "max_num_seqs": 4,
                                       "max_num_batched_tokens": 8192, "cpu_cores": 8, "ram_gib": 32},
                            "cpuset": "0-7", "argv": self.argv}
        self.policy.write_text(json.dumps(self.policy_data))
        development = []
        for index in range(4):
            path = self.root / "images" / f"dev{index}.png"
            Image.new("RGB", (8, 8), (0, index + 1, 0)).save(path)
            development.append({"page_id": f"dev{index}", "document_id": f"devdoc{index}",
                                "path": str(path), "kind": "image", "split": "development"})
        self.warmup.write_text(json.dumps({"pages": development}))

    def formal_pages(self, count):
        pages = []
        for index in range(count):
            image = Image.new("RGB", (8, 8), (index + 1, 0, 0))
            path = self.root / "images" / f"formal{index}.png"
            image.save(path)
            pages.append({"page_id": f"page{index}", "document_id": f"doc{index // 17}",
                          "source_family_id": f"family{index // 17}", "source_id": f"source{index}",
                          "path": str(path), "kind": "image", "unit_kind": "page",
                          "expected_pixel_hash": hashlib.sha256(image.tobytes()).hexdigest()})
        self.manifest.write_text(json.dumps({"pages": pages}))
        return pages

    def args(self, count):
        return ["--adapter", "ovis", "--manifest", str(self.manifest), "--warmup-manifest", str(self.warmup),
                "--policy", str(self.policy), "--out", str(self.root / f"run{count}"),
                "--model-dir", str(self.root), "--base-url", "http://127.0.0.1:1/v1", "--cycles", "1"]

    def test_40_and_49_page_workloads_keep_unique_input_counts_and_family_identity(self):
        for count in (40, 49):
            with self.subTest(count=count):
                source = self.formal_pages(count)
                with patch.object(entry, "live_service_argv", return_value=self.argv), \
                        patch.object(entry, "run_pages", return_value={"endurance_status": "PASS"}) as run:
                    self.assertEqual(entry.main(self.args(count)), 0)
                pool, config = run.call_args.args
                self.assertEqual(len(pool), count)
                self.assertEqual({case["source_id"] for case in pool}, {case["source_id"] for case in source})
                self.assertEqual({case["source_family_id"] for case in pool}, {case["source_family_id"] for case in source})
                self.assertEqual(config["admission_window_seconds"], 3600)
                self.assertEqual(config["minimum_completed_pages"], 300)
                state = json.loads((self.root / f"run{count}-state/state.json").read_text())
                self.assertEqual(state["unique_base_page_count"], count)
                self.assertEqual(state["quality_samples_added_by_repetition"], 0)
                self.assertNotIn("independent_quality_sample_count", state)

    def test_stale_policy_argv_is_rejected_before_running_or_writing_state(self):
        self.formal_pages(49)
        with patch.object(entry, "live_service_argv", return_value=self.argv + ["--changed"]), \
                patch.object(entry, "run_pages") as run, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                entry.main(self.args(49))
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()
        self.assertFalse((self.root / "run49-state").exists())

    def test_other_input_counts_and_duplicate_pixels_are_rejected(self):
        for count, duplicate in ((41, False), (49, True)):
            with self.subTest(count=count, duplicate=duplicate):
                pages = self.formal_pages(count)
                if duplicate:
                    pages[1]["expected_pixel_hash"] = pages[0]["expected_pixel_hash"]
                    self.manifest.write_text(json.dumps({"pages": pages}))
                with patch.object(entry, "run_pages") as run, contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit):
                        entry.main(self.args(count))
                run.assert_not_called()

    def test_live_service_argv_reads_pid_one_without_fallback(self):
        with patch.object(entry.Path, "read_bytes", autospec=True, return_value=b"python\0vllm\0serve\0") as read:
            self.assertEqual(entry.live_service_argv(), ["python", "vllm", "serve"])
        self.assertEqual(read.call_args.args[0], Path("/proc/1/cmdline"))


if __name__ == "__main__":
    unittest.main()
