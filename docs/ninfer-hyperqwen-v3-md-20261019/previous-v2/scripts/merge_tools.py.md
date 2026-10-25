# V2 支撑材料：`scripts/merge_tools.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/merge_tools.py -->
<!-- payload-sha256: d6b20a658ea148b419f8265a911ef4ccb22e41c45a39e82b334f17ae4bcbfd8e -->
<!-- payload-bytes: 17647 -->

<!-- payload-begin -->
````python
"""Local audit helpers. No network fetches, repository writes, or production restarts.

The optional merge probe operates in a disposable local clone. These checks validate
recorded evidence; they do not replace source review or independently certify a GPU run.
"""
from __future__ import annotations
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate_dag(tasks: list[dict]) -> list[str]:
    ids = [t['id'] for t in tasks]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate task id')
    deps = {t['id']: set(t.get('depends_on', [])) for t in tasks}
    for node, parents in deps.items():
        if not parents <= set(ids):
            raise ValueError(f'{node}: missing dependency {sorted(parents - set(ids))}')
    result: list[str] = []
    while deps:
        ready = sorted(node for node, parents in deps.items() if not parents)
        if not ready:
            raise ValueError('dependency cycle')
        result.extend(ready)
        for node in ready:
            del deps[node]
        for parents in deps.values():
            parents.difference_update(ready)
    return result


def check_junit(path: Path, required: list[str]) -> dict:
    root = ET.parse(path).getroot()
    tests = list(root.iter('testcase'))
    patterns = [re.compile(s) for s in required]
    names = [t.get('name', '') for t in tests]
    duplicates = sorted(k for k, v in collections.Counter(names).items() if v > 1)
    failed = [t.get('name', '') for t in tests if t.find('failure') is not None or t.find('error') is not None]
    skipped = [t.get('name', '') for t in tests if t.find('skipped') is not None or t.get('status') in ('notrun', 'disabled')]
    required_skipped = [name for name in skipped if any(p.search(name) for p in patterns)]
    missing = [p.pattern for p in patterns if not any(p.search(name) for name in names)]
    return {'passed': bool(tests and patterns) and not (duplicates or failed or required_skipped or missing),
            'total': len(tests), 'failed': failed, 'skipped': skipped,
            'required_skipped': required_skipped, 'missing_required_patterns': missing,
            'duplicate_names': duplicates, 'source_sha256': sha256_file(path)}


def redact_argv(argv: list[str]) -> list[str]:
    result, redact_next = [], False
    sensitive = re.compile(r'(^|[-_])(api[-_]?key|access[-_]?token|auth[-_]?token|bearer[-_]?token|refresh[-_]?token|secret|password|authorization)([-_]|$)', re.I)
    for arg in argv:
        if redact_next:
            result.append('<redacted>'); redact_next = False; continue
        if arg.startswith('-') and (arg.split('=', 1)[0].lower() == '--token' or sensitive.search(arg.split('=', 1)[0])):
            if '=' in arg:
                result.append(arg.split('=', 1)[0] + '=<redacted>')
            else:
                result.append(arg); redact_next = True
        else:
            result.append(arg)
    return result


def _percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    i = (len(ordered) - 1) * q
    lo = math.floor(i); hi = math.ceil(i)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (i - lo)


DEFAULT_RULES = {
    'ttft_seconds': {'direction': 'lower', 'p50_relative': .05, 'p90_relative': .10, 'absolute_floor': .005},
    'decode_tok_s': {'direction': 'higher', 'p50_relative': .03, 'p10_relative': .05, 'absolute_floor': 0.0},
    'prepare_seconds': {'direction': 'lower', 'p50_relative': .05, 'p90_relative': .10, 'absolute_floor': .0005},
}


