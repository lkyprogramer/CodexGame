import gzip
import subprocess
import unittest
from pathlib import Path


class TriageScriptGzTests(unittest.TestCase):
    def test_triage_groups_signatures_with_gz(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        archive = repo_root / "logs" / "archive.log.gz"
        archive.write_bytes(gzip.compress((repo_root / "logs" / "archive.log").read_bytes()))
        script = repo_root / "scripts" / "triage.sh"
        result = subprocess.run(
            ["bash", str(script), str(repo_root / "logs" / "app.log"), str(archive)],
            check=True,
            capture_output=True,
            text=True,
        )
        output = result.stdout.strip().splitlines()
        self.assertTrue(any("OrderService failed to reserve inventory" in line and line.startswith("2 ") for line in output))
        self.assertTrue(any("PaymentGateway timeout" in line and line.startswith("2 ") for line in output))
        self.assertTrue(any("ProfileService duplicate email" in line and line.startswith("1 ") for line in output))
        self.assertFalse(any("healthcheck" in line.lower() for line in output))


if __name__ == "__main__":
    unittest.main()
