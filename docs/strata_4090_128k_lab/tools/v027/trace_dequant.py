"""DEQUANT_SIDE=0: immutable HTTP cases and cross-process NVTX observation."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
import run_reference_logits as frozen
from lab import http, scoring
from lab.core import check_budget, dump, gpu_lock, hash_obj, load_config, sha256
from lab.tokenizer import StrataCounter

PRIOR = ROOT / 'workspace/combination/v027-20261028'
P3 = ROOT / 'workspace/combination/kvres-20261027'
P8 = ROOT / 'workspace/combination/reference-logits-20261028'
P9 = ROOT / 'workspace/combination/higher-precision-20261028'
TASK = ROOT / 'workspace/combination/dequant-side-20261028'


class Nvtx:
    def __init__(self):
        self.lib = ctypes.CDLL('libnvToolsExt.so.1')
        self.lib.nvtxRangePushA.argtypes = [ctypes.c_char_p]
        self.lib.nvtxRangePop.argtypes = []
        self.lib.nvtxMarkA.argtypes = [ctypes.c_char_p]

    @contextmanager
    def span(self, name):
        self.lib.nvtxRangePushA(name.encode())
        try:
            yield
        finally:
            self.lib.nvtxRangePop()

    def mark(self, name):
        self.lib.nvtxMarkA(name.encode())


@contextmanager
def first_output_marker(nvtx, name):
    """Use the existing SSE parser's first-output classification without changing bytes."""
    original = http.parse_sse

    def observed(lines, started=None, on_first=None, deadline=None):
        def mark():
            nvtx.mark('P10_FIRST/' + name)
            if on_first:
                on_first()
        return original(lines, started, mark, deadline)

    http.parse_sse = observed
    try:
        yield
    finally:
        http.parse_sse = original


def cases():
    corpus = json.loads((P3 / 'performance-corpus.json').read_text())
    result = []
    for name, scenario in [('append-prime', 'DIAGNOSTIC_SUBSTITUTE_FULL_REREAD_NOT_REAL_COMPACTION'),
                           ('append-0', 'FROZEN_SYNTHETIC_3K_APPEND')]:
        case = next(x for x in corpus['cases'] if x['id'] == name)
        if hash_obj(case['body']) != case['request_sha256']:
            raise ValueError('P3_FROZEN_BODY_DRIFT')
        result.append({'name': name, 'scenario': scenario, 'case': case,
                       'request': case['body'], 'body_sha256': case['request_sha256'],
                       'source': str(P3 / 'performance-corpus.json')})
    request = json.loads((PRIOR / 'baseline-v2/cfg/102400-prime.request.json').read_text())
    anchor = next(x for x in json.loads((P8 / 'inputs.json').read_text()) if x['name'] == 'prime-102400')
    if hash_obj(request) != anchor['source_request_sha256']:
        raise ValueError('P6_FROZEN_BODY_DRIFT')
    result.append({'name': '102400-prime', 'scenario': 'FROZEN_ORIGINAL_100K_COLD',
                   'case': {'id': '102400-prime', 'kind': 'exact', 'expected': anchor['gold']},
                   'request': request, 'body_sha256': hash_obj(request),
                   'source': str(PRIOR / 'baseline-v2/cfg/102400-prime.request.json')})
    return result


def prepare():
    TASK.mkdir(exist_ok=False)
    c = load_config(PRIOR / 'config.json')
    source = frozen.baseline.source_receipt(Path(c['deployed_repo']), PRIOR)
    protected = json.loads((P9 / 'FINAL_PROTECTION.json').read_text())['file_sha256']
    dump(TASK / 'production-before.json', {'service': frozen.baseline.combo.assert_service_inactive(),
         'file_sha256': frozen.baseline.combo.assert_protected(c, protected)})
    selected = cases()
    dump(TASK / 'cases.json', selected)
    dump(TASK / 'PREREGISTRATION.json', {
        'purpose': 'closed DEQUANT_SIDE path coverage and optimistic removable-cost qualification, not performance A/B',
        'source': source, 'driver_sha256': sha256(Path(__file__)),
        'cases': [{'name': x['name'], 'body_sha256': x['body_sha256'], 'scenario': x['scenario']} for x in selected],
        'execution': 'append-prime then append-0 on engine A; original100K on fresh engine B; one run each',
        'observability': 'unmodified P6 binary/server; parent NVTX request/first-output markers plus Nsight CUDA process-tree trace',
        'dequant_side': '0 throughout; no side=1 or performance pairing while original correctness gate remains FAIL',
        'trace_policy': 'inspect real sqlite schema and trace completeness; all dequant is initially only a candidate superset',
        'stop_rule': 'no actual eligible coverage or insufficient exposed/removable cost stops this direction; ambiguous attribution is not NO_HIT',
        'bound': 'optimistic dequant deletion/overlap bounds only, assuming unchanged other work; no measured speedup claim',
        'performance_gate_reference': 'P3 request improvement4%; small synthetic outputs do not represent real long thinking requests',
        'limits': {'max_context': 131072, 'safety_tokens': 4096, 'abort_gpu_c': 85, 'min_available_mib': 4096},
        'original_six_status': 'FAIL_UNCHANGED', 'real_compaction_fixture_available': False,
        'production_writes': False, 'deployment': False, 'scoring_changed': False})
    return {'state': 'PREPARED', 'task': str(TASK)}