def compare_samples(baseline: list[dict], candidate: list[dict], rules: dict | None = None,
                    min_samples: int = 10) -> dict:
    rules = DEFAULT_RULES if rules is None else rules
    if min_samples < 2 or not rules:
        raise ValueError('need at least two samples and nonempty rules')
    def index(rows: list[dict]) -> dict:
        result = {}
        for row in rows:
            key = (str(row['case_id']), int(row['repeat']))
            if key in result:
                raise ValueError(f'duplicate case/repeat {key}')
            for metric in rules:
                value = row['metrics'].get(metric)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError(f'invalid or missing {metric}: {key}')
            result[key] = row
        return result
    b, c = index(baseline), index(candidate)
    if set(b) != set(c):
        raise ValueError('baseline and candidate case/repeat identities differ')
    results = []
    for case_id in sorted({key[0] for key in b}):
        keys = sorted(key for key in b if key[0] == case_id)
        item = {'case_id': case_id, 'n': len(keys), 'passed': len(keys) >= min_samples, 'metrics': {}}
        if len(keys) < min_samples:
            item['blocked_reason'] = f'fewer than {min_samples} paired observations'
        for metric, rule in rules.items():
            direction = rule['direction']
            if direction not in ('higher', 'lower'):
                raise ValueError('direction must be higher or lower')
            observed = {}
            for quantile in ('p50', 'p90', 'p10'):
                rel_key = quantile + '_relative'
                if rel_key not in rule:
                    continue
                bv = _percentile([float(b[k]['metrics'][metric]) for k in keys], int(quantile[1:]) / 100)
                cv = _percentile([float(c[k]['metrics'][metric]) for k in keys], int(quantile[1:]) / 100)
                budget = max(abs(bv) * float(rule[rel_key]), float(rule.get('absolute_floor', 0.0)))
                passed = cv <= bv + budget if direction == 'lower' else cv >= bv - budget
                observed[quantile] = {'baseline': bv, 'candidate': cv, 'allowed_absolute_regression': budget, 'passed': passed}
                item['passed'] = item['passed'] and passed
            item['metrics'][metric] = observed
        results.append(item)
    return {'passed': bool(results) and all(r['passed'] for r in results), 'min_samples': min_samples,
            'cases': results, 'scope': 'performance guardrails, not a statistical non-inferiority proof or task-quality gate'}


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME='Merge Audit', GIT_AUTHOR_EMAIL='audit@example.invalid',
               GIT_COMMITTER_NAME='Merge Audit', GIT_COMMITTER_EMAIL='audit@example.invalid')
    run = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, '-C', str(repo), *args],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=120)
    if check and run.returncode:
        raise RuntimeError(run.stderr.decode('utf-8', 'replace').strip() or f'git returned {run.returncode}')
    return run


