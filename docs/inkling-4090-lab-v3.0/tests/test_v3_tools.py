import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "tools/driver_guard.sh"
WINDOW = ROOT / "tools/lab_window.sh"
FETCH = ROOT / "tools/ms_fetch.py"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


class DriverGuard(unittest.TestCase):
    def test_compare_identical_and_changed(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a"), Path(d, "b")
            a.write_text("## nvidia_smi\n610.57.04, RTX 4090\n")
            b.write_text(a.read_text())
            self.assertEqual(run(["bash", str(GUARD), "compare", str(a), str(b)]).returncode, 0)
            b.write_text("## nvidia_smi\n615.01, RTX 4090\n")
            r = run(["bash", str(GUARD), "compare", str(a), str(b)])
            self.assertEqual(r.returncode, 3)
            self.assertIn("DRIVER FINGERPRINT CHANGED", r.stderr)

    def test_scan_flags_driver_lines_but_allows_stub_package(self):
        with tempfile.TemporaryDirectory() as d:
            log = Path(d, "log")
            log.write_text("cuda-nvcc 12.8.93 nvidia\ncuda-driver-dev 12.8.90 nvidia\n")
            self.assertEqual(run(["bash", str(GUARD), "scan", str(log)]).returncode, 0)
            for line in ("Installing NVIDIA driver 570.124.06", "Building kernel module for 6.1", "dkms install", "cuda-drivers 570"):
                log.write_text("cuda-nvcc 12.8.93\n" + line + "\n")
                self.assertEqual(run(["bash", str(GUARD), "scan", str(log)]).returncode, 3, line)

    def test_snapshot_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d, "base")
            base.write_text("x")
            r = run(["bash", str(GUARD), "snapshot", str(base)])
            self.assertEqual(r.returncode, 2)
            self.assertEqual(base.read_text(), "x")


class LabWindowArguments(unittest.TestCase):
    """Only argument errors are tested: these exit before any systemctl call."""

    def run_window(self, *args, lab):
        env = dict(os.environ, LAB=lab, PATH="/usr/bin:/bin")
        return run(["bash", str(WINDOW), *args], env=env)

    def test_rejects_bad_minutes_and_missing_command(self):
        with tempfile.TemporaryDirectory() as d:
            for args in ((), ("0", "true"), ("91", "true"), ("x", "true"), ("10",)):
                self.assertEqual(self.run_window(*args, lab=d).returncode, 2, args)

    def test_requires_driver_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            r = self.run_window("5", "true", lab=d)
            self.assertEqual(r.returncode, 2)
            self.assertIn("missing driver baseline", r.stderr)


class MsFetch(unittest.TestCase):
    def listing(self, d, files):
        path = Path(d, "listing.json")
        path.write_text(json.dumps({"Code": 200, "Data": {"Files": [
            {"Type": "blob", "Path": p, "Size": len(c), "Sha256": hashlib.sha256(c).hexdigest()} for p, c in files.items()
        ] + [{"Type": "tree", "Path": "Mainline_Support", "Size": 0}]}}))
        return path

    def test_plan_filters_strips_suffix_and_verify_writes_lock(self):
        files = {"Mainline_Support/m.gguf_file": b"model", "README.md": b"r", "big.bin": b"skip"}
        with tempfile.TemporaryDirectory() as d:
            listing, out = self.listing(d, files), Path(d, "out")
            sha = hashlib.sha256(b"model").hexdigest()
            r = run([sys.executable, str(FETCH), "plan", "--model", "o/m", "--out", str(out), "--files-json", str(listing),
                     "--include", "Mainline_Support/*", "--include", "README.md", "--strip-suffix", "_file",
                     "--expect", "Mainline_Support/m.gguf_file=" + sha])
            self.assertEqual(r.returncode, 0, r.stderr)
            aria = (out / ".ms_fetch/aria2.txt").read_text()
            self.assertIn("  out=m.gguf\n", aria)
            self.assertIn("checksum=sha-256=" + sha, aria)
            self.assertNotIn("big.bin", aria)
            (out / "Mainline_Support").mkdir(parents=True)
            (out / "Mainline_Support/m.gguf").write_bytes(b"model")
            (out / "README.md").write_bytes(b"r")
            lock = Path(d, "lock.json")
            r = run([sys.executable, str(FETCH), "verify", "--out", str(out), "--lock", str(lock)])
            self.assertEqual(r.returncode, 0, r.stderr)
            records = json.loads(lock.read_text())["files"]
            self.assertEqual(len(records), 2)
            self.assertTrue(all(rec["source"] == "modelscope" for rec in records))

    def test_plan_rejects_sha_mismatch_and_filtered_expectation(self):
        with tempfile.TemporaryDirectory() as d:
            listing, out = self.listing(d, {"a.bin": b"a", "b.bin": b"b"}), Path(d, "out")
            wrong = "0" * 64
            r = run([sys.executable, str(FETCH), "plan", "--model", "o/m", "--out", str(out), "--files-json", str(listing),
                     "--expect", "a.bin=" + wrong])
            self.assertEqual(r.returncode, 1)
            self.assertIn("SHA256 mismatch", r.stderr)
            self.assertFalse((out / ".ms_fetch").exists())
            sha_b = hashlib.sha256(b"b").hexdigest()
            r = run([sys.executable, str(FETCH), "plan", "--model", "o/m", "--out", str(out), "--files-json", str(listing),
                     "--exclude", "b.bin", "--expect", "b.bin=" + sha_b])
            self.assertEqual(r.returncode, 1)
            self.assertIn("filtered out", r.stderr)

    def test_verify_rejects_corrupt_file_without_touching_lock(self):
        with tempfile.TemporaryDirectory() as d:
            listing, out = self.listing(d, {"a.bin": b"good"}), Path(d, "out")
            self.assertEqual(run([sys.executable, str(FETCH), "plan", "--model", "o/m", "--out", str(out),
                                  "--files-json", str(listing)]).returncode, 0)
            (out / "a.bin").write_bytes(b"bad!")
            lock = Path(d, "lock.json")
            r = run([sys.executable, str(FETCH), "verify", "--out", str(out), "--lock", str(lock)])
            self.assertEqual(r.returncode, 1)
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
