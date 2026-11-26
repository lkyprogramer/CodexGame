"""Behavior tests: case-level inference, invalid inputs, and read-only probe failures."""
import csv
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
FIELDS = ["pair_id", "case_id", "stratum", "baseline_ms", "candidate_ms"]


class ToolTests(unittest.TestCase):
    def module(self, name):
        self.assertTrue((ROOT / "tools" / (name + ".py")).is_file(), name + " is not implemented")
        return importlib.import_module(name)

    def stats(self, rows, header=FIELDS):
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)
        stream.seek(0)
        return self.module("paired_stats").analyze(stream, 300, 20261125)

    def rows(self, n=30):
        return [(str(i), "case" + str(i), "cold", 100, 50) for i in range(n)]

    def test_constant_twofold_speedup_and_interval(self):
        result = self.stats(self.rows())
        self.assertEqual((result["case_count"], result["pair_count"]), (30, 30))
        self.assertAlmostEqual(result["gmean_speedup"], 2)
        self.assertAlmostEqual(result["latency_reduction"], 0.5)
        self.assertEqual(result["speedup_ci95"], [2.0, 2.0])
        self.assertEqual(result["evidence_kind"], "derived_statistics")
        self.assertNotIn("PASS", json.dumps(result))

    def test_repetitions_do_not_reweight_cases_or_bootstrap(self):
        rows = [(str(i), "case" + str(i), "cold", 100, 100) for i in range(30)]
        rows[0] = ("0", "case0", "cold", 100, 25)
        once = self.stats(rows)
        repeated = self.stats(rows + [("rep" + str(i), "case0", "cold", 100, 25) for i in range(7)])
        self.assertAlmostEqual(repeated["gmean_speedup"], 1.0472941228206267)
        self.assertEqual(once["speedup_ci95"], repeated["speedup_ci95"])
        self.assertEqual(repeated["pair_count"], 37)
        self.assertEqual(self.stats(list(reversed(rows)))["speedup_ci95"], once["speedup_ci95"])

    def test_under_thirty_cases_has_no_confidence_interval(self):
        rows = self.rows(29) + [("extra", "case0", "cold", 100, 50)]
        result = self.stats(rows)
        self.assertEqual(result["evidence_status"], "INSUFFICIENT_EVIDENCE")
        self.assertIsNone(result["speedup_ci95"])
        self.assertIsNone(result["latency_reduction_ci95"])

    def test_invalid_schema_duplicate_pair_strata_and_empty_ids(self):
        for rows, header in [([], FIELDS), (self.rows(), FIELDS[:-1]),
                             (self.rows() + [("0", "other", "cold", 1, 1)], FIELDS),
                             (self.rows() + [("x", "other", "warm", 1, 1)], FIELDS),
                             ([("", "a", "cold", 1, 1)], FIELDS),
                             ([("a", "", "cold", 1, 1)], FIELDS),
                             ([("a", "b", "", 1, 1)], FIELDS)]:
            with self.subTest(rows=rows[:1], header=header), self.assertRaises(ValueError):
                self.stats(rows, header)

    def test_invalid_latencies_and_bootstrap_count(self):
        for baseline, candidate in [(0, 1), (-1, 1), (1, 0), ("nan", 1), (1, "inf"), (1, "bad")]:
            with self.subTest(baseline=baseline, candidate=candidate), self.assertRaises(ValueError):
                self.stats([("a", "b", "cold", baseline, candidate)])
        with self.assertRaises(ValueError):
            self.module("paired_stats").analyze(io.StringIO(""), 0, 1)
        self.assertAlmostEqual(self.stats([("a", "b", "cold", 1e-300, 5e-301)])["gmean_speedup"], 2)

    def test_stats_cli_writes_strict_json_and_rejects_invalid_without_overwrite(self):
        self.module("paired_stats")
        with tempfile.TemporaryDirectory() as directory:
            src, out = Path(directory) / "input.csv", Path(directory) / "result.json"
            with src.open("w", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                writer.writerows(self.rows())
            command = [sys.executable, str(ROOT / "tools/paired_stats.py"), "--input", str(src),
                       "--bootstrap", "300", "--seed", "20261125", "--output", str(out)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            original = out.read_text()
            self.assertEqual(json.loads(original)["case_count"], 30)
            src.write_text("wrong,header\n")
            self.assertNotEqual(subprocess.run(command, capture_output=True, timeout=10).returncode, 0)
            self.assertEqual(out.read_text(), original)

    def test_stats_cli_cannot_overwrite_input_csv(self):
        self.module("paired_stats")
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory) / "input.csv"
            original = ",".join(FIELDS) + "\na,b,cold,100,50\n"
            src.write_text(original)
            result = subprocess.run([sys.executable, str(ROOT / "tools/paired_stats.py"),
                                     "--input", str(src), "--output", str(src)], capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(src.read_text(), original)

    def test_preflight_command_failure_and_timeout_are_data(self):
        module = self.module("preflight")
        for command, timeout in [(["/__atomic_nonexistent_program__"], 1),
                                 ([sys.executable, "-c", "import time; time.sleep(2)"], 0.05),
                                 ([sys.executable, "-c", "raise SystemExit(7)"], 2)]:
            with self.subTest(command=command):
                self.assertFalse(module.run_command(command, timeout)["ok"])

    def test_preflight_gpu_match_unknown_values_and_errors(self):
        module = self.module("preflight")
        for name, expected in [("NVIDIA GeForce RTX 4090", "MATCH"),
                               ("NVIDIA A100-SXM4-80GB", "MISMATCH"),
                               ("NVIDIA GeForce RTX 4090 Laptop GPU", "MISMATCH")]:
            def runner(command, timeout=5):
                self.assertIn(command[0], {"uname", "lscpu", "nvidia-smi", "nvcc", "lsblk", "df"})
                return {"command": command, "ok": True, "exit_code": 0, "stderr": "",
                        "stdout": name + ", 24564, N/A, 590.48.01, N/A, 4, 16, 16"}
            with patch.object(module, "run_command", runner), patch.object(Path, "read_text", return_value="MemTotal: 1 kB"):
                result = module.collect()
            self.assertEqual(result["machine_match"], expected)
            self.assertIsNone(result["gpus"][0]["memory_free_mib"])
            self.assertIsNone(result["gpus"][0]["pcie_gen_current"])
            self.assertEqual(result["performance_qualification"], "NOT_RUN")
        with patch.object(module, "run_command", return_value={"ok": False, "error": "missing"}), \
             patch.object(Path, "read_text", side_effect=OSError("unavailable")):
            result = module.collect()
        self.assertEqual(result["machine_match"], "UNKNOWN")
        self.assertFalse(result["probes"]["meminfo"]["ok"])
        self.assertEqual(result["evidence_kind"], "hardware_inventory")


if __name__ == "__main__":
    unittest.main()

