#!/usr/bin/env python3
"""Read-only offline delivery validation. Does not fetch remote links or run tools.

Checks file existence/local Markdown links, strict JSON, source-lock constants,
the reduced synthetic fixture, and MANIFEST integrity if present. Does not prove
technical truth, external URL validity, product implementation or GPU qualification.
"""
import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
from urllib.parse import unquote, urlsplit

from contract_examples import guard_fixed_text_fixture

PARENT_SHA = "0a08667d8fc03d91e1b961a9e705f4649b357e65f25e285db847c390c2c99934"
STRATA_SHA = "504b143342a9fe1aa8320a7b31e11f5c0ac265c3"


def _nonfinite(value):
    raise ValueError("nonfinite JSON constant: " + value)


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("nonfinite/overflow JSON number: " + text)
    return value


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key: " + key)
        obj[key] = value
    return obj


def read_json_strict(path):
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_nonfinite, parse_float=_finite_float,
                      object_pairs_hook=_unique_object)


def package_files(root):
    return sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def check_local_links(root, path):
    text = path.read_text(encoding="utf-8")
    targets = re.findall(r"\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)", text)
    targets += re.findall(r"^\[[^\]]+\]:\s*(\S+)", text, re.MULTILINE)
    errors = []
    for target in targets:
        parsed = urlsplit(target.strip("<>"))
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        dest = (path.parent / unquote(parsed.path)).resolve()
        try:
            dest.relative_to(root.resolve())
        except ValueError:
            errors.append(f"{path.name}: local link escapes bundle: {target}")
            continue
        if not dest.exists():
            errors.append(f"{path.name}: missing local link: {target}")
    return errors


def check_manifest(root):
    manifest = root / "MANIFEST.sha256"
    if not manifest.exists():
        return ["MANIFEST.sha256 missing"]
    errors, listed = [], set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append("malformed manifest line")
            continue
        digest, name = match.groups()
        path = root / name
        if name in listed or name == "MANIFEST.sha256":
            errors.append("duplicate/self manifest member: " + name)
            continue
        listed.add(name)
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            errors.append("manifest path escape: " + name)
            continue
        if not path.is_file() or path.is_symlink():
            errors.append("manifest missing/unsafe member: " + name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            errors.append("manifest hash mismatch: " + name)
    actual = {str(p.relative_to(root)) for p in package_files(root) if p.name != "MANIFEST.sha256"}
    for name in sorted(actual - listed):
        errors.append("unlisted manifest file: " + name)
    return errors


def validate(root, require_manifest=False):
    errors = []
    required = ["README.md", "AGENTS.md", "START_HERE_AI.md", "VALIDATION.md", "REVIEW.md",
                "plans/IMPLEMENTATION_PLAN.md", "sources/LOCK.json", "sources/SOURCES.md",
                "examples/README.md", "examples/numerical_complete_fixture.json",
                "examples/kernel_evidence_example.json", "tools/contract_examples.py",
                "tools/probe_upstream_force_check.py", "tools/validate_addendum.py", "tests/test_addendum.py"]
    required += ["docs/" + name for name in ["01_SAMIR_VLLM_REUSE.md", "02_NABO_TO_4090.md",
                "03_BASE_INTEGRATION.md", "04_EVIDENCE_CONTRACT.md", "05_CODEGEN_AND_COUNTERS.md",
                "06_NUMERICAL_GUARD.md", "07_MEMORY_AND_ORACLE.md", "08_TEST_AND_ACCEPTANCE.md", "09_RUNBOOK.md"]]
    for name in required:
        if not (root / name).is_file():
            errors.append("required file missing: " + name)
    files = package_files(root)
    for path in files:
        if path.is_symlink():
            errors.append("symlink not allowed: " + str(path.relative_to(root)))
            continue
        try:
            if path.suffix == ".md":
                if not path.read_text(encoding="utf-8").strip():
                    errors.append("empty Markdown: " + path.name)
                errors.extend(check_local_links(root, path))
            elif path.suffix == ".json":
                read_json_strict(path)
        except (OSError, UnicodeError, ValueError) as exc:
            errors.append(f"{path.name}: {exc}")
    try:
        lock = read_json_strict(root / "sources/LOCK.json")
        if lock["parent"]["sha256"] != PARENT_SHA:
            errors.append("parent source lock mismatch")
        strata = next(r for r in lock["repositories"] if r["name"] == "Niko1221/Strata")
        if strata["commit"] != STRATA_SHA or strata["deployed_state"] != "UNKNOWN":
            errors.append("Strata source/deployed distinction changed")
        budget = lock.get("live_budget")
        budget_keys = {"engine_starts", "generation_requests", "gpu_runs", "production_changes"}
        if (not isinstance(budget, dict) or set(budget) != budget_keys
                or any(type(v) is not int or v != 0 for v in budget.values())):
            errors.append("invalid live budget: requires every declared integer-zero field")
        result = guard_fixed_text_fixture(read_json_strict(root / "examples/numerical_complete_fixture.json"))
        if result["status"] != "INPUT_ADMISSIBLE_FIXTURE_ONLY":
            errors.append("synthetic positive fixture invalid: " + repr(result["reasons"]))
        kernel = read_json_strict(root / "examples/kernel_evidence_example.json")
        if kernel.get("provenance") != "SYNTHETIC" or kernel.get("production_eligible") is not False:
            errors.append("kernel example must remain synthetic and ineligible")
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        errors.append("contract/source parse failure: " + str(exc))
    if require_manifest or (root / "MANIFEST.sha256").exists():
        errors.extend(check_manifest(root))
    return {"status": "OFFLINE_DELIVERY_VALID" if not errors else "OFFLINE_DELIVERY_INVALID",
            "files": len(files), "markdown_files": sum(p.suffix == ".md" for p in files),
            "errors": errors, "engine_starts": 0, "gpu_runs": 0,
            "limits": "Local structure/hash and toy fixture checks only; not GPU/product/source-truth validation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument("--require-manifest", action="store_true")
    args = parser.parse_args()
    result = validate(args.root.resolve(), args.require_manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if not result["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
