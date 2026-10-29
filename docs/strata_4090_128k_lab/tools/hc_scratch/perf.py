"""P24 frozen HC-only paired performance; diagnostic P23 rows never enter these statistics."""
import argparse
import copy
from datetime import datetime, timezone
import itertools
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

import cost
from cost import boundary, lifecycle
from boundary_memory import MemorySampler
from lab import http, scoring
from lab.assets import verify as verify_assets
from lab.core import check_budget, dump, gpu_inventory, gpu_lock, hash_obj, load_config, port_free, sha256
from lab.runner import make_run_config
from lab.statistics import percentile
from lab.tokenizer import StrataCounter

ROOT, P13 = cost.ROOT, cost.P13
TASK = ROOT / 'workspace/combination/hc-perf-20261029'
TREE = ROOT / 'workspace/trees/hc-scratch-20261028'
ORDERS = [('A', 'C'), ('C', 'A'), ('C', 'A'), ('A', 'C'), ('A', 'C'), ('C', 'A')]
TIMING = ('STRATA_PREFILL_TIMING', 'STRATA_DECODE_TIMING')


def schedule():
    rows = []
    for group, orders in [('100K', ORDERS), ('4K', [('A', 'C'), ('C', 'A')]),
                          ('append', [('A', 'C'), ('C', 'A')])]:
        for pair, order in enumerate(orders):
            for arm in order: rows.append(dict(index=len(rows), group=group, pair=pair, arm=arm))
    return rows


def paired_exact(a, c):
    if len(a) != 6 or len(c) != 6 or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in a + c):
        raise ValueError('SIX_POSITIVE_FINITE_PAIRED_TIMES_REQUIRED')
    logs = [math.log(y / x) for x, y in zip(a, c)]
    ratios = sorted(math.exp(sum(draw) / 6) for draw in itertools.product(logs, repeat=6))
    estimate = math.exp(statistics.mean(logs))
    lo, hi = percentile(ratios, .025), percentile(ratios, .975)
    return {'pairs': 6, 'ratio_C_over_A': estimate, 'ratio_ci95': [lo, hi],
            'improvement_pct': 100 * (1 - estimate), 'improvement_ci95': [100 * (1 - hi), 100 * (1 - lo)],
            'bootstrap_draws': 6 ** 6, 'unit': 'entire fresh-engine paired round; exhaustive log-ratio bootstrap'}


