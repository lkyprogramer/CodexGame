"""Freeze host-rendered G6 pixels while keeping native PDF inputs for Stage1."""
import argparse
import json
import os
from pathlib import Path

from prepare_perf_inputs import materialize, read_manifest, sha, write
from ocrbench.core import load_manifest
from ocrbench.extra_cli import select_pairs


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path("/work/corpus-extra/g6-public-extra"))
args = parser.parse_args()
os.umask(0o077)
source = args.root / "stage1-manifest.json"
pages = read_manifest(source)
assert len(pages) == 29 and len({p["source_family_id"] for p in pages}) == 5
assert all(p["kind"] == "pdf" and sha(Path(p["path"])) == p["source_sha256"] for p in pages)
pages = [{k: v for k, v in p.items() if k not in ("table_reference", "review_image", "GT_status")}
         for p in pages]
out = args.root / "host29-prepared"
out.mkdir(exist_ok=False, mode=0o700)
prepared = materialize(pages, out / "inputs", None, False)
by_id = {p["page_id"]: p for p in prepared}
native = [{**p, "expected_pixel_hash": by_id[p["page_id"]]["expected_pixel_hash"]} for p in pages]
write(out / "d0-manifest.json", {"pages": native})
write(out / "p0-manifest.json", {"pages": prepared})
cases = {p["page_id"]: p for p in load_manifest(out / "d0-manifest.json")}
pairs = select_pairs(cases, args.root / "pairs.json")
chains = select_pairs(cases, args.root / "chains.json")
assert len(pairs) == 21 and len(chains) == 3
assert len(load_manifest(out / "p0-manifest.json")) == 29
write(out / "all-tasks.json", {"pairs": pairs + chains})
profile = {"scope": "G6 supplement only; no additions to main420 or performance workloads",
           "source_manifest_sha256": sha(source), "d0_manifest_sha256": sha(out / "d0-manifest.json"),
           "p0_manifest_sha256": sha(out / "p0-manifest.json"), "unique_pages": 29,
           "source_families": 5, "adjacent_pairs": 21, "chains": 3,
           "all_tasks_sha256": sha(out / "all-tasks.json"),
           "preparation": "offline host RGB freeze; Stage1 D0 rerenders the same original PDFs",
           "complete_cell_GT": False}
write(out / "profile.json", profile)
print(json.dumps(profile))
