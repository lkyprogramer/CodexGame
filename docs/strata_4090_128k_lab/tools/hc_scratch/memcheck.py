"""P22 full-coverage memcheck with the frozen physical expert cache and lazy code loading."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import queue
import re
import subprocess
import threading
from types import SimpleNamespace

import lifecycle
from lifecycle import boundary, native_info, validate_startup
from lab.core import dump, sha256, load_config, gpu_lock, gpu_inventory, check_budget, port_free
from lab.runner import wait_released
from boundary_memory import MemorySampler
from run_boundaries import descendants

ROOT = lifecycle.ROOT
TASK = ROOT / 'workspace/combination/hc-memcheck-20261029'
PRIOR = lifecycle.TASK
TREE = lifecycle.TREE


def frozen_plan(plan, baseline_log):
    """Pin the original uniform-byte budget, which expands to10272 variable-size profile slots."""
    rows = re.findall(r'expert cache auto: .* -> (\d+) slots', baseline_log)
    if rows != ['7677'] or 'expert cache 10272 slots,' not in baseline_log:
        raise RuntimeError('BASELINE_CACHE_BUDGET_CHANGED')
    args = list(plan['args'])
    if args.count('--expert-cache') != 1 or args[args.index('--expert-cache') + 1] != 'auto':
        raise RuntimeError('FROZEN_CACHE_ARGUMENT_CHANGED')
    args[args.index('--expert-cache') + 1] = rows[0]
    env = dict(plan['env'])
    if any(k.startswith(('CUDA_', 'NV_COMPUTE_')) for k in env):
        raise RuntimeError('UNEXPECTED_TOOL_ENV')
    env['CUDA_MODULE_LOADING'] = 'LAZY'
    return args, env


def validate_capture(log, done, emitted, expected_allocations):
    def records(marker):
        return [json.loads(s[len(marker) + 1:]) for s in log.splitlines() if s.startswith(marker + ' ')]
    if (done['finish'] != 'length' or done['produced'] != 1 or len(emitted) != 1 or
            done['input_tokens'] != 16389 or done['reused'] != 0 or done['read_tokens'] != 16389):
        raise RuntimeError('MEMCHECK_REQUEST_NOT_COMPLETE')
    if records('P21_REQUEST') != [{'input_tokens': 16389, 'max_new': 1}]:
        raise RuntimeError('REQUEST_TRACE_CHANGED')
    chunks = records('P19_CHUNK')
    if chunks != [{'p0': 0, 'T': 16384, 'allocated_T': 16384, 'stream_all': True, 'cpu_share_limit': 4096}]:
        raise RuntimeError('MEMCHECK_16K_DISPATCH_CHANGED')
    allocations = records('P13_HC_ALLOCATION')
    if allocations != expected_allocations:
        raise RuntimeError('MEMCHECK_REGION_OR_LOAN_CHANGED')
    ranges, batches = records('P14_FULL_MTP_RANGE'), records('P14_FULL_MTP_BATCH')
    if [(r['start'], r['end']) for r in ranges] != [(0, 16384)] or not batches:
        raise RuntimeError('MEMCHECK_MTP_NOT_ACTUAL')
    if 'P20_MANAGED_HC ' in log or 'P15_ORACLE ' in log:
        raise RuntimeError('CONTROL_OR_RAW_ORACLE_ENABLED')
    return {'chunks': chunks, 'allocations': allocations, 'MTP_ranges': ranges, 'MTP_batches': batches}


def validate_tool(log):
    lifecycle.validate_memcheck(log)
    if any(s in log.lower() for s in ('internal sanitizer error', "didn't track", 'might go undetected',
                                      'suppressed', 'out of memory', 'target application returned an error')):
        raise RuntimeError('MEMCHECK_INCOMPLETE_COVERAGE')


def run(async_launch=False):
    folder = TASK / ('lazy-async-frozen-cache' if async_launch else 'lazy-frozen-cache'); folder.mkdir()
    if async_launch:
        if json.loads((TASK / 'lazy-frozen-cache/RUN_RESULT.json').read_text())['status'] != 'FAIL':
            raise RuntimeError('CORRECTIVE_RUN_REQUIRES_PRESERVED_FAILURE')
        micro = TASK / 'graph-launch-control'
        controls = {n: json.loads((micro / (n + '.json')).read_text())
                    for n in ('normal-synchronous', 'sanitizer-synchronous-negative', 'sanitizer-asynchronous')}
        if [controls[n]['returncode'] for n in controls] != [0, 1, 0]:
            raise RuntimeError('GRAPH_CONTROL_RESULTS_NOT_CONFIRMED')
        if 'FAIL: graph waits for CPU service' not in controls['sanitizer-synchronous-negative']['stderr']:
            raise RuntimeError('GRAPH_NEGATIVE_DID_NOT_REPRODUCE')
        positive = controls['sanitizer-asynchronous']
        if 'PASS: graph launch, CPU doorbell service and cleanup' not in positive['stdout']:
            raise RuntimeError('GRAPH_POSITIVE_DID_NOT_COMPLETE')
        validate_tool(positive['stdout'] + positive['stderr'])
    for path in (PRIOR / 'lifecycle/RUN_RESULT.json', lifecycle.managed.TASK / 'PAIR-16384.json'):
        if json.loads(path.read_text())['status'] != 'PASS': raise RuntimeError('PRIOR_GATE_NOT_PASS')
    receipt = json.loads((PRIOR / 'BUILD_COMPLETE.json').read_text())
    exe = TREE / 'build-lab/strata'
    if sha256(exe) != receipt['exe_sha256'] or any(sha256(TREE / n) != h for n, h in receipt['source'].items()):
        raise RuntimeError('FROZEN_BUILD_DRIFT')
    c = load_config(PRIOR / 'config.json')
    before = json.loads((PRIOR / 'production-before.json').read_text())
    previous = json.loads((PRIOR / 'memcheck/plan.json').read_text())
    args, settings = frozen_plan(previous, (PRIOR / 'lifecycle/stderr.log').read_text())
    if async_launch: settings['STRATA_VERIFY_ASYNC_LAUNCH'] = '1'
    inputs = json.loads((PRIOR / 'inputs.json').read_text())['memcheck']
    if sha256(Path(inputs['path'])) != inputs['sha256']: raise RuntimeError('INPUT_DRIFT')
    ids = boundary.reference.read_ids(inputs['path'])
    if len(ids) != 16389: raise RuntimeError('INPUT_EXTENT')
    check_budget(len(ids), 1, c['max_context'], c['safety_tokens'])
    env = boundary.reference.clean_env()
    for key in list(env):
        if key.startswith(('CUDA_', 'NV_COMPUTE_')): env.pop(key)
    env.update(CUDA_VISIBLE_DEVICES='0', **settings)
    env['STRATA_DUMP_FIRST_LOGITS'] = str(folder / 'first')
    cmd = ['/usr/local/cuda-12.3/bin/compute-sanitizer', '--tool', 'memcheck', '--error-exitcode', '87',
           '--target-processes', 'all', '--log-file', str(folder / 'sanitizer.log'), str(exe), '--serve', *args]
    expected_allocations = boundary.records(boundary.TASK / 'c-16384', 'P13_HC_ALLOCATION')
    registration = {'registered_utc': datetime.now(timezone.utc).isoformat(),
        'authority': 'user: solve memcheck OOM, preserve10272 physical slots/residency/dispatch; then staged gates',
        'changes': {'CUDA_MODULE_LOADING': 'EAGER (source default) -> LAZY',
                    'expert_cache_nominal_budget': 'auto result7677 frozen explicitly; same10272 profile slots/17055MiB',
                    'STRATA_VERIFY_ASYNC_LAUNCH': '1: existing frozen same-graph helper' if async_launch else 'unset: source default'},
        'command': cmd, 'env': settings, 'input': inputs, 'exe_sha256': sha256(exe),
        'prior_evidence_reused': {str(p): sha256(p) for p in [PRIOR / 'lifecycle/RUN_RESULT.json',
            lifecycle.managed.TASK / 'PAIR-16384.json', PRIOR / 'memcheck/RUN_RESULT.json']},
        'full_memcheck_coverage': 'no kernel filters/skips, suppressions, disabled heap checks or forced synchronization',
        'limits': {'engine_startups': 1, 'GEN1': 1, 'retries': 0, 'wall_s': 1800, 'gpu_c': 85, 'available_mib': 4096},
        'stop': 'first safety/config/functional/memory error, no cost or performance before PASS',
        'formal_performance_samples': 0, 'production_writes': False}
    if async_launch:
        registration['corrective_evidence'] = {str(p): sha256(p) for p in [
            TASK / 'lazy-frozen-cache/RUN_RESULT.json', TASK / 'lazy-frozen-cache/stderr.log',
            *(TASK / 'graph-launch-control' / (n + '.json') for n in controls)]}
    registration['driver_sha256'] = sha256(Path(__file__))
    dump(folder / 'PREREGISTRATION.json', registration)
    result = {'status': 'FAIL', 'error': None, 'GEN_attempts': 0}
    proc = None
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            boundary.reference.baseline.combo.assert_service_inactive()
            boundary.reference.baseline.combo.assert_protected(c, before['protected'])
            port_free(18089)
            if gpu_inventory('0')['compute_processes']: raise RuntimeError('GPU_NOT_IDLE')
            dump(folder / 'cooldown.json', boundary.reference.baseline.combo.wait_cool(c))
            q = queue.Queue()
            with (folder / 'stdout.log').open('w') as out, (folder / 'stderr.log').open('w') as err:
                proc = subprocess.Popen(cmd, cwd=TREE, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=err, text=True, bufsize=1, start_new_session=True)
                def pump():
                    for line in proc.stdout: out.write(line); out.flush(); q.put(line.strip())
                    q.put(None)
                thread = threading.Thread(target=pump, daemon=True); thread.start()
                with boundary.reference.Guard(c, folder, proc, exe, 1800) as guard, MemorySampler(
                        folder, lambda: descendants(SimpleNamespace(process=proc))) as memory:
                    def send(line): proc.stdin.write(line + '\n'); proc.stdin.flush()
                    def until(prefix):
                        while True:
                            try: line = q.get(timeout=1)
                            except queue.Empty:
                                if proc.poll() is not None: raise RuntimeError('NATIVE_ENDED_WITHOUT_TERMINAL_LINE')
                                continue
                            if line is None:
                                raise RuntimeError('NATIVE_PROTOCOL_EOF: launcher exit=' + str(proc.wait(timeout=5)))
                            if line.startswith(('ERR', 'SERR ')): raise RuntimeError('NATIVE_PROTOCOL: ' + line)
                            if line.startswith('T '): emitted.append(int(line.split()[1]))
                            if line.startswith(prefix): return line
                    emitted = []
                    if until('READY ') != 'READY 131072 stop': raise RuntimeError('READY_CONTRACT')
                    actual = native_info((folder / 'stdout.log').read_text())
                    validate_startup(actual, native_info((PRIOR / 'lifecycle/stdout.log').read_text()))
                    if boundary.records(folder, 'P13_HC_ALLOCATION') != expected_allocations:
                        raise RuntimeError('STARTUP_REGION_OR_LOAN_CHANGED')
                    dump(folder / 'effective-info.json', actual)
                    memory.checkpoint('loaded'); memory.stage = 'memcheck-16384'
                    result['GEN_attempts'] = 1; dump(folder / 'RUN_RESULT.json', result)
                    send('GEN 1 ' + ','.join(map(str, ids)))
                    done = lifecycle.parse_done(until('DONE '))
                    capture = validate_capture((folder / 'stderr.log').read_text(), done, emitted, expected_allocations)
                    files = list(folder.glob('first.*'))
                    if len(files) != 1: raise RuntimeError('LOGITS_COVERAGE')
                    logits = boundary.raw_analysis.compare_files(files[0], files[0], 248320 * 4, 4)
                    if not logits['all_finite']: raise RuntimeError('NONFINITE_LOGITS')
                    dump(folder / 'CAPTURE.json', dict(capture, done=done, emitted_ids=emitted, finite_logits=logits))
                    memory.checkpoint('finished'); guard.finish(); send('QUIT'); proc.wait(timeout=60)
                    if proc.returncode: raise RuntimeError('NATIVE_OR_SANITIZER_EXIT_' + str(proc.returncode))
                thread.join(timeout=5)
            wait_released(c)
        validate_tool((folder / 'sanitizer.log').read_text())
        result['status'] = 'PASS'
    except Exception as exc:
        result['error'] = str(exc)
        wait_released(c)
    finally:
        result['launcher_exit_code'] = proc.returncode if proc is not None else None
        dump(folder / 'RUN_RESULT.json', result)
        dump(folder / 'production-after.json', {'service': boundary.reference.baseline.combo.assert_service_inactive(),
             'protected': boundary.reference.baseline.combo.assert_protected(c, before['protected']), 'gpu': gpu_inventory('0')})
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--async-launch', action='store_true', help='one corrective run after graph negative/positive controls')
    if run(parser.parse_args().async_launch)['status'] != 'PASS': raise SystemExit(2)
