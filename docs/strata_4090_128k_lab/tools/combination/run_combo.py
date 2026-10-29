"""Frozen HTTP replay of the deployed combination, with KVRES as the only factor.

Both arms use the same isolated Python tree and native executable.  This driver
never starts/stops production and refuses to run while production is active.
"""
from __future__ import annotations

import argparse
import copy
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab import http, scoring
from lab.assets import verify as verify_assets
from lab.core import (check_budget, dump, flag_value, gpu_inventory, gpu_lock,
                      hash_obj, load_config, set_flag, sha256)
from lab.corpus import body
from lab.java_eval import evaluate
from lab.runner import (OwnedServer, audited_chat, evidence_lifecycle, make_run_config,
                        validate_counter, wait_released)
from lab.statistics import STRATUM_FIELDS, summarize
from lab.tokenizer import StrataCounter

SERVICE = 'openclaw-qwen38-next.service'
FROZEN_ENV = {
    'STRATA_REPLY_REUSE': '1', 'STRATA_PRESERVE_THINKING': '0',
    'STRATA_PREFILL_CPU_SHARE_MAX': '4096', 'STRATA_PREFILL_AUTO_MAX': '16384',
    'STRATA_ADAPT_OVERLAP': '1', 'STRATA_SIDE_MIXER': '2',
    'STRATA_ATTN_DAILY': '1', 'STRATA_GR_UP75': '1',
    'STRATA_GU_SWIGLU': '1', 'STRATA_QSA_ROWS': '1', 'STRATA_B6_MMVQ_ROWS': '1',
}


def ready_spec():
    # make_run_config intentionally ignores a section named "base".
    return {'status': 'READY', 'cfg_name': 'PROD-COMBINATION-KVRES',
            'common': {'args': {'--kv-resident': '0'}},
            'cfg': {'args': {'--kv-resident': '20480'}}}


def assert_service_inactive():
    result = subprocess.run(['systemctl', 'show', SERVICE, '-p', 'ActiveState',
                             '-p', 'SubState', '-p', 'UnitFileState'],
                            capture_output=True, text=True, timeout=15, check=True)
    state = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if state.get('ActiveState') != 'inactive':
        raise RuntimeError('PRODUCTION_NOT_INACTIVE: ' + str(state))
    return state


def protected_hashes(c):
    files = c.get('protected_files', [])
    if not files or not isinstance(files, list) or any(not isinstance(x, str) for x in files):
        raise ValueError('protected_files must list the real production files to audit')
    return {str(Path(p).resolve()): sha256(Path(p)) for p in files}


def assert_protected(c, expected):
    current = protected_hashes(c)
    if current != expected:
        changed = sorted(k for k in set(current) | set(expected) if current.get(k) != expected.get(k))
        raise RuntimeError('PROTECTED_PRODUCTION_FILES_CHANGED: ' + ', '.join(changed))
    return current


def wait_cool(c, *, loaded=False):
    deadline = time.monotonic() + float(c.get('cooldown_timeout_s', 600))
    limit = float(c.get('cooldown_temperature_c', 55))
    samples = []
    while True:
        sample = gpu_inventory(c['gpu'])
        samples.append({'ts': time.time(), **sample})
        if not loaded and sample['compute_processes']:
            raise RuntimeError('FOREIGN_GPU_PROCESS_BEFORE_ARM')
        if float(sample['temperature_c']) <= limit:
            return samples
        if time.monotonic() >= deadline:
            raise RuntimeError('COOLDOWN_TIMEOUT: GPU did not reach the frozen start temperature')
        time.sleep(5)


def validate_tree(tree):
    tree = Path(tree).resolve()
    build = json.loads((tree / 'build-lab/LAB_BUILD.json').read_text())
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=tree,
                          capture_output=True, text=True, timeout=15, check=True).stdout.strip()
    dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=tree,
                           capture_output=True, text=True, timeout=15, check=True).stdout
    if dirty or build['source_sha'] != head:
        raise RuntimeError('SOURCE_TREE_NOT_FROZEN: dirty tree or mismatched build source')
    if Path(build['exe']).resolve() != (tree / 'build-lab/strata').resolve():
        raise RuntimeError('BUILD_RECEIPT_EXE_MISMATCH')
    if sha256(Path(build['exe'])) != build['exe_sha256']:
        raise RuntimeError('BINARY_HASH_MISMATCH')
    return build


def assert_same_except_kvres(base, cfg):
    """Reject accidental extra factors before either arm is started."""
    a, b = copy.deepcopy(base), copy.deepcopy(cfg)
    for config, expected in ((a, '0'), (b, '20480')):
        for key in ('args', 'user_args'):
            if flag_value(config.get(key, []), '--kv-resident') != expected:
                raise RuntimeError('KVRES_ARM_VALUE_MISMATCH')
            config[key] = set_flag(config.get(key, []), '--kv-resident', None)
        for key in ('api_key', 'log'):
            config.pop(key, None)
        for key, value in FROZEN_ENV.items():
            if config.get('env', {}).get(key) != value:
                raise RuntimeError('COMBINATION_ENV_MISMATCH: ' + key)
    if a != b:
        raise RuntimeError('ARMS_DIFFER_BEYOND_KVRES')


