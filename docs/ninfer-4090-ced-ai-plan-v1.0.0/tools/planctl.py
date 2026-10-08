#!/usr/bin/env python3
"""Read-only task navigation. Status files are hints, not proof of engine test results."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_plan(root: Path = ROOT) -> dict[str, Any]:
    p = json.loads((root / 'manifests/plan.json').read_text(encoding='utf-8'))
    if p.get('schema_version') != 1 or not isinstance(p.get('tasks'), list):
        raise ValueError('unsupported or malformed plan')
    return p


def ready_tasks(plan: dict[str, Any], states: dict[str, str], include_optional: bool = False,
                subgates: dict[str, str] | None = None) -> list[dict[str, Any]]:
    optional = {p['id'] for p in plan['phases'] if p['optional']}
    conditions = plan.get('subgate_conditions', {})
    ready = []
    for t in plan['tasks']:
        if states.get(t['id'], 'NOT_RUN') != 'NOT_RUN':
            continue
        if not include_optional and t['phase'] in optional:
            continue
        if not all(states.get(d) == 'PASS' for d in t['depends_on']):
            continue
        condition = conditions.get(t['id'])
        if condition and (subgates or {}).get(condition['requires']) != condition['status']:
            continue
        ready.append(t)
    return ready


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('list')
    show = sub.add_parser('show'); show.add_argument('id')
    nxt = sub.add_parser('next')
    nxt.add_argument('--state', type=Path)
    nxt.add_argument('--include-optional', action='store_true')
    args = parser.parse_args()
    try:
        plan = load_plan()
        if args.command == 'list':
            for p in plan['phases']:
                suffix = ' [optional]' if p['optional'] else ''
                print(f"{p['id']}  {p['title']}  ({len(p['tasks'])} tasks + gate){suffix}")
        elif args.command == 'show':
            matches = [p for p in plan['phases'] if p['id'] == args.id]
            if matches:
                print((ROOT / matches[0]['document']).read_text(encoding='utf-8'))
            else:
                tasks = [t for t in plan['tasks'] if t['id'] == args.id]
                if not tasks:
                    parser.error('unknown phase/task id')
                print(json.dumps(tasks[0], ensure_ascii=False, indent=2))
        else:
            state = json.loads(args.state.read_text(encoding='utf-8')) if args.state else {}
            tasks = ready_tasks(plan, state.get('tasks', {}), args.include_optional, state.get('subgates', {}))
            for t in tasks:
                print(f"{t['id']}  {t['title']}  [{t['resource']}]")
            if not tasks:
                print('No task is ready according to the supplied state. No execution was performed.')
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
