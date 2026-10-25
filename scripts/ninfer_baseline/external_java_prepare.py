#!/usr/bin/env python3
"""Prepare two pinned SWE-bench Multilingual Java holdouts; never invoke a model.

Private references stay outside agent workspaces. Only copy base_dir and prompt_file
to an agent sandbox. Run grade_script on the trusted host, never inside that sandbox.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET

DATASET = "SWE-bench/SWE-bench_Multilingual"
SELECTED = {"google__gson-2158": "primitive adapter numeric conversion; small Maven module",
            "javaparser__javaparser-4561": "text-block method resolution across parser/solver modules"}
# Official Docker Hub linux/amd64 manifest digests inspected on 2026-10-21.
IMAGE_DIGESTS = {"google__gson-2158": "sha256:acbf12ce514b53b421cafe55707366d592474c23903069e49329359493dff490",
                 "javaparser__javaparser-4561": "sha256:28c3f0d67c27b07cbc710221525ea8556462da5d68b8e1d22811bcb2b21d647f"}


def fetch(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        return response.read()


def run(args, **kwargs):
    return subprocess.run(args, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, **kwargs)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def publish_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n")
    os.replace(temporary, path)


def allowed_patch(patch, prefixes=None):
    """Only textual production Java edits; forbid build/test/config and symlinks."""
    if not patch.strip():
        return True
    if "GIT binary patch" in patch or re.search(r"(?:new(?: file)?|old|deleted file) mode 120000", patch):
        return False
    result = run(["git", "apply", "--whitespace=nowarn", "--numstat", "-"], input=patch)
    if result.returncode:
        return False
    paths = []
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if len(fields) != 3 or not fields[0].isdigit() or not fields[1].isdigit():
            return False
        name = fields[2]
        if not re.fullmatch(r"[A-Za-z0-9_./$-]+/src/main/java/[A-Za-z0-9_./$-]+\.java", name):
            return False
        if ".." in name.split("/"):
            return False
        if prefixes and not any(name.startswith(prefix) for prefix in prefixes):
            return False
        paths.append(name)
    return bool(paths) or not patch.strip()


def extract_source(blob, dest):
    dest.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts[1:]
            if not parts:
                continue
            if ".." in parts or ".git" in parts or member.issym() or member.islnk():
                raise ValueError("Unsafe archive entry")
            target = dest.joinpath(*parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
                target.chmod(member.mode & 0o777)


def grade(case_file, patch_file, timeout=420):
    meta = json.loads(Path(case_file).read_text())
    patch = Path(patch_file).read_text()
    prefixes = (["gson/src/main/java/"] if meta["repo"] == "google/gson" else
                ["javaparser-core/src/main/java/", "javaparser-symbol-solver-core/src/main/java/"])
    if not allowed_patch(patch, prefixes):
        return {"status": "REJECTED_PATCH", "reason": "Only textual src/main/java/*.java edits are allowed"}
    work = Path(tempfile.mkdtemp(prefix="grade-", dir=Path(case_file).parent))
    (work / "candidate.patch").write_text(patch)
    (work / "tests.patch").write_text(meta["test_patch"])
    lines = ["#!/bin/bash", "set -euo pipefail", "cd /testbed",
             "git config --global --add safe.directory /testbed",
             f"git reset --hard {shlex.quote(meta['base_commit'])}", "git clean -fd",
             "if test -s /evidence/candidate.patch; then git apply /evidence/candidate.patch; fi",
             "git apply /evidence/tests.patch", "java -version", "mvn -version"]
    if meta["repo"] == "google/gson":
        prefix = ["mvnd", "test", "-B", "-T", "1", "-pl", "gson"]
    else:
        lines += ["./mvnw install -B -pl javaparser-symbol-solver-testing -DskipTests -am"]
        prefix = ["./mvnw", "test", "-B", "-pl", "javaparser-symbol-solver-testing"]
    lines += ["set +e"]
    expected = {}
    for group in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        expected[group] = []
        for index, test in enumerate(meta[group]):
            label = f"{group}-{index}"
            expected[group].append((label, test))
            lines += ["find . -path '*/surefire-reports/*.xml' -delete",
                      shlex.join(prefix + ["-Dtest=" + test]),
                      f"echo $? > /evidence/{label}.exit",
                      f"mkdir -p /evidence/{label}",
                      f"find . -path '*/surefire-reports/*.xml' -exec cp '{{}}' /evidence/{label}/ ';'"]
    (work / "run.sh").write_text("\n".join(lines) + "\n")
    name = "ninfer-java-" + work.name.lower()
    docker = meta.get("docker_executable", "docker")
    docker_args = [docker, "--host", meta["docker_host"]] if meta.get("docker_host") else [docker]
    host_env = {"PATH": "/usr/bin:/bin", "HOME": str(Path(case_file).parent),
                "DOCKER_CONFIG": str(Path(case_file).parent / "docker-config")}
    cmd = docker_args + ["run", "--pull=never", "--name", name, "--platform", "linux/amd64", "--cpus", "4", "--memory", "6g",
           "-v", f"{work}:/evidence", meta["pinned_image"], "bash", "/evidence/run.sh"]
    try:
        result = run(cmd, timeout=timeout, env=host_env)
        (work / "docker.log").write_text(result.stdout)
    except subprocess.TimeoutExpired as error:
        raw = error.stdout or b""
        (work / "docker.log").write_text(raw.decode(errors="replace") if isinstance(raw, bytes) else raw)
        return {"status": "BLOCKED", "reason": "grader timeout", "evidence_dir": str(work)}
    finally:
        run(docker_args + ["rm", "-f", name], timeout=20, env=host_env)
    groups = {}
    for group, tests in expected.items():
        groups[group] = []
        for label, selector in tests:
            records = []
            for path in (work / label).glob("*.xml"):
                root = ET.parse(path).getroot()
                for item in root.iter("testcase"):
                    records.append({"class": item.get("classname"), "name": item.get("name"),
                                    "ok": not any(item.find(tag) is not None for tag in ("failure", "error", "skipped"))})
            exit_file = work / (label + ".exit")
            exit_code = int(exit_file.read_text()) if exit_file.exists() else None
            classname, _, method = selector.partition("#")
            matching = [x for x in records if (x["class"] == classname or x["class"].rsplit(".", 1)[-1] == classname)
                        and (not method or x["name"] == method or x["name"].startswith(method + "["))]
            passed = exit_code == 0 and bool(matching) and all(x["ok"] for x in records)
            groups[group].append({"selector": selector, "passed": passed, "exit_code": exit_code, "testcases": records})
    success = all(x["passed"] for tests in groups.values() for x in tests)
    observed_tests = all(x["testcases"] for tests in groups.values() for x in tests)
    return {"status": "PASS" if success else "FAIL" if observed_tests else "BLOCKED",
            "groups": groups, "docker_exit": result.returncode, "evidence_dir": str(work)}


def prepare(args):
    private = args.private_dir.resolve()
    private.mkdir(parents=True, exist_ok=True)
    private.chmod(0o700)
    rows = json.loads(args.metadata_file.read_text()) if args.metadata_file else []
    if not rows:
        for offset in (100, 200):
            url = ("https://datasets-server.huggingface.co/rows?dataset=SWE-bench%2FSWE-bench_Multilingual"
                   f"&config=default&split=test&offset={offset}&length=100")
            rows += [x["row"] for x in json.loads(fetch(url))["rows"] if x["row"]["instance_id"] in SELECTED]
    rows = [x for x in rows if x["instance_id"] in SELECTED]
    if {x['instance_id'] for x in rows} != set(SELECTED):
        raise ValueError("Both fixed selected instances must be present")
    report = {"dataset": DATASET, "official_score": False, "agent_output_limit": 32768,
              "isolation": "Docker grader; copy only base_dir/prompt_file into separate agent workspace",
              "cases": [{"case_id": row["instance_id"], "status": "PREPARING"} for row in rows]}
    publish_report(args.output, report)
    for row in rows:
        case_id = row["instance_id"]
        folder = private / case_id
        folder.mkdir(exist_ok=True)
        # Preserve argv[0]: OrbStack's docker symlink dispatches by executable name.
        row["docker_executable"] = str(Path(shutil.which("docker")).absolute())
        endpoints = json.loads(run(["docker", "context", "inspect", "--format", "{{json .Endpoints}}"], timeout=20).stdout)
        row["docker_host"] = endpoints["docker"]["Host"]
        if not row["docker_host"].startswith("unix://"):
            raise ValueError("Only a local Unix-socket Docker daemon is allowed")
        (folder / "docker-config").mkdir(exist_ok=True)
        (folder / "docker-config" / "config.json").write_text("{}\n")
        case = {"case_id": case_id, "status": "BLOCKED", "repo": row["repo"],
                "base_commit": row["base_commit"], "selection_reason": SELECTED[case_id],
                "base_dir": str(folder / "base"), "prompt_file": str(folder / "prompt.md"),
                "grade_script": str(folder / "grade.sh"), "environment": {"image": row["image"], "platform": "linux/amd64"}}
        case["metadata_sha256"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
        case["metadata_source"] = "https://huggingface.co/datasets/SWE-bench/SWE-bench_Multilingual"
        case["environment"]["allowed_source_prefixes"] = (["gson/src/main/java/"] if row["repo"] == "google/gson"
            else ["javaparser-core/src/main/java/", "javaparser-symbol-solver-core/src/main/java/"])
        case["environment"]["production_prefixes"] = case["environment"]["allowed_source_prefixes"]
        case["environment"]["public_verify_command"] = None
        case["environment"]["public_verify_status"] = "NOT_RUN: dependency-complete build is available only in trusted Docker grader"
        report["cases"] = [case if item["case_id"] == case_id else item for item in report["cases"]]
        try:
            digest = IMAGE_DIGESTS[case_id]
            row["pinned_image"] = row["image"].rsplit(":", 1)[0] + "@" + digest
            case["environment"]["pinned_image"] = row["pinned_image"]
            try:
                pull = run(["docker", "pull", "--platform", "linux/amd64", row["pinned_image"]], timeout=180)
            except subprocess.TimeoutExpired as error:
                raw = error.stdout or b""
                (folder / "pull.log").write_text(raw.decode(errors="replace") if isinstance(raw, bytes) else raw)
                raise RuntimeError("official image pull exceeded 180s; see pull.log") from error
            (folder / "pull.log").write_text(pull.stdout)
            if pull.returncode:
                raise RuntimeError("official image pull failed; see pull.log")
            source = fetch(f"https://codeload.github.com/{row['repo']}/tar.gz/{row['base_commit']}")
            case["source_archive_sha256"] = hashlib.sha256(source).hexdigest()
            if not (folder / "base").exists():
                extract_source(source, folder / "base")
            (folder / "prompt.md").write_text(row["problem_statement"] +
                "\n\nImplement the issue in production Java sources. Preserve existing behavior. "
                "Only src/main/java/**/*.java edits are accepted. Do not modify build configuration or tests.\n")
            meta = folder / "private-case.json"
            meta.write_text(json.dumps(row, indent=2))
            wrapper = "#!/bin/sh\nexec " + shlex.join([sys.executable, str(Path(__file__).resolve()), "grade", "--case-file", str(meta), "--patch"]) + ' "$1"\n'
            (folder / "grade.sh").write_text(wrapper)
            (folder / "grade.sh").chmod(0o700)
            receipt = folder / "environment-receipt.json"
            receipt.write_text(json.dumps({"docker_host": row["docker_host"], "image": row["pinned_image"],
                "python_executable": sys.executable, "python_version": sys.version,
                "docker_executable": row["docker_executable"], "docker_version": run(["docker", "--version"]).stdout.strip(),
                "host_environment": {"PATH": "/usr/bin:/bin", "HOME": str(folder), "DOCKER_CONFIG": str(folder / "docker-config")},
                "container_resources": {"cpus": 4, "memory": "6g", "platform": "linux/amd64", "pull": "never"}}, indent=2))
            case["environment"]["receipt_file"] = str(receipt)
            case["grade_files"] = {str(path): sha256_file(path) for path in [folder / "grade.sh", Path(__file__).resolve(), meta, receipt, folder / "docker-config" / "config.json"]}
            (folder / "empty.patch").write_text("")
            (folder / "gold.patch").write_text(row["patch"])
            case["empty_result"] = grade(meta, folder / "empty.patch", args.grade_timeout)
            case["gold_result"] = grade(meta, folder / "gold.patch", args.grade_timeout)
            empty = case["empty_result"]
            gold = case["gold_result"]
            empty_valid = (empty["status"] == "FAIL" and
                           any(not x["passed"] for x in empty["groups"]["FAIL_TO_PASS"]) and
                           all(x["passed"] for x in empty["groups"]["PASS_TO_PASS"]))
            if empty_valid and gold["status"] == "PASS":
                case["status"] = "READY"
            else:
                case["blocked_reason"] = "empty F2P fail/P2P pass and gold all-pass gate not satisfied"
        except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as error:
            case["blocked_reason"] = str(error)
        publish_report(args.output, report)
    print(json.dumps({"cases": [{"case_id": x["case_id"], "status": x["status"], "reason": x.get("blocked_reason")} for x in report["cases"]]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--private-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--grade-timeout", type=int, default=420)
    p.add_argument("--metadata-file", type=Path)
    g = sub.add_parser("grade")
    g.add_argument("--case-file", required=True)
    g.add_argument("--patch", required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args)
    else:
        outcome = grade(args.case_file, args.patch)
        tests = [item for group in outcome.get("groups", {}).values() for selected in group for item in selected["testcases"]]
        outcome.update(passed=outcome["status"] == "PASS", tests_total=len(tests),
                       tests_passed=sum(item["ok"] for item in tests))
        print(json.dumps(outcome))
        sys.exit(0 if outcome["status"] == "PASS" else 1)