def validate_startup(server, arm):
    logs = '\n'.join(p.read_text(errors='replace') for p in server.folder.glob('*.log'))
    required = [r'LAB_PR_1536 enabled=1', r'LAB_CFG_PT preserve_thinking default=0',
                r'prompt chunk auto: 16384 tokens',
                r'expert cache ' + ('9420' if arm == 'base' else '10290') + r' slots']
    if arm == 'cfg':
        required.append(r'KV streaming: 20480 of 131072 cells per QSA layer in VRAM')
    if arm == 'base' and re.search(r'KV streaming: 20480 of', logs):
        raise RuntimeError('KVRES_ON_IN_BASE_ARM')
    missing = [pattern for pattern in required if re.search(pattern, logs) is None]
    if missing:
        raise RuntimeError('STARTUP_ACTIVATION_NOT_CONFIRMED: ' + ', '.join(missing))
    return {'arm': arm, 'required_patterns': required, 'confirmed': True}


def history_counter_probe(server, counter, c, folder):
    request = body('Reply only OK.', max_tokens=32)
    request['messages'][1:1] = [
        {'role': 'user', 'content': 'Record the literal marker PROBE-7319.'},
        {'role': 'assistant', 'content': 'PROBE-7319',
         'reasoning_content': 'Earlier private reasoning must not be rendered into this new turn.'},
    ]
    expected = counter(request)
    response = audited_chat(server, counter, c, request)
    record = {'request': request, 'request_sha256': hash_obj(request),
              'local_prompt_tokens': expected, 'response': response}
    dump(Path(folder) / 'history-counter-probe.json', record)
    if response.get('error') or response.get('usage', {}).get('prompt_tokens') != expected:
        raise RuntimeError('HISTORY_TOKEN_COUNTER_NOT_QUALIFIED')
    return record


def resource_sample(server):
    sample = {'ts': time.time(), 'processes': {}}
    wanted = {'MemAvailable', 'SwapFree', 'SwapTotal', 'Mlocked', 'Unevictable',
              'AnonPages', 'Cached', 'SReclaimable'}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in wanted:
            sample[key + '_kib'] = int(value.split()[0])
    for pid in [server.process.pid] + [x['pid'] for x in server.engine_audit]:
        fields = {}
        try:
            for line in (Path('/proc') / str(pid) / 'smaps_rollup').read_text().splitlines():
                if ':' in line:
                    key, value = line.split(':', 1)
                    if key in ('Rss', 'Pss', 'Anonymous', 'Private_Dirty', 'Locked', 'Swap'):
                        fields[key + '_kib'] = int(value.split()[0])
        except OSError as error:
            # A guard can terminate the engine while audited_chat returns its
            # failure; preserve that response even when /proc has disappeared.
            fields['error'] = str(error)
        sample['processes'][str(pid)] = fields
    return sample


@contextlib.contextmanager
def combination_server(c, tree, arm, ready, folder):
    """The shared lifecycle, also covering BaseException during __enter__."""
    server = OwnedServer(c, tree, arm, ready, folder)
    original_error = None
    try:
        server.__enter__()
        yield server
    except BaseException as error:
        original_error = error
        raise
    finally:
        server.__exit__(None, None, None)
        try:
            wait_released(c)
        except Exception as error:
            dump(Path(folder) / 'release-failure.json',
                 {'error': str(error), 'original_error': str(original_error) if original_error else None})
            if original_error is None:
                raise


def restore_evidence(case, text):
    tokens = [int(x) for x in re.findall(r'conversation cache: restored (\d+) tokens', text)]
    minimum = int(case.get('restore_min_tokens', 64000))
    return {'required': bool(case.get('expected_restore')), 'restored_tokens': tokens,
            'minimum_tokens': minimum,
            'pass': not case.get('expected_restore') or any(n >= minimum for n in tokens)}


