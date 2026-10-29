"""Run a frozen input manifest against one candidate at a time."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .core import load_manifest, run_pages


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", choices=["mini", "ovis"], required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--warmup-manifest", type=Path,
                        help="Development-only inputs, RGB-disjoint from the timed workload; primes every persistent worker")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--layout-model-dir", type=Path)
    parser.add_argument("--page-admission", type=int, choices=[1, 2, 4], default=1)
    parser.add_argument("--region-limit", type=int, choices=[1, 2, 4], default=4)
    parser.add_argument("--timing-scope", choices=["D0", "P0", "R0"], default="D0")
    parser.add_argument("--page-timeout", type=float, default=300)
    parser.add_argument("--document-timeout", type=float, default=1800)
    parser.add_argument("--region-timeout", type=float, default=120)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--option", action="append", default=[])
    args = parser.parse_args(argv)
    if any(value <= 0 for value in (args.page_timeout, args.document_timeout, args.region_timeout)):
        parser.error("timeouts must be positive")
    if args.limit is not None and args.limit <= 0:
        parser.error("limit must be positive")
    options = {}
    for option in args.option:
        key, separator, value = option.partition("=")
        if not separator or not key:
            parser.error("--option requires key=value")
        try:
            options[key] = json.loads(value)
        except json.JSONDecodeError:
            options[key] = value
    pages = load_manifest(args.manifest.resolve())
    warmup_pages = load_manifest(args.warmup_manifest.resolve()) if args.warmup_manifest else None
    if args.limit:
        pages = pages[:args.limit]
    config = vars(args).copy()
    config.update(out=str(args.out), model_dir=str(args.model_dir),
                  layout_model_dir=str(args.layout_model_dir) if args.layout_model_dir else None,
                  options=options, api_key=os.environ.get("OCR_API_KEY", "local-only"))
    config.pop("manifest")
    config.pop("warmup_manifest")
    config.pop("option")
    config.pop("limit")
    summary = run_pages(pages, config, warmup_pages=warmup_pages)
    print(json.dumps({key: value for key, value in summary.items() if key != "results"}, ensure_ascii=False))
    return 0 if (summary["run_status"] == "COMPLETED" and summary["pass_pages"] == summary["submitted_pages"]
                 and summary["pass_documents"] == len(summary["documents"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
