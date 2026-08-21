#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]


def run_step(name: str, command: Sequence[str], *, cwd: Path = ROOT) -> None:
    print(f"\n=== {name} ===", flush=True)
    print("$ " + " ".join(command), flush=True)
    result = subprocess.run(list(command), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n", flush=True)
    if result.returncode != 0:
        raise RuntimeError(f"{name} failed with exit code {result.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all release checks without modifying frozen benchmark content")
    parser.add_argument("--quick", action="store_true", help="Skip 96 reference/baseline verifier runs")
    args = parser.parse_args()

    print(f"QCB release root: {ROOT}")
    print(f"Python: {sys.version.split()[0]}")
    if sys.version_info < (3, 11):
        print("Python 3.11+ is required", file=sys.stderr)
        return 1
    for executable in ("git", "java", "javac"):
        if not shutil.which(executable):
            print(f"Missing required executable: {executable}", file=sys.stderr)
            return 1

    try:
        run_step("Python compile", [sys.executable, "-m", "compileall", "-q", "qcb", "scripts", "tests", "examples"])
        run_step("Unit tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
        run_step("Catalog and leakage validation", [sys.executable, "scripts/validate_catalog.py"])
        run_step("CLI import", [sys.executable, "-m", "qcb.cli", "--help"])

        if not args.quick:
            for prefix, workers in (("AT", 6), ("BF", 6), ("CR", 4), ("LC", 4), ("RE", 6), ("SF", 6)):
                run_step(
                    f"Reference and baseline verification: {prefix}",
                    [
                        sys.executable,
                        "scripts/verify_references.py",
                        "--prefix",
                        prefix,
                        "--workers",
                        str(workers),
                        "--baseline-timeout",
                        "8",
                    ],
                )

        with tempfile.TemporaryDirectory(prefix="qcb-release-report-") as temp:
            temp_path = Path(temp)
            run_step(
                "Synthetic original result audit",
                [
                    sys.executable,
                    "scripts/audit_results.py",
                    "--results",
                    "examples/synthetic-original-normalized-smoke.jsonl",
                    "--json",
                    str(temp_path / "audit-original.json"),
                ],
            )
            run_step(
                "Synthetic candidate result audit",
                [
                    sys.executable,
                    "scripts/audit_results.py",
                    "--results",
                    "examples/synthetic-candidate-normalized-smoke.jsonl",
                    "--json",
                    str(temp_path / "audit-candidate.json"),
                ],
            )
            run_step(
                "Synthetic model report",
                [
                    sys.executable,
                    "scripts/generate_report.py",
                    "--results",
                    "examples/synthetic-original-normalized-smoke.jsonl",
                    "--output",
                    str(temp_path / "model.md"),
                    "--json",
                    str(temp_path / "model.json"),
                ],
            )
            run_step(
                "Synthetic paired comparison",
                [
                    sys.executable,
                    "scripts/compare_models.py",
                    "--model-a",
                    "examples/synthetic-original-normalized-smoke.jsonl",
                    "--model-b",
                    "examples/synthetic-candidate-normalized-smoke.jsonl",
                    "--output",
                    str(temp_path / "comparison.md"),
                    "--json",
                    str(temp_path / "comparison.json"),
                ],
            )
            run_step(
                "Synthetic leaderboard",
                [
                    sys.executable,
                    "scripts/generate_leaderboard.py",
                    "--input",
                    "examples/synthetic-original-normalized-smoke.jsonl",
                    "--input",
                    "examples/synthetic-candidate-normalized-smoke.jsonl",
                    "--output",
                    str(temp_path / "leaderboard.md"),
                    "--json",
                    str(temp_path / "leaderboard.json"),
                ],
            )
            required = ["audit-original.json", "audit-candidate.json", "model.md", "model.json", "comparison.md", "comparison.json", "leaderboard.md", "leaderboard.json"]
            missing = [name for name in required if not (temp_path / name).is_file() or (temp_path / name).stat().st_size == 0]
            if missing:
                raise RuntimeError(f"Report pipeline did not create: {missing}")

        if (ROOT / "MANIFEST.sha256").is_file():
            run_step("Manifest", [sys.executable, "scripts/check_manifest.py"])

    except RuntimeError as exc:
        print(f"\nRELEASE VERIFICATION FAILED: {exc}", file=sys.stderr)
        return 1

    print("\nRELEASE VERIFICATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
