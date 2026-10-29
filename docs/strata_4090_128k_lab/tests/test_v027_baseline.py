"""Safety of the staged v0.2.7 experiment, without starting a model."""
import copy
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "tools/v027/run_baseline.py"
spec = importlib.util.spec_from_file_location("v027_baseline_tested", PATH)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
PORT = PATH.with_name("port_reply_pt.py")
spec = importlib.util.spec_from_file_location("v027_port_tested", PORT)
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


class V027GateTests(unittest.TestCase):
    def test_kvres_inherits_args_and_rejects_a_conflicting_override(self):
        cfg = {"args": ["--kv-resident", "20480"], "user_args": ["--max-context", "131072"]}
        baseline.assert_kvres(cfg)
        cfg["user_args"] += ["--kv-resident", "0"]
        with self.assertRaisesRegex(ValueError, "KVRES_OVERRIDE_DRIFT"):
            baseline.assert_kvres(cfg)

    def test_quality_lifecycle_and_fresh_task_all_gate_dequant(self):
        row = {"score": {"pass": True}, "restore": {"pass": True}}
        self.assertTrue(baseline.correctness_pass([row], None, True))
        self.assertFalse(baseline.correctness_pass([], None, True))
        self.assertFalse(baseline.correctness_pass([row], None, False))
        self.assertFalse(baseline.correctness_pass([row], "FINAL_AUDIT", True))
        for field in ("score", "restore"):
            failed = copy.deepcopy(row)
            failed[field]["pass"] = False
            self.assertFalse(baseline.correctness_pass([failed], None, True))

    def test_patch_anchor_keeps_changed_upstream_neighbor(self):
        lines = ["@@ -1,3 +1,4 @@\n", " BEFORE\n", " CONSTANT\n", "+LAB_ADDITION\n", " OLD_NEIGHBOR\n"]
        self.assertEqual(port.insert_hunks("BEFORE\nCONSTANT\nNEW_NEIGHBOR\n", lines),
                         "BEFORE\nCONSTANT\nLAB_ADDITION\nNEW_NEIGHBOR\n")

    def test_ambiguous_patch_anchor_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No unique preceding anchor"):
            port.insert_hunks("same\nsame\n", ["@@\n", " same\n", "+extra\n"])

    def test_approximate_paths_and_dequant_stay_disabled(self):
        for name in ("STRATA_KVA", "STRATA_MMVQ_IL_89", "STRATA_PROMPT_ATTN_IMMA", "STRATA_DEQUANT_SIDE"):
            self.assertEqual(baseline.CONSERVATIVE[name], "0")


if __name__ == "__main__":
    unittest.main()