def analyze(task):
    task = Path(task); planned = schedule(); rows = []
    cases = json.loads((task / 'cases.json').read_text())
    appends = json.loads((task / 'append.json').read_text())
    expected = {'100K': [next(x for x in cases if x['id'] == 'think-102400')],
                '4K': [next(x for x in cases if x['id'] == 'think-4096')],
                'append': [x['case'] for x in appends]}
    def audit(row):
        folder = task / f"{row['index']:02d}-{row['group']}-{row['arm']}"
        run = json.loads((folder / 'RUN_RESULT.json').read_text())
        if run['status'] != 'PASS' or run['identity'] != row:
            raise RuntimeError('FAILED_OR_CHANGED_FORMAL_SAMPLE: ' + folder.name)
        requests = json.loads((folder / 'RESULTS.json').read_text())
        if len(requests) != (2 if row['group'] == 'append' else 1) or any(r['score']['pass'] is not True for r in requests):
            raise RuntimeError('MISSING_OR_FAILED_FORMAL_REQUEST: ' + folder.name)
        for request, case in zip(requests, expected[row['group']]):
            m = request['metrics']
            if (request['id'] != case['id'] or request['request_sha256'] != case['request_sha256'] or
                    m['prompt_tokens'] != case['counted_prompt_tokens']):
                raise RuntimeError('FORMAL_REQUEST_IDENTITY_CHANGED')
            if row['group'] != 'append' and (m['generated_tokens'] != 2048 or m['reused_tokens'] != 0):
                raise RuntimeError('FORMAL_LENGTH_OR_COLD_STATE_CHANGED')
            if row['group'] == 'append' and request['id'] == 'append-0' and not (
                    m['reused_tokens'] >= 32000 and 3000 <= m['read_tokens'] <= 3500):
                raise RuntimeError('FORMAL_APPEND_STATE_CHANGED')
        return dict(row, requests=requests)
    invalid_support = []
    for row in planned:
        if row['group'] == '100K':
            rows.append(audit(row))
        else:
            try:
                rows.append(audit(row))
            except (FileNotFoundError, RuntimeError) as error:
                invalid_support.append({'identity': row, 'error': str(error)})
    primary = {}
    for metric in ('ttft_s', 'wall_s', 'decode_ms'):
        values = {arm: [next(r for r in rows if r['group'] == '100K' and r['pair'] == pair and r['arm'] == arm)
                        ['requests'][0]['metrics'][metric] for pair in range(6)] for arm in ('A', 'C')}
        primary[metric] = paired_exact(values['A'], values['C'])
    t = primary['ttft_s']
    ttft_pass = t['improvement_pct'] >= 4 and t['improvement_ci95'][0] > 0
    noninferior = all(primary[m]['ratio_ci95'][1] <= 1.02 for m in ('wall_s', 'decode_ms'))
    return {'status': 'INCOMPLETE_OR_INVALID' if invalid_support else
        'PASS_PERFORMANCE_SCREEN' if ttft_pass and noninferior else 'PERFORMANCE_GATE_NOT_MET',
        'primary': primary, 'TTFT_gate_pass': ttft_pass, 'wall_and_full_decode_noninferiority_pass': noninferior,
        'engines': len(rows), 'work_requests': sum(len(r['requests']) for r in rows),
        'counts_scope': 'validated complete runs; failed or missing support samples listed separately',
        'invalid_support_samples': invalid_support, 'expected_engines': 20, 'expected_work_requests': 24,
        'support_descriptive_only': [r for r in rows if r['group'] != '100K'],
        'formal_rows': rows, 'original_six_status': 'FAIL_UNCHANGED', 'adoption': 'NOT_PASSED_SEPARATE_TASK_QUALITY_GATE'}


def source_identity():
    receipt = json.loads((P13 / 'BUILD_COMPLETE.json').read_text())
    files = json.loads((P13 / 'P6_SOURCE.json').read_text())['python_port']['files']
    expected = {**files, 'src/prefill/prefill.cpp': receipt['patch']['after_sha256']}
    for name, digest in expected.items():
        if sha256(TREE / name) != digest: raise RuntimeError('PLAIN_HC_SOURCE_DRIFT: ' + name)
    if sha256(TREE / 'build-lab/strata') != receipt['exe_sha256']: raise RuntimeError('PLAIN_HC_BINARY_DRIFT')
    program = TREE / 'src/program/generate.cpp'
    frozen = subprocess.check_output(['git', '-C', str(TREE), 'show', receipt['source_sha'] + ':src/program/generate.cpp'])
    if program.read_bytes() != frozen: raise RuntimeError('PLAIN_HC_PROGRAM_DRIFT')
    return {'exe_sha256': receipt['exe_sha256'], 'source': expected, 'program_sha256': sha256(program)}


def configuration(c, folder, arm):
    original = json.loads(Path(c['deployed_config']).read_text())
    remove = {k: None for k in set(original.get('env', {})) | set(c['extra_frozen_env'])
              if k.startswith('STRATA_LAB_') or k in TIMING}
    ready = {'common': {'env': dict(remove, STRATA_LAB_HC_REGION='1' if arm == 'C' else '0', STRATA_LAB_HC_KEEP_LOAN='0')}}
    cfg = make_run_config(c, TREE, 'cfg', ready, folder)
    expected = json.loads((lifecycle.TASK / 'memcheck/plan.json').read_text())
    plain = lambda env: {k: v for k, v in env.items() if not k.startswith('STRATA_LAB_') and k not in TIMING}
    if cfg['args'] != expected['args'] or plain(cfg['env']) != plain(expected['env']):
        raise RuntimeError('FROZEN_FORMAL_CONFIGURATION_CHANGED')
    return ready, cfg