def descriptors(cases):
    result = []
    for case in cases:
        n = case.get('counted_prompt_tokens')
        if type(n) is not int or n < 0:
            raise ValueError('Each case requires exact counted_prompt_tokens')
        bucket = next((str(limit) for limit in (4096, 32768, 65536, 98304, 122880, 131072)
                       if n <= limit), 'over_limit')
        descriptor = {'id': case['id'], 'group': case['group'],
                      'cache_state': case.get('cache_state', 'sequence_controlled'),
                      'scenario': case.get('scenario', 'frozen_combination_replay'),
                      'context_bucket': case.get('context_bucket', bucket),
                      'request_sha256': hash_obj(case['body']),
                      'fixed_output': case.get('fixed_output')}
        if any(str(descriptor[k]) in ('', 'unspecified') for k in STRATUM_FIELDS):
            raise ValueError('Case workload strata must be frozen and classified')
        if case.get('request_sha256', descriptor['request_sha256']) != descriptor['request_sha256']:
            raise ValueError('Frozen case request hash mismatch')
        check_budget(n, case['body']['max_tokens'])
        result.append(descriptor)
    if not result or len({x['id'] for x in result}) != len(result):
        raise ValueError('Corpus cases must have unique nonempty IDs')
    return result


def preserve_statistics(out):
    reports = {}
    for metric in ('decode_ms', 'wall_s', 'ttft_s'):
        try:
            report = summarize(out, metric=metric)
            destination = Path(out) / 'statistics' / metric
            destination.mkdir(parents=True, exist_ok=True)
            for name in ('summary.json', 'requests.csv', 'REPORT.md'):
                if (Path(out) / name).exists():
                    shutil.copyfile(Path(out) / name, destination / name)
            reports[metric] = {'decision': report['decision'], 'failures': report['failures'],
                               'invalid_pairs': report['invalid_pairs'], 'unscored': report['unscored']}
        except Exception as error:
            reports[metric] = {'error': str(error)}
    dump(Path(out) / 'statistics-index.json', reports)
    return reports


