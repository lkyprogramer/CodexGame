#!/usr/bin/env python3
"""Validate plan structure and local links; never claims to validate CUDA or model quality."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def check_graph(tasks: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids = [t['id'] for t in tasks]
    if len(set(ids)) != len(ids):
        errors.append('duplicate task id')
    nodes = {t['id']: t for t in tasks}
    for t in tasks:
        for d in t['depends_on']:
            if d not in nodes:
                errors.append(f"{t['id']}: missing dependency {d}")
    visiting, done = set(), set()
    def visit(k: str) -> None:
        if k in visiting:
            errors.append(f'cycle at {k}')
            return
        if k in done or k not in nodes:
            return
        visiting.add(k)
        for d in nodes[k]['depends_on']:
            visit(d)
        visiting.remove(k)
        done.add(k)
    for k in nodes:
        visit(k)
    return errors


def validate(root: Path = ROOT) -> list[str]:
    errors = []
    required = ['00-START-HERE.md', 'AGENTS.md', 'manifests/plan.json', 'manifests/gates.json',
                'configs/experiment.json', 'prompts/START.md', 'templates/phase-report.md',
                'docs/03-contracts.md', 'docs/05-verification.md', 'tools/budget.py', 'tools/planctl.py']
    for name in required:
        if not (root/name).is_file():
            errors.append(f'missing file: {name}')
    parsed = {}
    for f in root.rglob('*.json'):
        try:
            parsed[f.relative_to(root).as_posix()] = json.loads(f.read_text(encoding='utf-8'))
        except (ValueError, OSError) as e:
            errors.append(f'{f.name}: invalid JSON: {e}')
    plan = parsed.get('manifests/plan.json')
    if plan:
        errors.extend(check_graph(plan['tasks']))
        phases = {p['id']: p for p in plan['phases']}
        known = {t['id'] for t in plan['tasks']}
        for p in plan['phases']:
            doc = root / p['document']
            if not doc.is_file():
                errors.append(f"missing phase doc {p['document']}")
            if p['gate_task'] not in known:
                errors.append(f"missing gate {p['gate_task']}")
        for t in plan['tasks']:
            if t.get('status') != 'NOT_RUN':
                errors.append(f"plan falsely contains executed task: {t['id']}")
            for key in ('files','steps','cases','outputs','contract','failure_action'):
                if not t.get(key):
                    errors.append(f"{t['id']}: empty {key}")
            if t['phase'] not in phases:
                errors.append(f"{t['id']}: unknown phase")
                continue
            doc = root / phases[t['phase']]['document']
            if doc.is_file() and f"### {t['id']} —" not in doc.read_text(encoding='utf-8'):
                errors.append(f"task missing in phase document: {t['id']}")
        gates=parsed.get('manifests/gates.json',{})
        gate_phase_ids={p['phase'] for p in gates.get('phases',[])}
        if gate_phase_ids != set(phases):
            errors.append('phase/gate manifest mismatch')
    for f in root.rglob('*.md'):
        text = f.read_text(encoding='utf-8')
        if len(re.findall(r'^```', text, re.M)) % 2:
            errors.append(f'unbalanced code fence: {f.relative_to(root)}')
        for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)',text):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',link) or link.startswith('#'):
                continue
            dest = unquote(link.split('#',1)[0])
            if dest and not (f.parent/dest).exists():
                errors.append(f'broken link: {f.relative_to(root)} -> {dest}')
    exp=parsed.get('configs/experiment.json',{})
    if exp:
        if exp['production']['allow_production_pause'] or exp['production']['auto_enable_lsp']:
            errors.append('unsafe production default')
        if exp['candidate']['late_state_prefill'] != 'off':
            errors.append('candidate default must be off')
    sums=root/'SHA256SUMS'
    if sums.is_file():
        for line in sums.read_text().splitlines():
            if not line.strip(): continue
            expected,name=line.split('  ',1)
            path=root/name
            if not path.resolve().is_relative_to(root.resolve()):
                errors.append('checksum path escapes package')
            elif not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
                errors.append(f'checksum mismatch: {name}')
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    a=p.parse_args()
    errors=validate(a.root)
    if errors:
        print('\n'.join('ERROR: '+e for e in errors))
        return 1
    plan=json.loads((a.root/'manifests/plan.json').read_text())
    print(f"PASS: package structure, JSON, DAG, local links and safe defaults; {len(plan['phases'])} phases, {len(plan['tasks'])} tasks.")
    print('NOT TESTED: NInfer compilation, CUDA execution, Predictor training, inference speed or model quality.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