def prepare():
    if TASK.exists(): raise RuntimeError('FORMAL_TASK_ALREADY_EXISTS')
    signal = json.loads((cost.TASK / 'ANALYSIS.json').read_text())
    if signal['status'] != 'PASS_MECHANISM_SIGNAL': raise RuntimeError('COST_GATE_NOT_PASS')
    # Recheck the complete retained-ID/copy chain, not just its saved status.
    import cost_analysis
    if cost_analysis.compare(cost.TASK) != signal: raise RuntimeError('COST_SIGNAL_DRIFT')
    source = source_identity()
    c = load_config(P13 / 'config.json'); c['deployed_repo'] = str(TREE)
    c['gpu_monitor_interval_s'] = 1; c['request_timeout_s'] = 300
    before = json.loads((cost.TASK / 'production-before.json').read_text())
    boundary.reference.baseline.combo.assert_service_inactive()
    boundary.reference.baseline.combo.assert_protected(c, before['protected'])
    port_free(18089)
    if gpu_inventory('0')['compute_processes']: raise RuntimeError('GPU_NOT_FREE')
    cases = json.loads((P13 / 'performance-cases.json').read_text())
    append = json.loads((P13 / 'append-cases.json').read_text())
    reg = json.loads((P13 / 'PREREGISTRATION.json').read_text())
    if any(sha256(P13 / n) != reg['inputs'][key] for n, key in [('performance-cases.json', 'performance_sha256'), ('append-cases.json', 'append_sha256')]):
        raise RuntimeError('FROZEN_CASE_FILES_CHANGED')
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    counter = StrataCounter(str(TREE), c['gguf'], c['template'])
    counts = {}
    for case in cases + [dict(x['case'], body=x['request']) for x in append]:
        if hash_obj(case['body']) != case['request_sha256']: raise RuntimeError('FROZEN_REQUEST_HASH_CHANGED')
        count = counter(copy.deepcopy(case['body']))
        if count != case['counted_prompt_tokens']: raise RuntimeError('FROZEN_TOKEN_COUNT_CHANGED')
        counts[case['id']] = count
    TASK.mkdir(); dump(TASK / 'config.json', c); dump(TASK / 'production-before.json', before)
    dump(TASK / 'ASSETS.json', {'metadata': verify_assets(c), 'fresh_full_model_content_hash': False})
    dump(TASK / 'cases.json', cases); dump(TASK / 'append.json', append)
    dump(TASK / 'PREREGISTRATION.json', {'registered_utc': datetime.now(timezone.utc).isoformat(),
        'authority': 'user staged cost/performance authorization; P22 and P23 gates PASS', 'source': source,
        'cost_analysis_sha256': sha256(cost.TASK / 'ANALYSIS.json'), 'P13_preregistration_sha256': sha256(P13 / 'PREREGISTRATION.json'),
        'schedule': schedule(), 'fresh_engine_limit': 20, 'work_request_limit': 24, 'short_qualification_requests': 0,
        'cases_sha256': sha256(TASK / 'cases.json'), 'append_sha256': sha256(TASK / 'append.json'), 'token_counts': counts,
        'deployed_config_sha256': sha256(Path(c['deployed_config'])), 'implementation_sha256': sha256(Path(__file__)),
        'primary': reg['primary'], 'noninferiority': reg['noninferiority'], 'statistics': reg['statistics'],
        'measurement': reg['measurement'], 'loading': 'EAGER; original auto10272 cache, default graph launch',
        'timed_controls': 'plain P13 HC binary; only HC_REGION0/1 and KEEP_LOAN0; remove prefill/decode timing env entirely',
        'append_coverage': 'strict frozen ACK/1730 scoring; prime cold, append actual reused>=32000/read3000..3500',
        'stop': 'first config/resource/request/quality/coverage failure; retain incomplete rows; no replacement or automatic retry',
        'limits': reg['limits'], 'original_six_status': 'FAIL_UNCHANGED', 'adoption': 'separate task-quality gate remains unpassed'})
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'sha256': sha256(TASK / 'PREREGISTRATION.json')})
    print('P24_REGISTERED_NO_GPU_REQUESTS', flush=True)


