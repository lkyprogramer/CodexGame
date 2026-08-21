#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qcb.audit import audit_result_file
from qcb.util import dump_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit result completeness and experimental consistency before reporting")
    parser.add_argument("--results", required=True)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--check-artifacts", action="store_true")
    parser.add_argument("--json")
    args = parser.parse_args()
    result = audit_result_file(args.root, args.results, check_artifacts=args.check_artifacts)
    if args.json:
        dump_json(args.json, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