def audit_repository(repo: Path, pin: dict, out: Path, merge_probe: bool = False) -> dict:
    repo, out = repo.resolve(), out.resolve()
    top = Path(_git(repo, 'rev-parse', '--show-toplevel').stdout.decode().strip()).resolve()
    if out == top or top in out.parents:
        raise ValueError('audit output must be outside the repository working tree')
    if out.exists() and any(out.iterdir()):
        raise ValueError('output directory is not empty; choose a new run directory')
    for name in ('base', 'ours', 'upstream'):
        if not re.fullmatch(r'[0-9a-f]{40}', pin[name]):
            raise ValueError(f'{name} must be a full immutable commit SHA')
        _git(repo, 'cat-file', '-e', pin[name] + '^{commit}')
    base, ours, upstream = pin['base'], pin['ours'], pin['upstream']
    actual_base = _git(repo, 'merge-base', ours, upstream).stdout.decode().strip()
    if actual_base != base:
        raise ValueError(f'merge base changed: expected {base}, got {actual_base}')
    counts = [int(x) for x in _git(repo, 'rev-list', '--left-right', '--count', ours + '...' + upstream).stdout.split()]
    for key, actual in [('expected_ours_unique_commits', counts[0]), ('expected_upstream_unique_commits', counts[1])]:
        if key in pin and pin[key] != actual:
            raise ValueError(f'{key}: expected {pin[key]}, got {actual}')
    out.mkdir(parents=True, exist_ok=True)
    before_head = _git(repo, 'rev-parse', 'HEAD').stdout.decode().strip()
    before_status = _git(repo, 'status', '--porcelain=v1', '--untracked-files=all').stdout
    report = {'base': base, 'ours': ours, 'upstream': upstream, 'ours_unique_commits': counts[0],
              'upstream_unique_commits': counts[1], 'input_head': before_head,
              'input_dirty': bool(before_status), 'input_status': before_status.decode('utf-8', 'replace'),
              'git_version': _git(repo, '--version').stdout.decode().strip(), 'diffs': {}}
    for label, left, right in [('base-to-ours', base, ours), ('base-to-upstream', base, upstream), ('ours-to-upstream', ours, upstream)]:
        data = _git(repo, 'diff', '--no-ext-diff', '--no-renames', '--numstat', '-z', left, right).stdout
        files = []
        for record in data.split(b'\0'):
            if not record:
                continue
            added, deleted, path = record.split(b'\t', 2)
            files.append({'path': path.decode('utf-8'), 'additions': None if added == b'-' else int(added),
                          'deletions': None if deleted == b'-' else int(deleted), 'binary': added == b'-'})
        report['diffs'][label] = {'count': len(files), 'files': files}
        patch = _git(repo, 'diff', '--no-ext-diff', '--binary', left, right).stdout
        (out / (label + '.patch')).write_bytes(patch)
        dump_json(out / (label + '.json'), files)
    left_paths = {f['path'] for f in report['diffs']['base-to-ours']['files']}
    right_paths = {f['path'] for f in report['diffs']['base-to-upstream']['files']}
    shared = sorted(left_paths & right_paths)
    report['both_sides_touched'] = shared
    stage_map = []
    for index, path in enumerate(shared, 1):
        entry = {'path': path, 'stage_id': f'{index:03}', 'blobs': {}}
        for side, commit in [('base', base), ('ours', ours), ('upstream', upstream)]:
            r = _git(repo, 'show', commit + ':' + path, check=False)
            if r.returncode:
                entry['blobs'][side] = {'present': False}; continue
            file = out / 'shared-paths' / f'{index:03}' / (side + '.txt')
            file.parent.mkdir(parents=True, exist_ok=True); file.write_bytes(r.stdout)
            entry['blobs'][side] = {'present': True, 'file': str(file.relative_to(out)), 'sha256': sha256_file(file)}
        stage_map.append(entry)
    dump_json(out / 'shared-paths.json', stage_map)
    if merge_probe:
        with tempfile.TemporaryDirectory(prefix='ninfer-merge-probe-', dir=str(out.parent)) as scratch:
            target = Path(scratch) / 'repo'
            # Local clone only. No network, no pushes, no mutation of the caller's refs/index.
            _git(repo, 'clone', '--no-checkout', '--no-hardlinks', '--', str(repo), str(target))
            _git(target, 'checkout', '--detach', ours)
            r = _git(target, 'merge', '--no-commit', '--no-ff', '--strategy=ort', upstream, check=False)
            conflict_raw = _git(target, 'diff', '--name-only', '--diff-filter=U', '-z').stdout
            conflicts = [s.decode('utf-8') for s in conflict_raw.split(b'\0') if s]
            (out / 'merge-probe.txt').write_bytes(r.stdout + b'\nSTDERR:\n' + r.stderr)
            (out / 'unmerged-index.txt').write_bytes(_git(target, 'ls-files', '-u').stdout)
            if r.returncode not in (0, 1) or (r.returncode == 1 and not conflicts):
                raise RuntimeError('merge failed without a normal conflict; inspect merge-probe.txt')
            report['merge_probe'] = {'executed': True, 'returncode': r.returncode, 'conflict_files': conflicts,
                                     'scope': 'actual ort merge in a disposable local clone; no compile or GPU execution'}
    else:
        report['merge_probe'] = {'executed': False}
    after_head = _git(repo, 'rev-parse', 'HEAD').stdout.decode().strip()
    after_status = _git(repo, 'status', '--porcelain=v1', '--untracked-files=all').stdout
    if after_head != before_head or before_status != after_status:
        raise RuntimeError('source changed during audit; do not use this as a frozen-source report')
    report['source_head_and_status_unchanged'] = True
    dump_json(out / 'audit.json', report)
    return report