def run(phase, name):
    c = load_config(PRIOR / 'config.json')
    c['gpu_monitor_interval_s'] = 1
    c['request_timeout_s'] = 300
    source = frozen.baseline.source_receipt(Path(c['deployed_repo']), PRIOR)
    before = json.loads((TASK / 'production-before.json').read_text())
    frozen.baseline.combo.assert_service_inactive()
    frozen.baseline.combo.assert_protected(c, before['file_sha256'])
    folder = TASK / name
    folder.mkdir(exist_ok=False)
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    counter = StrataCounter(c['deployed_repo'], c['gguf'], c['template'])
    frozen_cases = json.loads((TASK / 'cases.json').read_text())
    selected = frozen_cases[:2] if phase == 'append' else frozen_cases[2:]
    if selected != (cases()[:2] if phase == 'append' else cases()[2:]):
        raise ValueError('P10_FROZEN_CASE_DRIFT')
    nvtx = Nvtx()
    dump(folder / 'driver-process.json', {'pid': os.getpid(), 'started': time.time(), 'phase': phase})
    dump(folder / 'plan.json', {'phase': phase, 'cases': selected, 'source': source,
                              'driver_sha256': sha256(Path(__file__)), 'dequant_side': '0'})
    rows = []
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            dump(folder / 'cooldown.json', frozen.baseline.combo.wait_cool(c))
            with frozen.baseline.combo.combination_server(c, Path(c['deployed_repo']), 'cfg', {}, folder) as server:
                activation = frozen.baseline.activation_receipt(server)
                dump(folder / 'activation.json', activation)
                env = server.cfg.get('env', {})
                for key, value in {**frozen.baseline.CONSERVATIVE, **frozen.baseline.combo.FROZEN_ENV}.items():
                    if env.get(key) != value:
                        raise RuntimeError('FROZEN_ENV_DRIFT: ' + key)
                frozen.baseline.assert_kvres(server.cfg)
                for engine in server.engine_audit:
                    data = (Path('/proc') / str(engine['pid']) / 'environ').read_bytes().split(b'\0')
                    if b'STRATA_DEQUANT_SIDE=0' not in data:
                        raise RuntimeError('ACTUAL_DEQUANT_SIDE_NOT_ZERO')
                with frozen.MemorySampler(folder, lambda: frozen.baseline.boundary.descendants(server)) as memory:
                    for item in selected:
                        case_name = item['name']
                        request = item['request']
                        prefix = folder / case_name
                        count = counter(request)
                        check_budget(count, request['max_tokens'], 131072, 4096)
                        dump(Path(str(prefix) + '.request.json'), request)
                        memory.stage = case_name
                        memory.checkpoint(case_name + '-before')
                        engine_log = folder / 'engine.log'
                        offset = engine_log.stat().st_size
                        with nvtx.span('P10_REQUEST/' + case_name), first_output_marker(nvtx, case_name):
                            response = frozen.baseline.boundary.exchange(server, request, prefix, timeout=300)
                        dump(Path(str(prefix) + '.response.json'), response)
                        delta = engine_log.read_bytes()[offset:].decode(errors='replace')
                        Path(str(prefix) + '.engine.log').write_text(delta)
                        score = scoring.score(item['case'], response)
                        metrics = http.measurements(response)
                        record = {'name': case_name, 'scenario': item['scenario'], 'body_sha256': hash_obj(request),
                                  'matches_original_body': hash_obj(request) == item['body_sha256'],
                                  'local_prompt_tokens': count, 'metrics': metrics, 'score': score,
                                  'expected': item['case']['expected'], 'profiled_wall_not_performance_sample': True}
                        rows.append(record)
                        dump(folder / 'requests.json', rows)
                        print(json.dumps(record), flush=True)
                        if response.get('error') or server.abort_reason or response.get('tools'):
                            raise RuntimeError('REQUEST_INFRASTRUCTURE: ' + str(response.get('error') or server.abort_reason))
                        frozen.baseline.boundary.audit_usage(request, response, count, c)
                        if case_name in ('append-prime', '102400-prime') and metrics['reused_tokens'] != 0:
                            raise RuntimeError('EXPECTED_COLD_INPUT_REUSED')
                        if case_name == 'append-0' and not (3000 <= metrics['read_tokens'] <= 3500 and metrics['reused_tokens'] >= 32000):
                            raise RuntimeError('EXPECTED_3K_APPEND_NOT_OBSERVED')
                        frozen.baseline.boundary.wait_idle(server, folder, case_name)
                        memory.checkpoint(case_name + '-after')
        frozen.baseline.source_receipt(Path(c['deployed_repo']), PRIOR)
        dump(folder / 'COMPLETION.json', {'state': 'COMPLETE', 'requests': len(rows),
             'dequant_side': '0', 'original_six_status': 'FAIL_UNCHANGED'})
    except BaseException as error:
        dump(folder / 'FAILURE.json', {'error': str(error), 'partial_files_preserved': True})
        raise
    finally:
        dump(folder / 'production-after.json', {'service': frozen.baseline.combo.assert_service_inactive(),
             'file_sha256': frozen.baseline.combo.assert_protected(c, before['file_sha256']),
             'gpu': frozen.gpu_inventory('0')})
    return {'state': 'COMPLETE', 'folder': str(folder)}


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Owned profiler requested shutdown'))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--phase', choices=['append', 'cold'])
    ap.add_argument('--name')
    args = ap.parse_args()
    if args.prepare:
        print(json.dumps(prepare()))
    else:
        if not args.phase or not args.name:
            ap.error('--phase and --name required')
        print(json.dumps(run(args.phase, args.name)))
