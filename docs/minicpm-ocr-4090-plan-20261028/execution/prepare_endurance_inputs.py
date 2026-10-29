"""Prepare the same 49-page, three-document P0 stream for both E0 runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from prepare_perf_inputs import materialize, read_manifest, write
from ocrbench.core import load_manifest


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--root", type=Path, default=Path("/work"))
args = parser.parse_args()
os.umask(0o077)
source = args.root / "corpus-extra/perf-prepared/d0-complete3-49-manifest.json"
pages = read_manifest(source)
assert len(pages) == 49 and {p["document_id"] for p in pages} == {"PDF-001", "PDF-002", "PDF-003"}
assert all(p["kind"] == "pdf" and p.get("expected_pixel_hash") for p in pages)
out = args.root / "corpus-extra/endurance49"
out.mkdir(exist_ok=False, mode=0o700)
prepared = materialize(pages, out / "inputs", None, True)
manifest = out / "manifest.json"
write(manifest, {"pages": prepared, "timing_scope": "P0", "purpose": "E0 continuous multi-page documents"})
assert len(load_manifest(manifest)) == 49
profile = {"source_manifest_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
           "base_unique_pages": 49, "original_documents": 3,
           "quality_samples_added_by_repetition": 0,
           "note": "PNG preparation is offline. D0 still rerenders original PDFs. E0 retains original document grouping."}
write(out / "profile.json", profile)
print(json.dumps(profile))
