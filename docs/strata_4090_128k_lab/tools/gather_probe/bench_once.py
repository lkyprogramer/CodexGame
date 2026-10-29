"""Run one ordinary-user, fixed-duration complete-expert replay arm."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools/combination'))
from boundary_memory import MemorySampler, system_memory
import run_boundaries as boundary
from lab.core import gpu_inventory, gpu_lock

TASK = Path('/home/hhtele/strata-lab-4090/workspace/gather-probe-20261028')
TREE = TASK.parent / 'trees/gather-probe-20261028'


def validate_request(a):
    out = Path(a.out).resolve()
    scope = 'bench' if a.scope == 'bench' else 'micro'
    expected = (30, 60) if a.scope == 'bench' else (2, 10)
    if a.scope not in ('bench', 'row-bench') or a.mode not in ('off', 'on'):
        raise ValueError('ARM_SCOPE_OR_MODE')
    if out.parents[1] != TASK.resolve() or out.parent.name != scope or (a.warm, a.seconds) != expected:
        raise ValueError('ARM_PATH_OR_DURATION')
    return out


def check_resources(config):
    gpu = gpu_inventory(config.get('gpu', 0))
    available = system_memory()['meminfo']['MemAvailable_kib'] / 1024
    if gpu['compute_processes']:
        raise RuntimeError('GPU_LOAD_DURING_CPU_BENCH')
    if float(gpu['temperature_c']) >= 85:
        raise RuntimeError('GPU_TEMPERATURE_LIMIT')
    if available < max(4096, config.get('min_available_mib', 4096)):
        raise RuntimeError('HOST_MEMORY_FLOOR')
    return {'ts': time.time(), 'gpu': gpu, 'MemAvailable_mib': available}


def stop_group(child):
    """Only this Popen's new process group is eligible for cleanup."""
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=5)
    # perf may have exited before its benchmark; clear any remaining group members.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run(a):
    out = validate_request(a)
    if os.geteuid() == 0:
        raise RuntimeError('BENCH_MUST_RUN_AS_ORDINARY_USER')
    proof = json.loads((TASK / 'correctness/COMPLETE.json').read_text())
    exe = TREE / 'build-lab/lab_gu_probe'
    if proof['state'] != 'PASS' or hashlib.sha256(exe.read_bytes()).hexdigest() != proof['binary_sha256']:
        raise RuntimeError('CORRECTNESS_GATE_IDENTITY')
    config = json.loads((TASK / 'config.json').read_text())
    protected = json.loads((TASK / 'production-before.json').read_text())['file_sha256']
    combo = boundary.combo
    combo.assert_service_inactive()
    combo.assert_protected(config, protected)
    env = {k: v for k, v in os.environ.items() if not k.startswith('STRATA_')}
    env.update({k: str(v) for k, v in config['extra_frozen_env'].items()})
    for key in list(env):
        if key.startswith(('STRATA_LAB_GU_', 'STRATA_LAB_GATHER_')) or key == 'LD_PRELOAD':
            env.pop(key)
    env['STRATA_LAB_GU_GATHER'] = '0'
    command = [str(exe), a.scope, str(TASK / 'fixtures.txt'), a.mode, str(a.warm), str(a.seconds)]
    events = 'cycles,ref-cycles,instructions,task-clock,page-faults,minor-faults,major-faults,context-switches,cpu-migrations'
    perf = ['perf', 'stat', '-x,', '-e', events, '-o', str(out / 'owner-perf.csv'), '--', *command]
    receipt = {'command': perf, 'uid': os.geteuid(), 'started': time.time(), 'candidate': 'IQ3_S-nt1-AVX2-gather'}
    (out / 'command.json').write_text(json.dumps(receipt, indent=2) + '\n')
    child = None
    error = None
    resources = []
    try:
        with gpu_lock(config.get('gpu_lock_workspace', config['workspace'])), \
                (out / 'stdout.log').open('w') as stdout, (out / 'stderr.log').open('w') as stderr:
            resources.append(check_resources(config))
            child = subprocess.Popen(perf, stdout=stdout, stderr=stderr, env=env, start_new_session=True)
            receipt['perf_pid'] = child.pid
            (out / 'command.json').write_text(json.dumps(receipt, indent=2) + '\n')
            fake = types.SimpleNamespace(process=child, engine_audit=[])
            with MemorySampler(out, lambda: boundary.descendants(fake)) as memory:
                try:
                    memory.checkpoint('before')
                    memory.stage = 'load-warmup-measure'
                    deadline = time.monotonic() + a.warm + a.seconds + 120
                    while child.poll() is None:
                        if time.monotonic() > deadline:
                            raise RuntimeError('BENCH_ABSOLUTE_TIMEOUT')
                        resources.append(check_resources(config))
                        time.sleep(1)
                    if child.returncode:
                        raise RuntimeError('BENCH_FAILED ' + str(child.returncode))
                finally:
                    stop_group(child)
                    child = None
                    memory.checkpoint('after')
            resources.append(check_resources(config))
        rows = [json.loads(s) for s in (out / 'stdout.log').read_text().splitlines() if s.startswith('{')]
        if len(rows) != 1 or rows[0]['state'] != 'COMPLETE' or rows[0]['mode'] != a.mode:
            raise RuntimeError('BENCH_RESULT_IDENTITY')
        result = rows[0]
        if a.scope == 'bench' and (result['workers'] != 15 or result['seconds'] < 60 or result['sweeps'] <= 0):
            raise RuntimeError('BENCH_DURATION_OR_WORKERS')
        if a.scope == 'bench' and (a.mode == 'on') != (result['candidate_row_calls'] > 0):
            raise RuntimeError('CANDIDATE_HIT_EVIDENCE')
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        return result
    except BaseException as exc:
        error = str(exc) or type(exc).__name__
        raise
    finally:
        if child is not None:
            stop_group(child)
        (out / 'resources.json').write_text(json.dumps(resources, indent=2) + '\n')
        try:
            combo.assert_service_inactive()
            combo.assert_protected(config, protected)
        except BaseException as exc:
            error = (error + '; ' if error else '') + 'FINAL_PROTECTION: ' + (str(exc) or type(exc).__name__)
            raise
        finally:
            (out / 'completion.json').write_text(json.dumps({'state': 'FAILURE' if error else 'COMPLETE', 'error': error}, indent=2) + '\n')


def terminated(*_):
    raise KeyboardInterrupt('BENCH_TERMINATED')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminated)
    parser = argparse.ArgumentParser()
    parser.add_argument('out')
    parser.add_argument('scope', choices=['bench', 'row-bench'])
    parser.add_argument('mode', choices=['off', 'on'])
    parser.add_argument('warm', type=float)
    parser.add_argument('seconds', type=float)
    print(json.dumps(run(parser.parse_args())), flush=True)