class PerfSampler(MemorySampler):
    def sample(self, full=False):
        row = super().sample(full)
        fields = ['clocks.sm', 'clocks.mem', 'temperature.gpu', 'power.draw', 'memory.used', 'pstate']
        values = subprocess.check_output(['nvidia-smi', '-i', '0', '--query-gpu=' + ','.join(fields),
                                          '--format=csv,noheader,nounits'], text=True, timeout=10).strip().split(',')
        if len(values) != len(fields): raise RuntimeError('GPU_CLOCK_SAMPLE_INVALID')
        row['gpu_clocks'] = dict(zip(fields, [v.strip() for v in values])); row['capture_finished_ts'] = time.time()
        return row


def run(index):
    row = schedule()[index]
    for previous in schedule()[:index]:
        f = TASK / f"{previous['index']:02d}-{previous['group']}-{previous['arm']}/RUN_RESULT.json"
        if json.loads(f.read_text())['status'] != 'PASS': raise RuntimeError('PREVIOUS_FORMAL_RUN_NOT_PASS')
    folder = TASK / f"{index:02d}-{row['group']}-{row['arm']}"; folder.mkdir()
    reg = json.loads((TASK / 'PREREGISTRATION.json').read_text())
    if (sha256(TASK / 'PREREGISTRATION.json') != json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())['sha256'] or
            sha256(Path(__file__)) != reg['implementation_sha256'] or source_identity() != reg['source'] or
            sha256(cost.TASK / 'ANALYSIS.json') != reg['cost_analysis_sha256']): raise RuntimeError('FORMAL_REGISTRATION_OR_SOURCE_DRIFT')
    c = load_config(TASK / 'config.json')
    if sha256(Path(c['deployed_config'])) != reg['deployed_config_sha256']: raise RuntimeError('DEPLOYED_INPUT_CONFIG_DRIFT')
    for name, key in [('cases.json', 'cases_sha256'), ('append.json', 'append_sha256')]:
        if sha256(TASK / name) != reg[key]: raise RuntimeError('FORMAL_INPUT_DRIFT')
    cases = json.loads((TASK / 'cases.json').read_text())
    selected = ([next(x for x in cases if x['id'] == ('think-102400' if row['group'] == '100K' else 'think-4096'))]
                if row['group'] != 'append' else [dict(x['case'], body=x['request']) for x in json.loads((TASK / 'append.json').read_text())])
    ready, cfg = configuration(c, folder, row['arm'])
    dump(folder / 'plan.json', {'identity': row, 'args': cfg['args'], 'env': cfg['env'],
        'registration_sha256': sha256(TASK / 'PREREGISTRATION.json'), 'exe_sha256': reg['source']['exe_sha256'],
        'case_sha256': [hash_obj(x['body']) for x in selected]})
    before = json.loads((TASK / 'production-before.json').read_text()); results = []
    result = {'status': 'FAIL', 'identity': row, 'engine_startups': 0, 'work_requests': 0, 'error': None}
    dump(folder / 'RUN_RESULT.json', result)
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1', CUDA_MODULE_LOADING='EAGER')
    os.environ.pop('CUDA_MODULE_DATA_LOADING', None)
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            boundary.reference.baseline.combo.assert_service_inactive()
            boundary.reference.baseline.combo.assert_protected(c, before['protected'])
            dump(folder / 'cooldown.json', boundary.reference.baseline.combo.wait_cool(c))
            result['engine_startups'] = 1; dump(folder / 'RUN_RESULT.json', result)
            with boundary.reference.baseline.combo.combination_server(c, TREE, 'cfg', ready, folder) as server:
                activation = boundary.reference.baseline.activation_receipt(server)
                if activation['expert_cache_slots'] != 10272: raise RuntimeError('FORMAL_CACHE_CHANGED')
                dump(folder / 'activation.json', activation)
                for engine in server.engine_audit:
                    native_env = dict(x.decode().split('=', 1) for x in (Path('/proc') / str(engine['pid']) / 'environ').read_bytes().split(b'\0') if b'=' in x)
                    if native_env.get('CUDA_MODULE_LOADING') != 'EAGER' or any(k in native_env for k in TIMING):
                        raise RuntimeError('FORMAL_TIMING_OR_LOADING_DRIFT')
                    if {k: v for k, v in native_env.items() if k.startswith('STRATA_LAB_')} != {
                            'STRATA_LAB_HC_REGION': '1' if row['arm'] == 'C' else '0', 'STRATA_LAB_HC_KEEP_LOAN': '0'}:
                        raise RuntimeError('FORMAL_DIAGNOSTIC_CONTROLS_PRESENT')
                    if any(k.startswith(('STRATA_DUMP', 'STRATA_DBG')) for k in native_env) or native_env.get('STRATA_VERIFY_ASYNC_LAUNCH') == '1':
                        raise RuntimeError('FORMAL_DUMP_OR_LAUNCH_CONTROL_PRESENT')
                with PerfSampler(folder, lambda: boundary.reference.baseline.boundary.descendants(server)) as memory:
                    for case in selected:
                        count = reg['token_counts'][case['id']]
                        check_budget(count, case['body']['max_tokens'], c['max_context'], c['safety_tokens'])
                        memory.checkpoint(case['id'] + '-before')
                        dump(folder / (case['id'] + '.request.json'), case['body'])
                        result['work_requests'] += 1; dump(folder / 'RUN_RESULT.json', result)
                        response = boundary.reference.baseline.boundary.exchange(server, case['body'], folder / case['id'], timeout=300)
                        dump(folder / (case['id'] + '.response.json'), response)
                        m, score = http.measurements(response), scoring.score(case, response)
                        results.append({'id': case['id'], 'request_sha256': hash_obj(case['body']), 'metrics': m, 'score': score})
                        dump(folder / 'RESULTS.json', results)
                        if response.get('error') or server.abort_reason or score['pass'] is not True:
                            raise RuntimeError('FORMAL_REQUEST_FAILED: ' + str(response.get('error') or server.abort_reason or score))
                        boundary.reference.baseline.boundary.audit_usage(case['body'], response, count, c)
                        if row['group'] != 'append' and (m['generated_tokens'] != 2048 or m['reused_tokens'] != 0 or m['read_tokens'] != count):
                            raise RuntimeError('FORMAL_LENGTH_OR_COLD_STATE_CHANGED')
                        if row['group'] == 'append':
                            if case['id'] == 'append-prime' and m['reused_tokens'] != 0: raise RuntimeError('APPEND_PRIME_NOT_COLD')
                            if case['id'] == 'append-0' and not (m['reused_tokens'] >= 32000 and 3000 <= m['read_tokens'] <= 3500):
                                raise RuntimeError('ACTUAL_32K_TO_3K_APPEND_NOT_CONFIRMED')
                        if any(type(m[k]) not in (int, float) or not math.isfinite(m[k]) or m[k] <= 0 for k in ('wall_s', 'ttft_s', 'decode_ms')):
                            raise RuntimeError('FORMAL_TIME_NOT_AUDITABLE')
                        boundary.reference.baseline.boundary.wait_idle(server, folder, case['id'])
                        memory.checkpoint(case['id'] + '-after')
            if server.abort_reason: raise RuntimeError(server.abort_reason)
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = str(error)
    finally:
        dump(folder / 'RUN_RESULT.json', result)
        dump(folder / 'production-after.json', {'service': boundary.reference.baseline.combo.assert_service_inactive(),
            'protected': boundary.reference.baseline.combo.assert_protected(c, before['protected']), 'gpu': gpu_inventory('0')})
    print(json.dumps(dict(result, metrics=[r['metrics'] for r in results])), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['prepare', 'run', 'analyze']); p.add_argument('--index', type=int)
    a = p.parse_args()
    if a.mode == 'prepare': prepare()
    elif a.mode == 'run':
        if a.index is None or not 0 <= a.index < 20: p.error('--index must be 0..19')
        if run(a.index)['status'] != 'PASS': raise SystemExit(2)
    else:
        result = analyze(TASK); dump(TASK / 'ANALYSIS.json', result)
        print(json.dumps({k: result[k] for k in ('status', 'TTFT_gate_pass', 'wall_and_full_decode_noninferiority_pass', 'engines', 'work_requests')}))
