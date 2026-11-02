"""Bounded A0/P6 frozen-failure replay; production lifecycle is external."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/combination'), str(Path(__file__).parent)]
import run_baseline as baseline
from lab.assets import verify
from lab.core import check_budget, dump, gpu_lock, hash_obj, load_config, sha256
from lab.runner import make_run_config
from lab.tokenizer import StrataCounter

ORDER = [('A', 'B'), ('B', 'A'), ('A', 'B')]
BINARIES = {'A': '819ff262a1742e8b57eedc6203b015f7c9831dd4a94ecacbb5a8b1c865fade3d',
            'B': '58ffaf7f67535049baf996dd8793202b2ba4d2d7090569cfcc13019a28269f22'}


def inputs(root, arm):
    task = root / 'workspace/combination' / ('kvres-20261027' if arm == 'A' else 'v027-20261028')
    c = load_config(task / 'config.json')
    c['extra_frozen_env'] = {**c['extra_frozen_env'], **baseline.CONSERVATIVE}
    tree = Path(c['deployed_repo'])
    verify(c)
    if arm == 'A':
        baseline.combo.validate_tree(tree)
    else:
        baseline.source_receipt(tree, task)
    if sha256(tree / 'build-lab/strata') != BINARIES[arm]:
        raise RuntimeError('BASELINE_BINARY_DRIFT')
    _, boolean, _, coding = baseline.frozen_failures(root / 'workspace/combination/kvres-20261027')
    return c, tree, boolean, coding


def config_receipt(c, tree, folder):
    cfg = make_run_config(c, tree, 'cfg', {}, folder)
    baseline.assert_kvres(cfg)
    for key, value in {**baseline.combo.FROZEN_ENV, **baseline.CONSERVATIVE}.items():
        if cfg['env'].get(key) != value:
            raise RuntimeError('FROZEN_ENV_DRIFT: ' + key)
    if 'STRATA_VERIFY_PROFILE' in cfg['env'] or any(k.startswith('STRATA_LAB_') for k in cfg['env']):
        raise RuntimeError('DIAGNOSTIC_ENV_FORBIDDEN')
    for key in ('exe', 'cwd', 'log', 'api_key'):
        cfg.pop(key, None)
    return cfg


def make_counter(c, tree, runtime):
    """Keep the worker's CPU renderer on the actual server's history defaults."""
    for key in ('STRATA_REPLY_REUSE', 'STRATA_PRESERVE_THINKING'):
        os.environ[key] = runtime['env'][key]
    return StrataCounter(tree, c['gguf'], c['template'])


def count_inputs(root, out, arm):
    # This command runs in a fresh process per version: frontend imports cannot
    # accidentally carry over from the other Strata source tree.
    c, tree, boolean, coding = inputs(root, arm)
    runtime = config_receipt(c, tree, out / arm)
    counter = make_counter(c, tree, runtime)
    counts = [counter(body) for body in (boolean['body'], coding)]
    for body, count in zip((boolean['body'], coding), counts):
        check_budget(count, body['max_tokens'], c['max_context'], c['safety_tokens'])
    explicit_false = copy.deepcopy(coding)
    explicit_false.setdefault('chat_template_kwargs', {})['preserve_thinking'] = False
    explicit_true = copy.deepcopy(coding)
    explicit_true.setdefault('chat_template_kwargs', {})['preserve_thinking'] = True
    false_count, true_count = counter(explicit_false), counter(explicit_true)
    if counts[1] != false_count or true_count <= false_count:
        raise RuntimeError('CPU_PT0_COUNTER_REGRESSION')
    # Exact regression case observed in U01; no generated request is sent here.
    if counts[1] != 4408:
        raise RuntimeError('FROZEN_CODING_COUNT_DRIFT')
    return {'arm': arm, 'prompt_counts': counts, 'coding_explicit_false': false_count,
            'coding_explicit_true': true_count, 'cpu_only': True,
            'request_hashes': [hash_obj(boolean['body']), hash_obj(coding)]}


def prepare(root, out):
    out.mkdir(parents=True, exist_ok=False)
    configs = {}
    identities = {}
    request_hashes = {}
    cpu_receipts = {}
    for arm in ('A', 'B'):
        c, tree, boolean, coding = inputs(root, arm)
        configs[arm] = config_receipt(c, tree, out / arm)
        identities[arm] = {'tree': str(tree), 'binary_sha256': BINARIES[arm],
                           'config_sha256': sha256(Path(c['deployed_config'])),
                           'assets_receipt_sha256': sha256(Path(c['workspace']) / 'assets.json')}
        request_hashes[arm] = [hash_obj(boolean['body']), hash_obj(coding)]
        raw = subprocess.check_output([sys.executable, '-B', __file__, 'count', '--root', str(root),
                                       '--out', str(out), '--arm', arm], text=True)
        cpu_receipts[arm] = json.loads(raw)
    if configs['A'] != configs['B'] or request_hashes['A'] != request_hashes['B']:
        raise RuntimeError('UNDECLARED_ARM_DIFFERENCE')
    image = subprocess.check_output(['docker', 'image', 'inspect', '--format={{.Id}}', baseline.IMAGE], text=True).strip()
    if image != baseline.IMAGE:
        raise RuntimeError('GRADING_IMAGE_DRIFT')
    # One immutable record precedes production shutdown and every generated request.
    plan = {'id': 'U01-VERSION-COMPARISON-20261031', 'run_id': out.name, 'created_ts': time.time(),
            'deadline_epoch': time.time() + 14400, 'order': ORDER, 'max_engines': 6,
            'max_requests': 12, 'requests_per_engine': ['schema-boolean', 'seed43-final-original'],
            'request_hashes': request_hashes['A'], 'identities': identities, 'cpu_preflight': cpu_receipts,
            'normalized_runtime_sha256': hash_obj(configs['A']), 'image': image,
            'driver_sha256': sha256(Path(__file__)), 'protected_sha256': baseline.combo.protected_hashes(c),
            'quality_failure_policy': 'retain and continue paired arms; no replacement',
            'infrastructure_failure_policy': 'abort; remaining requests NOT_RUN',
            'scope': 'three repeats of two frozen cases; descriptive only, not independent task NI',
            'production_final_state': 'restore original v0.2.3 service; no deployment'}
    # Pin the shared harness and graders as well as the arm binaries.
    plan['harness_sha256'] = {str(p.relative_to(root)): sha256(p) for base in
        (root / 'lab', root / 'tools/combination', root / 'tools/session', root / 'tools/v027')
        for p in base.glob('*.py')}
    dump(out / 'PREREGISTRATION.json', plan)
    dump(out / 'CONFIG_CONTRACT.json', configs['A'])
    dump(out / 'STATE.json', {'state': 'PREPARED', 'http_attempts': 0})
    print(json.dumps({'state': 'PREPARED', 'request_hashes': plan['request_hashes']}), flush=True)


def deadline_signal(*_):
    raise TimeoutError('CAMPAIGN_OR_WORKER_DEADLINE')


def worker(root, out, arm, group):
    plan = json.loads((out / 'PREREGISTRATION.json').read_text())
    c, tree, boolean, coding = inputs(root, arm)
    folder = out / f'group-{group}-{arm}'
    if folder.exists():
        raise RuntimeError('WORKER_REPLAY_FORBIDDEN')
    folder.mkdir()
    if hash_obj(config_receipt(c, tree, folder)) != plan['normalized_runtime_sha256']:
        raise RuntimeError('CONFIG_CONTRACT_DRIFT')
    if [hash_obj(boolean['body']), hash_obj(coding)] != plan['request_hashes']:
        raise RuntimeError('REQUEST_DRIFT')
    if sha256(Path(__file__)) != plan['driver_sha256']:
        raise RuntimeError('DRIVER_DRIFT')
    for name, digest in plan['harness_sha256'].items():
        if sha256(root / name) != digest:
            raise RuntimeError('HARNESS_DRIFT: ' + name)
    baseline.combo.assert_service_inactive()
    baseline.combo.assert_protected(c, plan['protected_sha256'])
    signal.signal(signal.SIGALRM, deadline_signal)
    signal.signal(signal.SIGTERM, deadline_signal)
    signal.alarm(max(1, int(min(2100, plan['deadline_epoch'] - time.time() - 300))))
    rows = []
    error = None
    try:
        baseline.combo.wait_cool(c)
        with baseline.combo.combination_server(c, tree, 'cfg', {}, folder) as server:
            dump(folder / 'activation.json', baseline.activation_receipt(server))
            pid = server.engine_audit[0]['pid']
            env = dict(item.decode().split('=', 1) for item in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if item.startswith(b'STRATA_'))
            if env != server.cfg['env']:
                raise RuntimeError('LIVE_STRATA_ENV_DRIFT')
            dump(folder / 'actual-strata-env.json', env)
            counter = make_counter(c, tree, server.cfg)
            if [counter(boolean['body']), counter(coding)] != plan['cpu_preflight'][arm]['prompt_counts']:
                raise RuntimeError('WORKER_COUNTER_PREFLIGHT_DRIFT')
            with baseline.MemorySampler(folder, lambda: baseline.boundary.descendants(server)) as memory:
                replay = baseline.Replay(c, server, counter, folder, memory)
                rows = replay.rows
                for index, (name, body, case, turn) in enumerate([
                        ('schema-boolean', boolean['body'], boolean, None),
                        ('seed43-final-original', coding, None, 8)]):
                    check_budget(counter(body), body['max_tokens'], c['max_context'], c['safety_tokens'])
                    # Durable attempts include failed exchanges and grader failures.
                    dump(folder / f'attempt-{index}.json', {'name': name, 'request_sha256': hash_obj(body), 'started_ts': time.time()})
                    replay.request(name, copy.deepcopy(body), case, chain_turn=turn, frozen_hash=hash_obj(body))
    except BaseException as exc:
        error = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        signal.alarm(0)
        dump(folder / 'RESULT.json', {'arm': arm, 'group': group, 'rows': rows, 'error': error})
        baseline.combo.assert_protected(c, plan['protected_sha256'])


def run(root, out):
    plan = json.loads((out / 'PREREGISTRATION.json').read_text())
    state = json.loads((out / 'STATE.json').read_text())
    if state['state'] != 'PREPARED':
        raise RuntimeError('CAMPAIGN_REPLAY_FORBIDDEN')
    c, _, _, _ = inputs(root, 'A')
    dump(out / 'STATE.json', {'state': 'RUNNING', 'started_ts': time.time()})
    error = None
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            for group, arms in enumerate(ORDER, 1):
                for arm in arms:
                    if time.time() >= plan['deadline_epoch'] - 1800:
                        raise TimeoutError('INSUFFICIENT_REMAINING_BUDGET')
                    print(json.dumps({'group': group, 'arm': arm, 'state': 'STARTING'}), flush=True)
                    with (out / f'group-{group}-{arm}.stdout.log').open('x') as log:
                        result = subprocess.run([sys.executable, '-B', __file__, 'worker', '--root', str(root), '--out', str(out), '--arm', arm, '--group', str(group)], stdout=log, stderr=subprocess.STDOUT)
                    if result.returncode:
                        raise RuntimeError(f'WORKER_FAILED group={group} arm={arm} rc={result.returncode}')
                    print(json.dumps({'group': group, 'arm': arm, 'state': 'COMPLETE'}), flush=True)
    except BaseException as exc:
        error = f'{type(exc).__name__}: {exc}'
    finally:
        baseline.combo.assert_protected(c, plan['protected_sha256'])
        attempts = list(out.glob('group-*/attempt-*.json'))
        results = [json.loads(p.read_text()) for p in sorted(out.glob('group-*/RESULT.json'))]
        dump(out / 'SUMMARY.json', {'state': 'COMPLETE' if error is None else 'INCOMPLETE', 'error': error,
             'http_attempts': len(attempts), 'planned_requests': 12, 'not_run': 12 - len(attempts), 'results': results,
             'formal_quality_noninferiority': 'NOT_ESTABLISHED'})
        dump(out / 'STATE.json', {'state': 'CLOSED', 'http_attempts': len(attempts), 'error': error})
    return 0 if error is None else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['prepare', 'run', 'worker', 'count'])
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--arm', choices=['A', 'B'])
    p.add_argument('--group', type=int, choices=[1, 2, 3])
    a = p.parse_args()
    if a.mode == 'prepare':
        prepare(a.root, a.out)
    elif a.mode == 'count':
        if not a.arm:
            p.error('count requires arm')
        print(json.dumps(count_inputs(a.root, a.out, a.arm)))
    elif a.mode == 'worker':
        if not a.arm or not a.group:
            p.error('worker requires arm and group')
        worker(a.root, a.out, a.arm, a.group)
    else:
        raise SystemExit(run(a.root, a.out))