def run_combination(c, tree, corpus_path, out, rounds, execute=False):
    tree, out, corpus_path = Path(tree).resolve(), Path(out).resolve(), Path(corpus_path).resolve()
    if type(rounds) is not int or rounds < 2 or rounds % 2:
        raise ValueError('Use an even number of paired rounds for balanced AB/BA order')
    if int(c['port']) != 18089 or c['max_context'] != 131072:
        raise ValueError('Combination validation is fixed to lab port 18089 and total context 131072')
    if c['min_available_mib'] < 4096 or c.get('gpu_temp_abort_c', 85) > 85:
        raise ValueError('Do not weaken RAM or thermal protection')
    if Path(c['deployed_repo']).resolve() != tree:
        raise ValueError('deployed_repo must point to the isolated combination tree')
    if c.get('request_overrides'):
        raise ValueError('Requests must be frozen in the corpus, without runtime overrides')
    corpus = json.loads(corpus_path.read_text())
    if corpus.get('max_context') != 131072 or hash_obj(corpus['cases']) != corpus['corpus_sha256']:
        raise ValueError('Corpus identity or context mismatch')
    cases = corpus['cases']
    desc = descriptors(cases)
    ready = ready_spec()
    prepared = {arm: make_run_config(c, tree, arm, ready, out / ('prepared-' + arm))
                for arm in ('base', 'cfg')}
    assert_same_except_kvres(prepared['base'], prepared['cfg'])
    for config in prepared.values():
        if Path(config.get('cwd', '')).resolve() != tree:
            raise ValueError('Engine cwd must be the isolated combination tree')
    build = validate_tree(tree)
    plan = {'schema_version': 2, 'mode': 'CONFIG', 'arms': ['base', 'cfg'],
            'comparisons': [['base', 'cfg']], 'rounds': rounds, 'cases': desc,
            'case_ids': [x['id'] for x in desc], 'primary_metric': 'decode_ms',
            'base_sha': build['source_sha'], 'candidate_sha': build['source_sha'],
            'binary_sha256': build['exe_sha256'], 'tree': str(tree),
            'corpus_sha256': corpus['corpus_sha256'], 'ready': ready,
            'arm_meanings': {'base': 'full deployed combination except KVRES=0',
                             'cfg': 'full deployed combination with KVRES=20480'},
            'order': [['base', 'cfg'] if n % 2 == 0 else ['cfg', 'base'] for n in range(rounds)],
            'scope': 'Frozen controlled replay of the deployed combination; not full real Pi or formal quality NI',
            'cooldown_temperature_c': c.get('cooldown_temperature_c', 55),
            'cooldown_timeout_s': c.get('cooldown_timeout_s', 600),
            'not_production': True}
    if not execute:
        return {'state': 'DRY_RUN', 'plan': plan}
    protected = protected_hashes(c)
    initial_service = assert_service_inactive()
    assets = verify_assets(c)
    out.mkdir(parents=True, exist_ok=False)
    dump(out / 'campaign.json', plan)
    dump(out / 'corpus.json', corpus)
    dump(out / 'assets.json', assets)
    dump(out / 'production-before.json', {'service': initial_service, 'file_sha256': protected})
    dump(out / 'build.json', build)
    (out / 'requests.jsonl').touch(mode=0o600)
    descriptor_by_id = {x['id']: x for x in desc}
    # Counter and server must apply the same PT default before frontend is imported.
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    original_error = None
    try:
        with evidence_lifecycle(c, out):
            try:
                counter = StrataCounter(tree, c['gguf'], c['template'])
                with gpu_lock(c.get('gpu_lock_workspace', c['workspace'])):
                    for rnd, order in enumerate(plan['order']):
                        for arm in order:
                            assert_service_inactive()
                            assert_protected(c, protected)
                            verify_assets(c)
                            if validate_tree(tree) != build:
                                raise RuntimeError('BUILD_RECEIPT_CHANGED')
                            folder = out / f'round-{rnd:02d}-{arm}'
                            folder.mkdir(parents=True)
                            dump(folder / 'cooldown-before-arm.json', wait_cool(c))
                            with combination_server(c, tree, arm, ready, folder) as server:
                                dump(folder / 'activation.json', validate_startup(server, arm))
                                validate_counter(counter, server)
                                history_counter_probe(server, counter, c, folder)
                                for case in cases:
                                    if case.get('cooldown_before'):
                                        dump(folder / ('cooldown-' + case['id'] + '.json'), wait_cool(c, loaded=True))
                                    request = copy.deepcopy(case['body'])
                                    local_tokens = counter(request)
                                    if local_tokens != case['counted_prompt_tokens']:
                                        raise RuntimeError('FROZEN_CORPUS_TOKEN_COUNT_CHANGED: ' + case['id'])
                                    log = folder / 'engine.log'
                                    log_offset = log.stat().st_size if log.exists() else 0
                                    before = resource_sample(server)
                                    started = time.time()
                                    response = audited_chat(server, counter, c, request)
                                    metrics = http.measurements(response)
                                    quality = scoring.score(case, response)
                                    if case['kind'] == 'java' and not response.get('error'):
                                        quality = evaluate(response.get('text', ''), case['java_task'],
                                                           c.get('java_image', '') if c.get('java_enabled') else '',
                                                           folder / 'java' / case['id'])
                                    with log.open('rb') as source:
                                        source.seek(log_offset)
                                        new_logs = source.read().decode('utf-8', errors='replace')
                                    restored = restore_evidence(case, new_logs)
                                    if not restored['pass']:
                                        quality = {'pass': False, 'reason': 'EXPECTED_LONG_CONTEXT_RESTORE_NOT_OBSERVED'}
                                    fixed = case.get('fixed_output')
                                    record = {'round': rnd, 'arm': arm, 'case_id': case['id'], 'phase': 'measured',
                                              'started': started, **{k: descriptor_by_id[case['id']][k] for k in STRATUM_FIELDS},
                                              'request_sha256': hash_obj(request), 'request': request,
                                              'local_prompt_tokens': local_tokens, 'metrics': metrics, 'score': quality,
                                              'fixed_output_comparable': fixed is None or metrics.get('generated_tokens') == fixed,
                                              'restore_evidence': restored, 'memory_before': before,
                                              'memory_after': resource_sample(server), 'response': response}
                                    with (out / 'requests.jsonl').open('a', encoding='utf-8') as destination:
                                        destination.write(json.dumps(record, ensure_ascii=False) + '\n')
                                        destination.flush()
                                        os.fsync(destination.fileno())
                                    print(json.dumps({'round': rnd, 'arm': arm, 'case': case['id'],
                                                      'wall_s': metrics['wall_s'], 'decode_tps': metrics['decode_tps'],
                                                      'score': quality, 'generated': metrics['generated_tokens']}, ensure_ascii=False), flush=True)
                                    if response.get('error') or server.abort_reason:
                                        raise RuntimeError('REQUEST_OR_RESOURCE_FAILURE: ' + str(response.get('error') or server.abort_reason))
                                    if not restored['pass'] or (quality.get('pass') is False and
                                                              (case.get('stop_on_failure') or 'retrieval' in case['group'])):
                                        raise RuntimeError('CRITICAL_QUALITY_FAILURE: ' + case['id'])
                            assert_service_inactive()
                            assert_protected(c, protected)
            finally:
                final_protection = {'service': assert_service_inactive(),
                                    'file_sha256': assert_protected(c, protected)}
                dump(out / 'production-after.json', final_protection)
    except BaseException as error:
        original_error = error
    finally:
        reports = preserve_statistics(out)
    if original_error is not None:
        raise original_error
    return {'state': 'COMPLETE', 'results': str(out), 'statistics': reports,
            'quality_failures_preserved': True, 'deployment_approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--corpus', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--rounds', type=int, default=6)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    result = run_combination(load_config(args.config), args.tree, args.corpus, args.out, args.rounds, args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 2 if any(x.get('failures') or x.get('invalid_pairs') or x.get('unscored') or x.get('error')
                    for x in result.get('statistics', {}).values()) else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as error:
        print('COMBINATION_BLOCKED: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(2)
