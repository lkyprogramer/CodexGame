from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_result_file
from .catalog import discover_tasks, load_suite
from .config import load_config
from .report import generate_comparison_report, generate_model_report
from .runner import run_suite
from .util import dump_json, load_json


def _root(value: str | None) -> Path:
    return Path(value).resolve() if value else Path(__file__).resolve().parent.parent


def command_run(args: argparse.Namespace) -> int:
    root = _root(args.root)
    config = load_config(args.config)
    tasks = load_suite(root, args.suite)
    if args.task:
        selected = set(args.task)
        tasks = [task for task in tasks if task.id in selected]
        missing = selected - {task.id for task in tasks}
        if missing:
            raise SystemExit(f"Tasks not present in suite: {sorted(missing)}")
    seeds = [int(x) for x in args.seeds.split(",") if x.strip()]
    result = run_suite(root, tasks, config, args.suite, args.output, seeds, resume=args.resume, overwrite=args.overwrite)
    print(result)
    return 0


def command_report(args: argparse.Namespace) -> int:
    generate_model_report(args.results, args.output, args.json)
    print(args.output)
    return 0


def command_compare(args: argparse.Namespace) -> int:
    generate_comparison_report(args.model_a, args.model_b, args.output, args.json)
    print(args.output)
    return 0


def command_audit(args: argparse.Namespace) -> int:
    root = _root(args.root)
    result = audit_result_file(root, args.results, check_artifacts=args.check_artifacts)
    if args.json:
        dump_json(args.json, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


def command_validate(args: argparse.Namespace) -> int:
    root = _root(args.root)
    tasks = discover_tasks(root)
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)):
        raise SystemExit("Duplicate task IDs")
    for suite in (root / "suites").glob("*.json"):
        data = load_json(suite)
        unknown = set(data["task_ids"]) - set(ids)
        if unknown:
            raise SystemExit(f"{suite.name}: unknown tasks {sorted(unknown)}")
    print(f"Validated {len(tasks)} tasks and {len(list((root/'suites').glob('*.json')))} suites")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qcb", description="QCB-4090 coding benchmark")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run a benchmark suite")
    run.add_argument("--config", required=True)
    run.add_argument("--suite", default="smoke", choices=["smoke", "core", "full", "finalists"])
    run.add_argument("--seeds", default="42")
    run.add_argument("--task", action="append")
    run.add_argument("--output", default="results")
    policy = run.add_mutually_exclusive_group()
    policy.add_argument("--resume", action="store_true", help="Skip task/seed pairs already present in the result file")
    policy.add_argument("--overwrite", action="store_true", help="Replace an existing result file")
    run.add_argument("--root")
    run.set_defaults(func=command_run)

    report = sub.add_parser("report", help="Generate one-model report")
    report.add_argument("--results", required=True)
    report.add_argument("--output", required=True)
    report.add_argument("--json")
    report.set_defaults(func=command_report)

    compare = sub.add_parser("compare", help="Compare two paired result files")
    compare.add_argument("--model-a", required=True)
    compare.add_argument("--model-b", required=True)
    compare.add_argument("--output", required=True)
    compare.add_argument("--json")
    compare.set_defaults(func=command_compare)

    audit = sub.add_parser("audit", help="Audit result completeness and experimental consistency")
    audit.add_argument("--results", required=True)
    audit.add_argument("--check-artifacts", action="store_true")
    audit.add_argument("--json")
    audit.add_argument("--root")
    audit.set_defaults(func=command_audit)

    validate = sub.add_parser("validate", help="Validate catalog and suites")
    validate.add_argument("--root")
    validate.set_defaults(func=command_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
