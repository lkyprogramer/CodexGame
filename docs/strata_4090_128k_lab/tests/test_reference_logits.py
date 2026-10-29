import hashlib
import importlib.util
import math
from pathlib import Path
import struct
import tempfile
import unittest

PATH = Path(__file__).resolve().parents[1] / "tools/v027/analyze_reference_logits.py"
spec = importlib.util.spec_from_file_location("reference_logits_tested", PATH)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class ReferenceLogitsTests(unittest.TestCase):
    def test_shape_truncation_and_nonfinite_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logits.f32"
            path.write_bytes(struct.pack("<4f", 1, 2, 3, 4))
            self.assertEqual(list(analysis.load_rows(path, 2, 2)[1]), [3, 4])
            with self.assertRaisesRegex(ValueError, "SHAPE"):
                analysis.load_rows(path, 3, 2)
            path.write_bytes(struct.pack("<4f", 1, math.nan, 3, 4))
            with self.assertRaisesRegex(ValueError, "NONFINITE"):
                analysis.load_rows(path, 2, 2)

    def test_rank_ties_and_stable_probabilities(self):
        summary = analysis.row_summary([1000, 1001, 1001, 999], [0, 1, 3])
        self.assertEqual(summary["top1"], 1)
        self.assertEqual([x["id"] for x in summary["top"]], [1, 2, 0, 3])
        self.assertEqual(summary["tracked"]["0"]["rank"], 3)
        self.assertEqual(summary["tracked"]["1"]["rank"], 1)
        self.assertAlmostEqual(sum(x["probability"] for x in summary["top"]), 1)

    def test_constant_offset_is_removed_without_hiding_rank_reversal(self):
        shifted = analysis.row_metrics([1000, 1001], [1010, 1011])
        self.assertEqual(shifted["centered_rmse"], 0)
        self.assertAlmostEqual(shifted["kl_reference_to_native"], 0)
        reverse = analysis.row_metrics([0, 2], [2, 0])
        self.assertGreater(reverse["centered_rmse"], 0)
        self.assertGreater(reverse["kl_reference_to_native"], 0)

    def test_consumed_ids_need_all_frozen_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tokens.ids"
            path.write_text("21,22,12\n")
            ids = [21, 22, 12]
            record = {"path": str(path), "count": 3, "fnv64": analysis.fnv_ids(ids),
                      "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "int32_sha256": hashlib.sha256(analysis.ids_bytes(ids)).hexdigest()}
            self.assertEqual(analysis.verify_ids(record), ids)
            record["int32_sha256"] = "wrong"
            with self.assertRaisesRegex(ValueError, "FROZEN_ID"):
                analysis.verify_ids(record)

    def test_native_input_hash_and_emitted_argmax_are_independent_checks(self):
        records = [{"case": "probe", "step": 0, "input_count": 1,
                    "input_fnv": analysis.fnv_ids([10]), "emitted": 1},
                   {"case": "probe", "step": 1, "input_count": 2,
                    "input_fnv": analysis.fnv_ids([10, 1]), "emitted": analysis.EOS}]
        final = [0] * (analysis.EOS + 1)
        final[analysis.EOS] = 2
        analysis.validate_native(records, "probe", [10], [1], [[0, 2], final])
        control = dict(records[1], emitted=analysis.DASH)
        last = [0] * (analysis.DASH + 1)
        last[analysis.DASH] = 2
        analysis.validate_native([records[0], control], "probe", [10], [1], [[0, 2], last], analysis.DASH)
        records[0]["emitted"] = 0
        with self.assertRaisesRegex(ValueError, "ARGMAX"):
            analysis.validate_native(records, "probe", [10], [1], [[0, 2], final])
        records[0]["emitted"] = 1
        records[0]["input_fnv"] = "wrong"
        with self.assertRaisesRegex(ValueError, "INPUT_ID"):
            analysis.validate_native(records, "probe", [10], [1], [[0, 2], final])


if __name__ == "__main__":
    unittest.main()
