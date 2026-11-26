#!/usr/bin/env python3
"""Structural self-check of the v3 package. Runs no engine, GPU or example command."""
import argparse
import ast
import json
from pathlib import Path
import re
import subprocess
import sys

TOPICS = 10


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=Path, default=Path(__file__).resolve().parents[1])
    args = ap.parse_args(argv)
    p = args.package.resolve()
    errors, checks = [], {}

    def ck(ok, msg):
        if not ok:
            errors.append(msg)

    files = [f for f in p.rglob("*") if f.is_file() and "__pycache__" not in f.parts]
    for f in files:
        if f.suffix == ".py":
            ast.parse(f.read_text(), filename=str(f))
        if f.suffix == ".json":
            json.loads(f.read_text())
    shells = [f for f in files if f.suffix == ".sh"]
    for f in shells:
        r = subprocess.run(["bash", "-n", str(f)], capture_output=True, text=True)
        ck(r.returncode == 0, "shell syntax %s: %s" % (f.relative_to(p), r.stderr))
    checks["python_files"] = sum(f.suffix == ".py" for f in files)
    checks["shell_scripts"] = len(shells)

    counts = {"md": 0, "fences": 0, "bash_blocks": 0, "links": 0}
    text = {}
    for f in sorted(p.rglob("*.md")):
        counts["md"] += 1
        body = f.read_text()
        text[f.relative_to(p).as_posix()] = body
        fence, lang, block, prose = None, "", [], []
        for line in body.splitlines():
            m = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
            if fence:
                if m and m[1][0] == fence[0] and len(m[1]) >= len(fence) and not m[2].strip():
                    if lang in ("bash", "sh", "shell"):
                        r = subprocess.run(["bash", "-n"], input="\n".join(block) + "\n", text=True, capture_output=True)
                        counts["bash_blocks"] += 1
                        ck(r.returncode == 0, "shell block %s: %s" % (f.relative_to(p), r.stderr))
                    fence = None
                else:
                    block.append(line)
            elif m:
                fence, lang, block = m[1], m[2].strip().split(" ")[0], []
                counts["fences"] += 1
            else:
                prose.append(line)
        ck(fence is None, "unclosed fence " + str(f.relative_to(p)))
        for line in prose:
            if line.lstrip().startswith("|"):
                ck(line.count("|") - line.count("\\|") >= 3, "suspicious table row %s: %s" % (f.relative_to(p), line[:60]))
        for target in re.findall(r"(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)", "\n".join(prose)):
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                continue
            dest = (f.parent / target.split("#", 1)[0]).resolve()
            counts["links"] += 1
            ck(dest == p or p in dest.parents, "link escapes package %s %s" % (f.relative_to(p), target))
            ck(dest.exists(), "broken link %s %s" % (f.relative_to(p), target))
    checks.update(counts)

    topics = sorted((p / "docs").glob("*.md"))
    checks["topic_documents"] = len(topics)
    ck(len(topics) == TOPICS, "expected %d topic documents" % TOPICS)

    tasks_doc = text.get("docs/07_tasks.md", "")
    task_ids = re.findall(r"^\| (T\d{2}) \|", tasks_doc, re.M)
    ck(len(task_ids) == len(set(task_ids)) and task_ids, "task ids missing or duplicated")
    statuses = re.findall(r"\| (NOT_RUN|RUNNING|PASS|FAIL|BLOCKED|NO_BENEFIT|DEFERRED) \|\s*$", tasks_doc, re.M)
    rows = re.findall(r"^\| (?:T\d{2}|R1–R7|O\d) \|", tasks_doc, re.M)
    ck(len(statuses) == len(rows), "every task row needs one status from the vocabulary")
    referenced = set()
    for body in text.values():
        referenced |= set(re.findall(r"\bT\d{2}\b", body))
    ck(referenced <= set(task_ids), "unknown task ids referenced: %s" % sorted(referenced - set(task_ids)))
    checks["tasks"] = len(task_ids)

    research = re.findall(r"^\| (R\d) \|", text.get("docs/06_loop_research.md", ""), re.M)
    ck(research == ["R%d" % i for i in range(1, 8)], "research ids R1-R7")

    sources_doc = text.get("docs/09_sources.md", "")
    source_ids = re.findall(r"^\| (S\d{2}) \|", sources_doc, re.M)
    ck(len(source_ids) == len(set(source_ids)) and source_ids, "source ids missing or duplicated")
    cited = set()
    for body in text.values():
        cited |= set(re.findall(r"\bS\d{2}\b", body))
    ck(cited <= set(source_ids), "unknown source ids cited: %s" % sorted(cited - set(source_ids)))
    checks["sources"] = len(source_ids)

    assets = re.findall(r"^\| (A\d)(?:（[^|]*）)? \|", text.get("docs/01_model.md", ""), re.M)
    ck(assets == ["A%d" % i for i in range(1, 7)], "asset ids A1-A6")
    shas = re.findall(r"\b[0-9a-f]{64}\b", text.get("docs/01_model.md", ""))
    runbook = text.get("docs/08_runbooks.md", "")
    for s in re.findall(r"=([0-9a-f]{64})'", runbook):
        ck(s in shas, "runbook SHA256 not in asset table: " + s[:12])
    checks["asset_sha256"] = len(set(shas))

    report = {"scope": "package_structure_only", "target_execution": "NOT_RUN",
              "status": "PASS" if not errors else "FAIL", "checks": checks, "errors": errors}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
