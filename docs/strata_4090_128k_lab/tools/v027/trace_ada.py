"""Frozen SIDE=0 / IL89=0 decode qualification; no candidate activation."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_dequant as prior
from lab import http, scoring
from lab.core import check_budget, dump, gpu_lock, hash_obj, load_config, sha256
from lab.tokenizer import StrataCounter

ROOT = prior.ROOT
TASK = ROOT / 'workspace/combination/ada-delta-20261028'
PHASES = {'short': 'think-4096', 'long': 'think-102400'}


def output_event(raw):
    line = raw.decode('utf-8', 'strict').strip() if isinstance(raw, bytes) else raw.strip()
    if not line.startswith('data:') or line[5:].strip() == '[DONE]':
        return False
    item = json.loads(line[5:].strip())
    return any((c.get('delta') or {}).get(k)
               for c in item.get('choices', []) for k in ('content', 'reasoning_content', 'tool_calls'))


@contextmanager
def output_markers(nvtx, name):
    original = http.parse_sse

    def observed(lines, started=None, on_first=None, deadline=None):
        def marked_lines():
            for raw in lines:
                if output_event(raw):
                    nvtx.mark('P11_OUTPUT/' + name)
                yield raw

        def first():
            nvtx.mark('P11_FIRST/' + name)
            if on_first:
                on_first()
        return original(marked_lines(), started, first, deadline)

    http.parse_sse = observed
    try:
        yield
    finally:
        http.parse_sse = original


def cases():
    corpus = json.loads((prior.P3 / 'performance-corpus.json').read_text())
    result = [next(c for c in corpus['cases'] if c['id'] == name) for name in PHASES.values()]
    for c in result:
        if hash_obj(c['body']) != c['request_sha256'] or c['body']['max_tokens'] != 2048 or c['fixed_output'] != 2048:
            raise ValueError('FROZEN_INPUT_DRIFT')
    return result


def prepare():
    TASK.mkdir(exist_ok=False)
    c = load_config(prior.PRIOR / 'config.json')
    source = prior.frozen.baseline.source_receipt(Path(c['deployed_repo']), prior.PRIOR)
    before = json.loads((prior.TASK / 'FINAL_PROTECTION.json').read_text())
    dump(TASK / 'production-before.json', {
        'service': prior.frozen.baseline.combo.assert_service_inactive(),
        'file_sha256': prior.frozen.baseline.combo.assert_protected(c, before['file_sha256'])})
    selected = cases()
    dump(TASK / 'cases.json', selected)
    dump(TASK / 'PREREGISTRATION.json', {
        'purpose': 'Ada table delta baseline coverage and conditional cost screening',
        'source': source, 'driver_sha256': sha256(Path(__file__)),
        'cases': [{'id': c['id'], 'request_sha256': c['request_sha256'], 'fixed_output': 2048} for c in selected],
        'execution': 'two fresh-engine profiled requests and two unprofiled controls; same immutable body each',
        'capture': 'unchanged P6 binary; CUDA graph node trace and parent NVTX request/first/every-output',
        'decode_window': 'client observed first to last output event; excludes first-token computation and final response tail',
        'controls': 'observational profiler perturbation only, not candidate A/B or causal overhead proof',
        'threshold_reference': 0.04,
        'stop': 'no eligible delta hit or insufficient conditional removable cost stops before enabling; ambiguous trace is not NO_HIT',
        'eligible_candidate': 'new table row differs from both baseline and old IL89 override; all table differences separately counted',
        'bound': 'candidate interval union with non-target durations fixed; not exact critical path or strict unprofiled bound',
        'limits': {'max_context': 131072, 'safety_tokens': 4096, 'abort_gpu_c': 85, 'min_available_mib': 4096},
        'IL89': '0 throughout qualification', 'DEQUANT_SIDE': '0', 'original_six_status': 'FAIL_UNCHANGED',
        'production_writes': False, 'deployment': False, 'scoring_changed': False})
    return {'state': 'PREPARED'}


def run(phase, name):
    c = load_config(prior.PRIOR / 'config.json')
    c.update(gpu_monitor_interval_s=1, request_timeout_s=300)
    source = prior.frozen.baseline.source_receipt(Path(c['deployed_repo']), prior.PRIOR)
    before = json.loads((TASK / 'production-before.json').read_text())
    prior.frozen.baseline.combo.assert_service_inactive()
    prior.frozen.baseline.combo.assert_protected(c, before['file_sha256'])
    selected = next(x for x in json.loads((TASK / 'cases.json').read_text()) if x['id'] == PHASES[phase])
    if selected != next(x for x in cases() if x['id'] == PHASES[phase]):
        raise ValueError('FROZEN_CASE_DRIFT')
    folder = TASK / name
    folder.mkdir(exist_ok=False)
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    counter = StrataCounter(c['deployed_repo'], c['gguf'], c['template'])
    nvtx = prior.Nvtx()
    dump(folder / 'driver-process.json', {'pid': os.getpid(), 'started': time.time(), 'phase': phase})
    dump(folder / 'plan.json', {'phase': phase, 'case': selected, 'source': source,
                              'driver_sha256': sha256(Path(__file__)), 'IL89': '0'})
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            dump(folder / 'cooldown.json', prior.frozen.baseline.combo.wait_cool(c))
            with prior.frozen.baseline.combo.combination_server(c, Path(c['deployed_repo']), 'cfg', {}, folder) as server:
                dump(folder / 'activation.json', prior.frozen.baseline.activation_receipt(server))
                for key, value in {**prior.frozen.baseline.CONSERVATIVE, **prior.frozen.baseline.combo.FROZEN_ENV}.items():
                    if server.cfg.get('env', {}).get(key) != value:
                        raise RuntimeError('FROZEN_ENV_DRIFT: ' + key)
                prior.frozen.baseline.assert_kvres(server.cfg)
                for engine in server.engine_audit:
                    env = (Path('/proc') / str(engine['pid']) / 'environ').read_bytes().split(b'\0')
                    if b'STRATA_MMVQ_IL_89=0' not in env or b'STRATA_DEQUANT_SIDE=0' not in env:
                        raise RuntimeError('ACTUAL_ENV_DRIFT')
                with prior.frozen.MemorySampler(folder, lambda: prior.frozen.baseline.boundary.descendants(server)) as memory:
                    request = selected['body']
                    case_name = selected['id']
                    prefix = folder / case_name
                    count = counter(request)
                    check_budget(count, request['max_tokens'], 131072, 4096)
                    dump(Path(str(prefix) + '.request.json'), request)
                    memory.stage = case_name
                    memory.checkpoint(case_name + '-before')
                    offset = (folder / 'engine.log').stat().st_size
                    with nvtx.span('P11_REQUEST/' + case_name), output_markers(nvtx, case_name):
                        response = prior.frozen.baseline.boundary.exchange(server, request, prefix, timeout=300)
                    dump(Path(str(prefix) + '.response.json'), response)
                    Path(str(prefix) + '.engine.log').write_text((folder / 'engine.log').read_bytes()[offset:].decode(errors='replace'))
                    metrics = http.measurements(response)
                    row = {'name': case_name, 'body_sha256': hash_obj(request), 'local_prompt_tokens': count,
                           'metrics': metrics, 'score': scoring.score(selected, response),
                           'fixed_output_comparable': metrics['generated_tokens'] == 2048,
                           'qualification_only': True}
                    dump(folder / 'requests.json', [row])
                    print(json.dumps(row), flush=True)
                    if response.get('error') or server.abort_reason or response.get('tools'):
                        raise RuntimeError('REQUEST_INFRASTRUCTURE: ' + str(response.get('error') or server.abort_reason))
                    prior.frozen.baseline.boundary.audit_usage(request, response, count, c)
                    if metrics['reused_tokens'] != 0 or metrics['generated_tokens'] != 2048:
                        raise RuntimeError('COLD_OR_FIXED_LENGTH_REQUIREMENT_FAILED')
                    prior.frozen.baseline.boundary.wait_idle(server, folder, case_name)
                    memory.checkpoint(case_name + '-after')
        prior.frozen.baseline.source_receipt(Path(c['deployed_repo']), prior.PRIOR)
        dump(folder / 'COMPLETION.json', {'state': 'COMPLETE', 'requests': 1, 'IL89': '0',
             'original_six_status': 'FAIL_UNCHANGED'})
    except BaseException as error:
        dump(folder / 'FAILURE.json', {'error': str(error), 'partial_files_preserved': True})
        raise
    finally:
        dump(folder / 'production-after.json', {'service': prior.frozen.baseline.combo.assert_service_inactive(),
             'file_sha256': prior.frozen.baseline.combo.assert_protected(c, before['file_sha256']),
             'gpu': prior.frozen.gpu_inventory('0')})
    return {'state': 'COMPLETE', 'folder': str(folder)}


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: sys.exit('Owned profiler requested shutdown'))
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare', action='store_true')
    ap.add_argument('--phase', choices=PHASES)
    ap.add_argument('--name')
    args = ap.parse_args()
    if args.prepare:
        print(json.dumps(prepare()))
    else:
        if not args.phase or not args.name:
            ap.error('--phase and --name required')
        print(json.dumps(run(args.phase, args.name)))
