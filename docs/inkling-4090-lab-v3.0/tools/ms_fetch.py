#!/usr/bin/env python3
"""Plan and verify model downloads from ModelScope, keyed by SHA256.

plan:   list a ModelScope repo, filter files, check expected SHA256 values, write an aria2c input file.
verify: hash every planned file and merge the results into a lock file.
"""
import argparse
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

API = "https://www.modelscope.cn/api/v1/models/{model}/repo/files?Revision={rev}&Recursive=true"
RESOLVE = "https://www.modelscope.cn/models/{model}/resolve/{rev}/{path}"
SHA = re.compile(r"^[0-9a-f]{64}$")


def list_files(model, rev, files_json=None):
    if files_json:
        data = json.loads(Path(files_json).read_text())
    else:
        with urllib.request.urlopen(API.format(model=model, rev=urllib.parse.quote(rev)), timeout=60) as r:
            data = json.load(r)
    files = ((data.get("Data") or {}).get("Files")) or []
    out = [{"path": f["Path"], "size": int(f["Size"]), "sha256": (f.get("Sha256") or "").lower()}
           for f in files if f.get("Type") == "blob"]
    if not out:
        raise SystemExit("no files listed for " + model)
    return out


def plan(args):
    expect = {}
    for item in args.expect:
        path, _, digest = item.partition("=")
        if not SHA.match(digest.lower()):
            raise SystemExit("bad --expect value: " + item)
        expect[path] = digest.lower()
    files = list_files(args.model, args.revision, args.files_json)
    chosen = [f for f in files
              if (not args.include or any(fnmatch.fnmatchcase(f["path"], g) for g in args.include))
              and not any(fnmatch.fnmatchcase(f["path"], g) for g in args.exclude)]
    listed = {f["path"] for f in files}
    errors = ["expected file not listed: " + p for p in expect if p not in listed]
    for f in chosen:
        if not SHA.match(f["sha256"]):
            errors.append("no SHA256 from ModelScope for " + f["path"])
        if f["path"] in expect and expect[f["path"]] != f["sha256"]:
            errors.append("SHA256 mismatch for %s: ModelScope %s, expected %s" % (f["path"], f["sha256"], expect[f["path"]]))
    missing = [p for p in expect if p in listed and p not in {f["path"] for f in chosen}]
    errors += ["expected file filtered out: " + p for p in missing]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    out = Path(args.out)
    meta = out / ".ms_fetch"
    meta.mkdir(parents=True, exist_ok=True)
    lines, entries = [], []
    for f in chosen:
        local = f["path"]
        if args.strip_suffix and local.endswith(args.strip_suffix):
            local = local[: -len(args.strip_suffix)]
        dest = out / local
        lines += [RESOLVE.format(model=args.model, rev=args.revision, path=urllib.parse.quote(f["path"])),
                  "  dir=" + str(dest.parent), "  out=" + dest.name, "  checksum=sha-256=" + f["sha256"]]
        entries.append({"remote_path": f["path"], "local_path": local, "size": f["size"], "sha256": f["sha256"]})
    (meta / "aria2.txt").write_text("\n".join(lines) + "\n")
    plan_doc = {"source": "modelscope", "model": args.model, "modelscope_revision": args.revision,
                "hf_revision": args.hf_revision, "files": entries}
    (meta / "plan.json").write_text(json.dumps(plan_doc, indent=2) + "\n")
    total = sum(e["size"] for e in entries)
    print("planned %d files, %.2f GiB -> %s" % (len(entries), total / 2**30, meta / "aria2.txt"))
    return 0


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 22), b""):
            h.update(block)
    return h.hexdigest()


def verify(args):
    out = Path(args.out)
    plan_doc = json.loads((out / ".ms_fetch" / "plan.json").read_text())
    lock_path = Path(args.lock)
    lock = json.loads(lock_path.read_text()) if lock_path.exists() else {"files": []}
    bad = 0
    for e in plan_doc["files"]:
        p = out / e["local_path"]
        if not p.is_file() or p.stat().st_size != e["size"]:
            print("MISSING or wrong size: %s" % p, file=sys.stderr)
            bad += 1
            continue
        digest = sha256_file(p)
        if digest != e["sha256"]:
            print("SHA256 MISMATCH: %s %s" % (p, digest), file=sys.stderr)
            bad += 1
            continue
        record = {"path": str(p), "size": e["size"], "sha256": digest, "model": plan_doc["model"],
                  "remote_path": e["remote_path"], "hf_revision": plan_doc.get("hf_revision"), "source": "modelscope"}
        lock["files"] = [r for r in lock["files"] if r["path"] != record["path"]] + [record]
        print("OK %s" % p)
    if bad:
        return 1
    lock["files"].sort(key=lambda r: r["path"])
    lock_path.write_text(json.dumps(lock, indent=2) + "\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan")
    p.add_argument("--model", required=True)
    p.add_argument("--revision", default="master")
    p.add_argument("--hf-revision")
    p.add_argument("--out", required=True)
    p.add_argument("--include", action="append", default=[])
    p.add_argument("--exclude", action="append", default=[])
    p.add_argument("--expect", action="append", default=[], help="remote_path=sha256")
    p.add_argument("--strip-suffix")
    p.add_argument("--files-json", help="offline ModelScope listing (tests)")
    v = sub.add_parser("verify")
    v.add_argument("--out", required=True)
    v.add_argument("--lock", required=True)
    args = ap.parse_args(argv)
    return plan(args) if args.cmd == "plan" else verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
