"""Workflow prerequisites and fixed diagnostics; no model or Docker is used."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "run_standard_validation", Path(__file__).parents[1] / "deploy/run_standard_validation.py")
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class StandardValidationTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for folder in ["evidence", "results", "deploy", "ocrbench"]:
            (self.root / folder).mkdir()
        for filename in ["probe_runtime.py", "deploy/run_quality_suite.py"]:
            (self.root / filename).write_text("fixture\n")
        self.policy = {"policy": {"dtype": "bfloat16", "max_model_len": 16384,
                                  "gpu_memory_utilization": .65, "max_num_seqs": 4,
                                  "max_num_batched_tokens": 8192, "cpu_cores": 8, "ram_gib": 32},
                       "argv": ["fixture"]}
        self.calls = []
        self.normal = "PASS"
        self.dev_ok = True
        self.dev_blocks = [{"block_id": "block-0000", "text": "Development text"}]
        self.dev_text = "Development text"
        self.dev_layout_empty = False
        self.dev_model_calls = 1
        self.dev_write_contracts = True
        self.failed = set()

    def execute(self, command, log, env):
        name = log.stem
        self.calls.append((name, command, env))
        log.write_text("fixture execution\n")
        if name == "probe":
            out = Path(command[command.index("--out") + 1])
            out.mkdir()
            (out / "probe-result.json").write_text(json.dumps({
                "status": "UNAVAILABLE" if self.normal == "PASS" else "FAIL",
                "checks": {"image_tokenize_completion_usage": {"status": self.normal},
                           "disconnect_abort_and_drain": {"status": "UNAVAILABLE"}}}))
            return (2 if self.normal == "PASS" else 1), None
        if name == "dev":
            out = Path(command[command.index("--out") + 1])
            out.mkdir()
            records = []
            for page_id in sorted(validation.KNOWN_TEXT_DEV_PAGES):
                records.append({"page_id": page_id, "status": "PASS",
                                "model_call_count": self.dev_model_calls})
                if self.dev_write_contracts:
                    page_out = out / "pages" / page_id
                    page_out.mkdir(parents=True)
                    (page_out / "result.json").write_text(json.dumps({
                        "page_id": page_id, "status": "PASS", "ordered_blocks": self.dev_blocks,
                        "text": self.dev_text,
                        "layout_empty": self.dev_layout_empty,
                        "request_records": [{"attempts": [{"phase": "completion"}]}]
                        if self.dev_model_calls else [],
                    }))
            (out / "summary.json").write_text(json.dumps({
                "run_status": "COMPLETED", "planned_pages": 4, "submitted_pages": 4,
                "terminal_pages": 4, "pass_pages": 4 if self.dev_ok else 3,
                "documents": [{"document_id": "d1"}, {"document_id": "d2"}],
                "pass_documents": 2 if self.dev_ok else 1,
                "all_document_artifacts_pass": self.dev_ok, "results": records}))
        return (1 if name in self.failed or name == "dev" and not self.dev_ok else 0), None

    def run_workflow(self, adapter="ovis", build_interference=False):
        with patch.object(validation, "runtime_policy", return_value=self.policy), \
                patch.object(validation, "execute", side_effect=self.execute):
            return validation.run(adapter, "test-r1", self.root, build_interference)

    def state(self, adapter="ovis"):
        return json.loads((self.root / "evidence" / f"{adapter}-standard-test-r1/state.json").read_text())

    def test_normal_probe_failure_stops_before_development(self):
        self.normal = "FAIL"
        self.assertEqual(self.run_workflow(), 1)
        self.assertEqual([row[0] for row in self.calls], ["probe"])
        self.assertEqual(self.state()["status"], "STOPPED_PREREQUISITE_FAILED")

    def test_development_failure_stops_before_smoke_and_full(self):
        self.dev_ok = False
        self.assertEqual(self.run_workflow(), 1)
        self.assertEqual([row[0] for row in self.calls], ["probe", "dev"])
        self.assertEqual(self.state()["stages"][1]["status"], "FAIL")

    def test_all_empty_false_pass_rejected_for_both_candidates(self):
        self.dev_blocks = []
        self.dev_layout_empty = True
        self.dev_model_calls = 0
        for adapter in ("mini", "ovis"):
            with self.subTest(adapter=adapter):
                self.calls.clear()
                self.assertEqual(self.run_workflow(adapter), 1)
                self.assertEqual([row[0] for row in self.calls], ["probe", "dev"])
                self.assertEqual(self.state(adapter)["stages"][1]["status"], "FAIL")

    def test_each_nonempty_dev_requirement_is_enforced(self):
        for field, value in (("dev_blocks", []), ("dev_layout_empty", True),
                             ("dev_model_calls", 0), ("dev_model_calls", True),
                             ("dev_write_contracts", False)):
            with self.subTest(field=field, value=value):
                self.setUp()
                setattr(self, field, value)
                self.assertEqual(self.run_workflow(), 1)
                self.assertEqual([row[0] for row in self.calls], ["probe", "dev"])

    def test_empty_or_whitespace_visible_text_rejected_for_both_candidates(self):
        for adapter in ("mini", "ovis"):
            for text in ("", " \t\n\u3000"):
                with self.subTest(adapter=adapter, text=text):
                    self.setUp()
                    self.dev_text = text
                    self.dev_blocks = [{"block_id": "block-0000", "text": text}]
                    self.assertEqual(self.run_workflow(adapter), 1)
                    self.assertEqual([row[0] for row in self.calls], ["probe", "dev"])
                    self.assertEqual(self.state(adapter)["stages"][1]["status"], "FAIL")

    def test_formula_markup_does_not_replace_canonical_visible_text(self):
        self.dev_text = ""
        self.dev_blocks = [{"block_id": "block-0000", "raw_content": "$$x^2$$"}]
        self.assertEqual(self.run_workflow(), 1)
        self.assertEqual([row[0] for row in self.calls], ["probe", "dev"])

    def test_full_and_quality_failures_preserved_and_robustness_still_runs(self):
        self.failed = {"full", "quality"}
        self.assertEqual(self.run_workflow(), 1)
        self.assertEqual([row[0] for row in self.calls],
                         ["probe", "dev", "smoke", "full", "quality", "robustness"])
        state = self.state()
        self.assertEqual(state["status"], "COMPLETE_WITH_EXECUTION_FAILURES")
        self.assertEqual(state["quality_status"], "UNSCORED")
        self.assertEqual([row["name"] for row in state["stages"] if row["status"] == "FAIL"],
                         ["full", "quality"])

    def test_unavailable_cancel_kept_without_blocking_normal_collection(self):
        self.assertEqual(self.run_workflow("mini"), 0)
        state = self.state("mini")
        self.assertEqual(state["status"], "COMPLETE_WITH_UNAVAILABLE_CHECKS")
        self.assertEqual(state["stages"][0]["exit_code"], 2)
        self.assertEqual(state["stages"][0]["checks"]["disconnect_abort_and_drain"], "UNAVAILABLE")
        self.assertFalse(state["formal_performance_eligible"])
        self.assertFalse(state["build_interference"])
        for name, command, env in self.calls:
            self.assertEqual(env["OMP_NUM_THREADS"], "8")
            self.assertEqual(env["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"], "True")
            if name in {"dev", "smoke", "full", "robustness"}:
                self.assertIn("--layout-model-dir", command)
                self.assertEqual(command[command.index("--page-admission") + 1], "1")
                self.assertEqual(command[command.index("--region-limit") + 1], "4")
                self.assertIn("build_interference=false", command)
            elif name == "quality":
                self.assertNotIn("--build-interference", command)

    def test_explicit_build_interference_enters_state_and_cli_metadata(self):
        self.assertEqual(self.run_workflow(build_interference=True), 0)
        self.assertTrue(self.state()["build_interference"])
        self.assertFalse(self.state()["formal_performance_eligible"])
        for name, command, _ in self.calls:
            if name in {"dev", "smoke", "full", "robustness"}:
                self.assertIn("build_interference=true", command)
            elif name == "quality":
                self.assertIn("--build-interference", command)

    def test_cli_build_interference_defaults_false_and_accepts_flag(self):
        with patch.object(validation, "run", return_value=0) as run:
            self.assertEqual(validation.main(["--adapter", "mini", "--tag", "clean"]), 0)
            self.assertFalse(run.call_args.args[3])
            self.assertEqual(validation.main(["--adapter", "ovis", "--tag", "building",
                                              "--build-interference"]), 0)
            self.assertTrue(run.call_args.args[3])

    def test_runtime_argv_mismatch_rejected(self):
        with patch.object(validation, "read_json", return_value=self.policy), \
                patch.object(Path, "read_bytes", return_value=b"other-process\0"):
            with self.assertRaisesRegex(ValueError, "LIVE_PID1_ARGV"):
                validation.runtime_policy(self.root, "ovis")

    def test_tag_cannot_escape_task_directory(self):
        with self.assertRaisesRegex(ValueError, "safe ASCII"):
            validation.run("ovis", "../old", self.root)


if __name__ == "__main__":
    unittest.main()