def check_phase(plan: dict, evidence: dict, root: Path) -> dict:
    errors: list[str] = []
    validate_dag(plan['tasks'])
    phase = evidence.get('phase')
    phases = {p['id']: p for p in plan['phases']}
    if phase not in phases:
        return {'passed': False, 'errors': ['unknown phase']}
    strict = plan.get('strict_evidence') is True
    expected = {t['id']: t for t in plan['tasks'] if t['phase'] == phase and t.get('kind') != 'gate'}
    rows = evidence.get('tasks', [])
    actual = {t['id']: t for t in rows}
    if len(actual) != len(rows) or set(actual) != set(expected):
        errors.append('task identities missing, duplicate, or unexpected')
    for task_id, task in expected.items():
        row = actual.get(task_id, {})
        if strict and not re.fullmatch('[0-9a-f]{40}', row.get('commit', '')):
            errors.append(task_id + ': missing immutable task commit')
        if row.get('status') == 'PASS':
            continue
        if row.get('status') == 'NOT_APPLICABLE' and task.get('optional') and row.get('disabled_feature') and row.get('reason'):
            continue
        errors.append(task_id + ': not passed')
    if not re.fullmatch('[0-9a-f]{40}', evidence.get('source_commit', '')):
        errors.append('missing immutable source commit')
    review = evidence.get('review', {})
    if review.get('status') != 'PASS' or not review.get('reviewer'):
        errors.append('unified review has not passed')
    if strict and review.get('reviewed_commit') != evidence.get('source_commit'):
        errors.append('reviewed commit does not match tested source commit')
    checks = evidence.get('checks', [])
    required_checks = {c['id']: c for c in phases[phase].get('required_checks', [])}
    if strict:
        check_ids = [c.get('id') for c in checks]
        if len(set(check_ids)) != len(check_ids) or None in check_ids:
            errors.append('missing or duplicate check identity')
        for required_id in required_checks:
            if required_id not in check_ids:
                errors.append('missing required check: ' + required_id)
    if not checks:
        errors.append('no recorded checks')
    resolved_root = root.resolve()
    for check in checks:
        spec = required_checks.get(check.get('id'), {})
        if strict and check.get('source_commit') != evidence.get('source_commit'):
            errors.append('check source commit mismatch: ' + str(check.get('id')))
        if strict and spec.get('kind') and check.get('kind') != spec['kind']:
            errors.append('required check kind mismatch: ' + str(check.get('id')))
        name = check.get('evidence', '')
        file = (root / name).resolve()
        if not name or not file.is_file() or resolved_root not in file.parents:
            errors.append('missing or unsafe evidence path: ' + str(name)); continue
        expected_hash = check.get('sha256')
        if not expected_hash or sha256_file(file) != expected_hash:
            errors.append('missing or wrong evidence hash: ' + name)
        if check.get('status') != 'PASS':
            errors.append('check not passed: ' + name)
        if check.get('kind') == 'junit':
            patterns = spec.get('required_patterns', []) if strict and spec else check.get('required_patterns', [])
            if not check_junit(file, patterns)['passed']:
                errors.append('JUnit required-test gate failed: ' + name)
    if phases[phase].get('gpu_required'):
        gpu = evidence.get('gpu', {})
        if gpu.get('executed') is not True or not gpu.get('uuid') or not gpu.get('model_sha256'):
            errors.append('mandatory GPU/model execution evidence absent')
        if strict and not re.fullmatch('[0-9a-f]{64}', gpu.get('model_sha256', '')):
            errors.append('invalid GPU model SHA256')
    if phase != 'P0':
        previous = f'P{int(phase[1:]) - 1}'
        previous_report = evidence.get('previous_gate')
        p = (root / str(previous_report or '')).resolve()
        if not previous_report or not p.is_file() or resolved_root not in p.parents:
            errors.append('previous phase gate report missing')
        else:
            g = json.loads(p.read_text())
            if g.get('phase') != previous or g.get('passed') is not True:
                errors.append('previous phase gate not passed')
    return {'phase': phase, 'source_commit': evidence.get('source_commit'), 'passed': not errors, 'errors': errors,
            'scope': 'evidence consistency checks; reviewer judgments and actual hardware execution still require raw logs'}
````
<!-- payload-end -->
