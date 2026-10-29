"""Collect one candidate's standard diagnostics; never starts/stops its service.

Exit zero means collection completed without a failed execution check. Neither
that exit code nor a parsed page is a quality acceptance decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def runtime_policy(root: Path, adapter: str) -> dict:
    record = read_json(root / "evidence" / f"{adapter}-effective-runtime.json")
    actual = Path("/proc/1/cmdline").read_bytes().decode().strip("\0").split("\0")
    if actual != record["argv"]:
        raise ValueError("LIVE_PID1_ARGV_DIFFERS_FROM_CAPTURED_RUNTIME")
    expected = {"dtype": "bfloat16", "max_model_len": 16384,
                "gpu_memory_utilization": .65, "max_num_seqs": 4,
                "max_num_batched_tokens": 8192, "cpu_cores": 8, "ram_gib": 32}
    if record["policy"] != expected:
        raise ValueError("CAPTURED_RUNTIME_DIFFERS_FROM_COMMON_POLICY")
    return record


def execute(command: list[str], log: Path, env: dict) -> tuple[int | None, str | None]:
    try:
        with log.open("x") as stream:
            return subprocess.call(command, stdout=stream, stderr=subprocess.STDOUT, env=env), None
    except OSError as error:
        return None, f"{type(error).__name__}: {error}"


KNOWN_TEXT_DEV_PAGES = frozenset({
    "PAPER-004-p001", "PAPER-009-p001", "PAPER-027-p001", "LOCAL-GOVPDF-01-p001",
})


def dev_complete(summary: dict, output: Path) -> bool:
    complete = (summary.get("run_status") == "COMPLETED"
            and all(summary.get(key) == 4 for key in
                    ("planned_pages", "submitted_pages", "terminal_pages", "pass_pages"))
            and bool(summary.get("documents"))
            and summary.get("pass_documents") == len(summary["documents"])
            and summary.get("all_document_artifacts_pass") is True)
    if not complete:
        return False
    # These four frozen development pages contain text. This startup gate does
    # not change blank-page semantics in either adapter or the general runner.
    records = summary.get("results")
    if (not isinstance(records, list) or len(records) != 4
            or any(not isinstance(record, dict) for record in records)
            or {record.get("page_id") for record in records} != KNOWN_TEXT_DEV_PAGES):
        return False
    for record in records:
        calls = record.get("model_call_count")
        if record.get("status") != "PASS" or type(calls) is not int or calls <= 0:
            return False
        result = read_json(output / "pages" / record["page_id"] / "result.json")
        blocks = result.get("ordered_blocks")
        text = result.get("text")
        if (result.get("page_id") != record["page_id"] or result.get("status") != "PASS"
                or result.get("layout_empty") is True
                or not isinstance(blocks, list) or not blocks
                or not isinstance(text, str) or not text.strip()):
            return False
    return True


def run(adapter: str, tag: str, root: Path, build_interference: bool = False) -> int:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", tag):
        raise ValueError("tag must be safe ASCII and at most 64 characters")
    runtime = runtime_policy(root, adapter)
    directory = root / "evidence" / f"{adapter}-standard-{tag}"
    directory.mkdir(exist_ok=False)
    write_json(directory / "runtime-snapshot.json", runtime)
    sources = [Path(__file__), root / "probe_runtime.py", root / "deploy/run_quality_suite.py",
               *(root / "ocrbench").glob("*.py")]
    write_json(directory / "source-hashes.json", {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources})
    env = dict(os.environ, PYTHONPATH=str(root), PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK="True",
               OMP_NUM_THREADS="8", OPENBLAS_NUM_THREADS="8", MKL_NUM_THREADS="8")
    model = "minicpm-ocr" if adapter == "mini" else "ovisocr3"
    model_dir = "/models/MiniCPM-OCR-1.0" if adapter == "mini" else "/models/OvisOCR3"
    url = f"http://127.0.0.1:{18499 if adapter == 'mini' else 18500}/v1"
    base = [sys.executable, "-m", "ocrbench.cli", "--adapter", adapter,
            "--base-url", url, "--model", model, "--model-dir", model_dir,
            "--page-admission", "1", "--region-limit", "4", "--timing-scope", "D0",
            "--option", "runtime_policy=" + json.dumps(runtime["policy"]),
            "--option", 'profile="C0-S0-full-diagnostic"',
            "--option", "build_interference=" + json.dumps(build_interference)]
    if adapter == "mini":
        base += ["--layout-model-dir", "/models/PP-DocLayoutV3_infer"]
    state = {"adapter": adapter, "tag": tag, "status": "RUNNING", "quality_status": "UNSCORED",
             "formal_performance_eligible": False, "build_interference": build_interference,
             "wall_start": time.time(), "stages": []}
    state_path = directory / "state.json"
    write_json(state_path, state)

    def stage(name: str, command: list[str]) -> dict:
        record = {"name": name, "command": command, "status": "RUNNING", "wall_start": time.time()}
        state["stages"].append(record)
        write_json(state_path, state)
        code, error = execute(command, directory / f"{name}.log", env)
        record.update(exit_code=code, status="PASS" if code == 0 else "FAIL", wall_end=time.time())
        if error:
            record["error"] = error
        write_json(state_path, state)
        return record

    def stop(reason: str) -> int:
        state.update(status="STOPPED_PREREQUISITE_FAILED", stop_reason=reason, wall_end=time.time())
        write_json(state_path, state)
        return 1

    probe_out = root / "results" / f"{adapter}-probe-{tag}"
    probe = stage("probe", [sys.executable, str(root / "probe_runtime.py"), "--base-url", url,
                            "--model", model, "--model-dir", model_dir,
                            "--image", str(root / "results/ovis-dev-r1/pages/LOCAL-GOVPDF-01-p001/input.png"),
                            "--out", str(probe_out)])
    try:
        report = read_json(probe_out / "probe-result.json")
        probe["checks"] = {name: check["status"] for name, check in report["checks"].items()}
        probe["status"] = report["status"]
        write_json(state_path, state)
    except (OSError, ValueError, KeyError) as error:
        probe["error"] = f"INVALID_PROBE_EVIDENCE: {error}"
        return stop("probe did not leave valid terminal evidence")
    if probe["checks"].get("image_tokenize_completion_usage") != "PASS":
        return stop("normal multimodal image/tokenize/completion/usage prerequisite failed")

    jobs = [("dev", root / "corpus/development-manifest.json"),
            ("smoke", root / "corpus/smoke-manifest.json"),
            ("full", root / "corpus/manifest.json")]
    for name, manifest in jobs:
        output = root / "results" / f"{adapter}-{name}-{tag}"
        record = stage(name, base + ["--manifest", str(manifest), "--out", str(output)])
        if name == "dev":
            try:
                accepted = record["exit_code"] == 0 and dev_complete(read_json(output / "summary.json"), output)
            except (OSError, ValueError):
                accepted = False
            if not accepted:
                record["status"] = "FAIL"
                return stop("development pages or required document artifacts failed")

    quality_command = [sys.executable, str(root / "deploy/run_quality_suite.py"),
                       "--adapter", adapter, "--tag", tag, "--root", str(root)]
    if build_interference:
        quality_command.append("--build-interference")
    stage("quality", quality_command)
    stage("robustness", base + ["--manifest", str(root / "corpus-extra/robustness48/manifest.json"),
                                 "--out", str(root / "results" / f"{adapter}-robustness-{tag}")])
    failed = any(record["status"] == "FAIL" for record in state["stages"])
    unavailable = any(record["status"] == "UNAVAILABLE" for record in state["stages"])
    state.update(status="COMPLETE_WITH_EXECUTION_FAILURES" if failed else
                 "COMPLETE_WITH_UNAVAILABLE_CHECKS" if unavailable else "EXECUTION_COMPLETE",
                 wall_end=time.time())
    write_json(state_path, state)
    print(json.dumps({"status": state["status"], "quality_status": "UNSCORED", "evidence": str(directory)}))
    return 1 if failed else 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter", choices=["mini", "ovis"], required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--root", type=Path, default=Path("/work"))
    parser.add_argument("--build-interference", action="store_true",
                        help="Record actual concurrent compilation; default is no build interference")
    args = parser.parse_args(argv)
    return run(args.adapter, args.tag, args.root, args.build_interference)


if __name__ == "__main__":
    raise SystemExit(main())
