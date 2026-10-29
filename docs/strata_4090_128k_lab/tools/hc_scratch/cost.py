"""P23: one frozen100K A/C mechanism pair, after complete numerical/lifecycle/memcheck gates."""
from datetime import datetime, timezone
import argparse
import copy
import difflib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess

import memcheck
import cost_patch
from memcheck import boundary, lifecycle
from lab import http, scoring
from lab.assets import verify as verify_assets
from lab.core import check_budget, dump, gpu_inventory, gpu_lock, hash_obj, load_config, sha256
from lab.runner import make_run_config
from lab.tokenizer import StrataCounter
from boundary_memory import MemorySampler

ROOT = memcheck.ROOT
TASK = ROOT / 'workspace/combination/hc-cost-20261029'
TREE = ROOT / 'workspace/trees/hc-cost-20261029'
P13 = boundary.P13
SOURCE_FILES = ('src/prefill/prefill.cpp', 'src/program/generate.cpp')
CASE_SHA = '70bca1817c37adeacd59038f25b6a5d622efa3163497ee54b0719cddb3f9c563'
TOKEN_SHA = '89110d268d1dea535a776a4f5aba2178ec43780c3448deed2f3935bc6e59cac7'


def prepare_build():
    if TASK.exists() or TREE.exists(): raise RuntimeError('COST_STAGE_ALREADY_EXISTS')
    if json.loads((memcheck.TASK / 'lazy-async-frozen-cache/RUN_RESULT.json').read_text())['status'] != 'PASS':
        raise RuntimeError('FULL_MEMCHECK_NOT_PASS')
    receipt = json.loads((lifecycle.TASK / 'BUILD_COMPLETE.json').read_text())
    if sha256(lifecycle.TREE / 'build-lab/strata') != receipt['exe_sha256'] or any(
            sha256(lifecycle.TREE / n) != h for n, h in receipt['source'].items()):
        raise RuntimeError('P21_SOURCE_OR_BINARY_DRIFT')
    if sha256(lifecycle.TREE / 'build-lab/libstrata_prefill.a') != receipt['new_prefill_archive_sha256']:
        raise RuntimeError('P21_ARCHIVE_DRIFT')
    c = load_config(lifecycle.TASK / 'config.json')
    before = json.loads((lifecycle.TASK / 'production-before.json').read_text())
    boundary.reference.baseline.combo.assert_service_inactive()
    boundary.reference.baseline.combo.assert_protected(c, before['protected'])
    TASK.mkdir()
    dump(TASK / 'production-before.json', before)
    dump(TASK / 'ASSETS.json', {'metadata': verify_assets(c), 'fresh_full_model_content_hash': False})
    cases = json.loads((P13 / 'performance-cases.json').read_text())
    case = next(x for x in cases if x['id'] == 'think-102400')
    tokens = next(x for x in json.loads((P13 / 'tokens.json').read_text()) if x['name'] == case['id'])
    if (hash_obj(case['body']) != CASE_SHA or case['request_sha256'] != CASE_SHA or
            case['fixed_output'] != 2048 or tokens['count'] != 102400 or sha256(Path(tokens['path'])) != TOKEN_SHA):
        raise RuntimeError('FROZEN_P13_CASE_DRIFT')
    dump(TASK / 'case.json', dict(case=case, tokens=tokens))
    c['deployed_repo'] = str(TREE)
    expected = json.loads((lifecycle.TASK / 'memcheck/plan.json').read_text())
    c['extra_frozen_env'] = {k: v for k, v in expected['env'].items() if not k.startswith('STRATA_LAB_')}
    c['extra_frozen_env'].pop('STRATA_VERIFY_ASYNC_LAUNCH', None)
    c['request_timeout_s'] = 300; c['gpu_monitor_interval_s'] = 1
    dump(TASK / 'config.json', c)
    dump(TASK / 'PREREGISTRATION.json', {'registered_utc': datetime.now(timezone.utc).isoformat(),
        'authority': 'user: after full memcheck PASS proceed through cost and performance gates',
        'prerequisite': {'path': str(memcheck.TASK / 'lazy-async-frozen-cache/RUN_RESULT.json'),
                         'sha256': sha256(memcheck.TASK / 'lazy-async-frozen-cache/RUN_RESULT.json')},
        'scope': 'prefill expert transfers, resident routed hits, borrowed-slot refill and exposed copy wait; not all GPU transfers',
        'arms': ['A: original HC layout/loan', 'C: shared HC region/natural reduced loan'],
        'order': ['A', 'C'], 'fresh_engine_limit': 2, 'work_request_limit': 2, 'automatic_retries': 0,
        'body_sha256': CASE_SHA, 'token_file_sha256': TOKEN_SHA, 'input_tokens': 102400, 'fixed_output': 2048,
        'sampling': {k: case['body'][k] for k in ('temperature', 'top_p', 'top_k', 'seed')},
        'unchanged': 'P13 original args/auto cache10272/profile/int8 resident20480/MAX4096/AUTO16384; EAGER/default graph launch',
        'instrumentation': 'CPU-only cost counters/logs; reuse existing host route data, joins, CUDA sync and timer events',
        'coverage_gate': 'all actually computed FFN layers/chunks, valid counts only; fused/missing/ambiguous coverage blocks hit claims',
        'mechanism_gate': 'actual C-retained experts must be routed and remove real transfers or exposed wait; capacity alone is insufficient',
        'stop': 'first resource/config/request/coverage failure; no second100K pair; no performance before cost gate',
        'limits': {'gpu_c': 85, 'mem_available_mib': 4096, 'total_context': 131072, 'safety_tokens': 4096},
        'timings': 'diagnostic only; do not add overlapping host and GPU waits or treat cumulative copy time as critical path',
        'formal_performance_samples': 0, 'original_six_status': 'FAIL_UNCHANGED', 'production_writes': False})
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'sha256': sha256(TASK / 'PREREGISTRATION.json')})
    subprocess.run(['git', '-C', str(ROOT / 'workspace/repo'), 'worktree', 'add', '--detach', str(TREE),
                    '5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d'], check=True)
    for name in json.loads((P13 / 'P6_SOURCE.json').read_text())['python_port']['files']:
        shutil.copy2(lifecycle.TREE / name, TREE / name)
    for name, patch in zip(SOURCE_FILES, (cost_patch.prefill, cost_patch.program)):
        old = (lifecycle.TREE / name).read_text(); new = patch(old); (TREE / name).write_text(new)
        (TASK / (Path(name).stem + '.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
            fromfile='a/' + name, tofile='b/' + name)))
    base = boundary.TREE / 'build-lab'; out = TREE / 'build-lab'; out.mkdir()
    commands = json.loads((base / 'compile_commands.json').read_text()); compiled = []
    for source in SOURCE_FILES:
        entry = next(x for x in commands if x['file'].endswith('/' + source))
        argv = shlex.split(entry['command']); argv[argv.index('-o') + 1] = str(out / (Path(source).name + '.o'))
        argv[argv.index('-c') + 1] = str(TREE / source)
        with (TASK / (Path(source).stem + '-compile.log')).open('w') as log:
            subprocess.run(argv, cwd=entry['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
        compiled.append(argv)
    archive = out / 'libstrata_prefill.a'; shutil.copy2(lifecycle.TREE / 'build-lab/libstrata_prefill.a', archive)
    subprocess.run(['/usr/bin/ar', 'r', str(archive), str(out / 'prefill.cpp.o')], check=True)
    subprocess.run(['/usr/bin/ranlib', str(archive)], check=True)
    last = subprocess.check_output(['/home/hhtele/strata-0.1.43.1/.venv/bin/ninja', '-t', 'commands', 'strata'], cwd=base, text=True).splitlines()[-1]
    if not last.startswith(': && ') or not last.endswith(' && :'): raise RuntimeError('LINK_RULE_SHAPE')
    link = shlex.split(last[5:-5]); link[link.index('-o') + 1] = str(out / 'strata')
    link = [str(archive) if s == 'libstrata_prefill.a' else str(out / 'generate.cpp.o')
            if s == 'CMakeFiles/strata.dir/src/program/generate.cpp.o' else s for s in link]
    reused = {str((base / s).resolve()): sha256(base / s) for s in link if (base / s).is_file()
              and str((base / s).resolve()) not in (str(archive), str(out / 'generate.cpp.o'))}
    with (TASK / 'link.log').open('w') as log: subprocess.run(link, cwd=base, stdout=log, stderr=subprocess.STDOUT, check=True)
    dump(TASK / 'BUILD_COMPLETE.json', {'exe_sha256': sha256(out / 'strata'), 'compile_argv': compiled, 'link_argv': link,
        'source': {n: sha256(TREE / n) for n in SOURCE_FILES}, 'archive_sha256': sha256(archive),
        'reused_link_inputs': reused, 'patch_generator_sha256': sha256(Path(cost_patch.__file__))})
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    counter = StrataCounter(str(TREE), c['gguf'], c['template'])
    messages, tools, kwargs = counter.frontend.openai_to_messages(copy.deepcopy(case['body']))
    ids = counter.tokenizer.encode(counter.template.render(messages, tools=tools, **kwargs), parse_special=True)
    path = TASK / 'rendered.ids'; path.write_text(','.join(map(str, ids)) + '\n')
    if len(ids) != 102400 or sha256(path) != TOKEN_SHA: raise RuntimeError('RENDERED_TOKEN_STREAM_CHANGED')
    print('P23_PREREGISTERED_AND_BUILT_NO_GPU_REQUESTS', flush=True)


def run(arm):
    if arm == 'C' and json.loads((TASK / 'A/RUN_RESULT.json').read_text())['status'] != 'PASS':
        raise RuntimeError('A_TRACE_NOT_PASS')
    folder = TASK / arm; folder.mkdir()
    c = load_config(TASK / 'config.json')
    receipt = json.loads((TASK / 'BUILD_COMPLETE.json').read_text())
    if sha256(TREE / 'build-lab/strata') != receipt['exe_sha256'] or any(
            sha256(TREE / n) != h for n, h in receipt['source'].items()): raise RuntimeError('COST_BUILD_DRIFT')
    registration_receipt = json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())
    if sha256(TASK / 'PREREGISTRATION.json') != registration_receipt['sha256']:
        raise RuntimeError('REGISTRATION_DRIFT')
    validation_path = TASK / 'VALIDATION_ADDENDUM.json'
    if sha256(validation_path) != registration_receipt['validation_sha256']:
        raise RuntimeError('VALIDATION_REGISTRATION_DRIFT')
    validation = json.loads(validation_path.read_text())
    for name, expected_sha in validation['implementation'].items():
        if sha256(ROOT / name) != expected_sha: raise RuntimeError('VALIDATED_IMPLEMENTATION_DRIFT: ' + name)
    registration = json.loads((TASK / 'PREREGISTRATION.json').read_text())
    prerequisite = registration['prerequisite']
    if sha256(Path(prerequisite['path'])) != prerequisite['sha256']: raise RuntimeError('MEMCHECK_EVIDENCE_DRIFT')
    original = json.loads((TASK / 'case.json').read_text())
    case, tokens = original['case'], original['tokens']
    if hash_obj(case['body']) != CASE_SHA or sha256(Path(tokens['path'])) != TOKEN_SHA: raise RuntimeError('INPUT_DRIFT')
    c['extra_frozen_env'].update(STRATA_LAB_HC_REGION='1' if arm == 'C' else '0', STRATA_LAB_HC_KEEP_LOAN='0',
        STRATA_LAB_HC_MANIFEST='1', STRATA_LAB_BOUNDARY_TRACE='1', STRATA_LAB_HC_COST='1')
    cfg = make_run_config(c, TREE, 'cfg', {}, folder)
    expected = json.loads((lifecycle.TASK / 'memcheck/plan.json').read_text())
    if cfg['args'] != expected['args'] or {k: v for k, v in cfg['env'].items() if not k.startswith('STRATA_LAB_')} != {
            k: v for k, v in expected['env'].items() if not k.startswith('STRATA_LAB_')}:
        raise RuntimeError('ORIGINAL_CONFIGURATION_CHANGED')
    dump(folder / 'plan.json', {'arm': arm, 'args': cfg['args'], 'env': cfg['env'], 'body_sha256': CASE_SHA,
        'exe_sha256': receipt['exe_sha256'], 'registration_sha256': sha256(TASK / 'PREREGISTRATION.json'),
        'validation_sha256': sha256(validation_path),
        'formal_performance_sample': False, 'driver_sha256': sha256(Path(__file__))})
    before = json.loads((TASK / 'production-before.json').read_text())
    result = {'status': 'FAIL', 'error': None, 'work_requests': 0}
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1', CUDA_MODULE_LOADING='EAGER')
    os.environ.pop('CUDA_MODULE_DATA_LOADING', None)
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            boundary.reference.baseline.combo.assert_service_inactive()
            boundary.reference.baseline.combo.assert_protected(c, before['protected'])
            dump(folder / 'cooldown.json', boundary.reference.baseline.combo.wait_cool(c))
            with boundary.reference.baseline.combo.combination_server(c, TREE, 'cfg', {}, folder) as server:
                activation = boundary.reference.baseline.activation_receipt(server)
                if activation['expert_cache_slots'] != 10272: raise RuntimeError('ACTUAL_CACHE_CHANGED')
                dump(folder / 'activation.json', activation)
                for engine in server.engine_audit:
                    raw = (Path('/proc') / str(engine['pid']) / 'environ').read_bytes().split(b'\0')
                    if b'CUDA_MODULE_LOADING=EAGER' not in raw: raise RuntimeError('NATIVE_LOADING_NOT_EAGER')
                    if any(x.startswith((b'STRATA_LAB_ORACLE_DIR=', b'STRATA_DUMP_', b'STRATA_VERIFY_ASYNC_LAUNCH=1')) for x in raw):
                        raise RuntimeError('DIAGNOSTIC_CONTROL_LEAK')
                with MemorySampler(folder, lambda: boundary.reference.baseline.boundary.descendants(server)) as memory:
                    check_budget(102400, 2048, c['max_context'], c['safety_tokens'])
                    dump(folder / 'request.json', case['body'])
                    memory.stage = '100K'; memory.checkpoint('before-request')
                    offset = (folder / 'engine.log').stat().st_size
                    result['work_requests'] = 1; dump(folder / 'RUN_RESULT.json', result)
                    response = boundary.reference.baseline.boundary.exchange(server, case['body'], folder / '100K', timeout=300)
                    dump(folder / 'response.json', response)
                    log = (folder / 'engine.log').read_bytes()[offset:].decode(errors='replace')
                    (folder / 'request.engine.log').write_text(log)
                    metrics = http.measurements(response)
                    dump(folder / 'metrics.json', dict(metrics=metrics, score=scoring.score(case, response), diagnostic_only=True))
                    if response.get('error') or server.abort_reason or response.get('tools'):
                        raise RuntimeError('REQUEST_INFRASTRUCTURE: ' + str(response.get('error') or server.abort_reason))
                    boundary.reference.baseline.boundary.audit_usage(case['body'], response, 102400, c)
                    if metrics['reused_tokens'] != 0 or metrics['generated_tokens'] != 2048:
                        raise RuntimeError('COLD_FIXED_OUTPUT_CHANGED')
                    if any(x in log for x in ('P15_ORACLE ', 'P20_MANAGED_HC ', 'P21_REQUEST ')):
                        raise RuntimeError('OLD_DIAGNOSTICS_ENABLED')
                    boundary.reference.baseline.boundary.wait_idle(server, folder, '100K')
                    memory.checkpoint('after-request')
                    # Coverage is checked from the complete narrow cost log before another arm is allowed.
                    import cost_analysis
                    dump(folder / 'COVERAGE.json', cost_analysis.validate_arm(folder, arm))
        result['status'] = 'PASS'
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        dump(folder / 'RUN_RESULT.json', result)
        dump(folder / 'production-after.json', {'service': boundary.reference.baseline.combo.assert_service_inactive(),
            'protected': boundary.reference.baseline.combo.assert_protected(c, before['protected']), 'gpu': gpu_inventory('0')})
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['prepare-build', 'A', 'C'])
    a = p.parse_args()
    if a.mode == 'prepare-build': prepare_build()
    elif run(a.mode)['status'] != 'PASS': raise SystemExit(2)
