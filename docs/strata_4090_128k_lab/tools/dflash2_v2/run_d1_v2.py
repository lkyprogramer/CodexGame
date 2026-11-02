"""One frozen D1 attempt, no retries, no service control, no D2."""
import datetime as dt
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

R = Path(__file__).resolve().parent
Q = R.parent / 'df01-d1q-v2-adapter-20261102'
spec = importlib.util.spec_from_file_location('prior_helpers', R.parent / 'df01-d1-20261102/supervisor.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)
s.RUN = R
STATE = {}

def verify_files():
    auth = json.loads((R / 'AUTHORIZATION.json').read_text())
    for p, digest in auth['expected_sha256'].items():
        assert s.sha(p) == digest, 'FROZEN_IDENTITY_MISMATCH: ' + p
    return {'sha256': auth['expected_sha256']}


def validate_v2_receipt(receipt):
    assert receipt['schema'] == 'df01-v2-drafter/1', 'V2_SCHEMA'
    assert receipt['D1_v2_qualified'] is False, 'FIXTURE_MUST_NOT_QUALIFY_D1'
    gates = receipt['v2_hard_gates']
    assert gates['drafter_rows_tokens_probability_validity'] == 'PASS', 'V2_DRAFTER_HARD_GATE'
    legacy = receipt['legacy_v1_numeric_result']
    diagnostic = receipt['v2_confidence_diagnostic']
    assert len(diagnostic['values']) == 7, 'V2_INCOMPLETE_PROBABILITIES'
    if legacy == 'FAIL':
        assert receipt['legacy_reason'].startswith('selector probability '), 'UNAUTHORIZED_LEGACY_FAILURE'
        assert 'reason=absolute_difference ' in receipt['legacy_reason'], 'UNAUTHORIZED_LEGACY_FAILURE'
        assert diagnostic['threshold_exceeded'] is True, 'V2_MISSING_DIAGNOSTIC'
    else:
        assert legacy == 'PASS' and diagnostic['threshold_exceeded'] is False, 'V2_LEGACY_CLASSIFICATION'
    return {'legacy_v1_numeric_result': legacy, 'v2_confidence_diagnostic': diagnostic, 'v2_hard_gates': gates, 'D1_v2_qualified': False}


def validate_drafter_receipts(command):
    output = []
    for path in command['argv'][2:]:
        name = Path(path).name + '.v2-observed.bin'
        assert (R / name).is_file(), 'MISSING_RAW_OBSERVATION'
        receipt = json.loads((R / (name + '.json')).read_text())
        output.append({'fixture': path, 'observation': name, **validate_v2_receipt(receipt)})
    assert len(output) == 4
    return output

def stopped():
    service = s.service()
    assert service['ActiveState'] == 'inactive' and service['SubState'] == 'dead' and service['MainPID'] == '0', 'PRODUCTION_STATE_DRIFT'
    return service

def preflight():
    frozen = verify_files()
    commands = json.loads((Q / 'COMMANDS_V2.json').read_text())
    assert json.loads((Q / 'CPU_CHECKS.json').read_text())['status'] == 'PASS'
    assert json.loads((Q / 'RESULT.json').read_text())['v2_adapter'] == 'BUILT_CPU_TESTED_FROZEN_NOT_GPU_EXECUTED'
    assert json.loads((R / 'BINDING_CPU_CHECKS.json').read_text())['status'] == 'PASS'
    assert json.loads((R / 'AUTHORIZATION.json').read_text())['limits'] == {'qualification_programs': 2, 'fixtures': 16, 'generations': 6, 'GPU_window_seconds': 3600}
    assert 'D2_generation_commands' not in commands
    assert not any(k in commands['env'] for k in ['STRATA_SPEC_PROB','STRATA_SPEC_COUPLED','STRATA_SPEC_GATE_PICK','STRATA_SPEC_GUMBEL','STRATA_SPEC_COST'])
    for c in commands['D1_generation_commands']:
        assert '--serve' not in c['argv'] and '--spec-follow' not in c['argv'] and '--spec-oracle' not in c['argv'] and '--spec-corrupt' not in c['argv']
        path = Path(c['argv'][c['argv'].index('--tokens-file') + 1])
        ids = [int(x) for x in path.read_text().split()]
        assert hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest() == c['input_token_ids_sha256']
        assert len(ids) + 2048 + 4096 <= 131072
    assert len(commands['qualification_programs']) == 2 and len(commands['D1_generation_commands']) == 6
    assert sum(c['fixtures'] for c in commands['qualification_programs']) == 16
    service, resources = stopped(), s.telemetry()
    assert not resources['gpu_pids'], 'FOREIGN_GPU_PROCESS'
    assert resources['temperature_c'] < 85 and resources['mem_available_mib'] > 4096
    for port in [18343, 18089]:
        assert not s.command(['ss', '-Hltn', 'sport = :' + str(port)]).strip(), 'PORT_IN_USE'
    assert os.statvfs(R).f_bavail * os.statvfs(R).f_frsize >= 8 * 1024 ** 3, 'DISK_BUDGET'
    s.write('PREFLIGHT.json', {'status': 'PASS', 'utc': s.utc(), 'service': service, 'resources': resources, 'frozen_files': len(frozen['sha256']), 'service_control': 'NONE'})
    return commands

def run_step(command, env, work_deadline):
    s.cleanup()
    assert time.monotonic() < work_deadline, 'GPU_WORK_DEADLINE'
    stopped()
    assert not s.gpu_pids(), 'FOREIGN_GPU_PROCESS'
    c = command
    kind = c['kind']
    entry = {'id': c['id'], 'kind': kind, 'status': 'RUNNING', 'argv': c['argv'], 'env': env, 'started_utc': s.utc()}
    STATE['steps'].append(entry); s.write('STATE.json', STATE)
    start = time.monotonic()
    with (R / (c['id'] + '.stdout')).open('x') as out, (R / (c['id'] + '.stderr')).open('x') as err:
        p = subprocess.Popen(c['argv'], cwd=R, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
        s.ACTIVE = (p, s.identity(p.pid)); entry['identity'] = s.ACTIVE[1]
        s.write('STATE.json', STATE)
        try:
            while p.poll() is None:
                assert time.monotonic() < work_deadline, 'GPU_WORK_DEADLINE'
                t = s.telemetry(p.pid)
                with (R / 'TELEMETRY.jsonl').open('a') as log:
                    log.write(json.dumps({'step': c['id'], **t}) + '\n')
                assert t['temperature_c'] < 85, 'GPU_TEMPERATURE_LIMIT'
                assert t['mem_available_mib'] > 4096, 'HOST_MEMORY_LIMIT'
                assert set(t['gpu_pids']) <= {p.pid}, 'FOREIGN_GPU_PROCESS'
                time.sleep(2)
            assert p.returncode == 0, 'NATIVE_PROGRAM_FAILURE'
            stdout = (R / (c['id'] + '.stdout')).read_text()
            stderr = (R / (c['id'] + '.stderr')).read_text()
            if kind == 'qualification':
                marker = 'DF01 drafter qualification: 7 fixtures PASS' if c['id'] == 'drafter' else 'DF01 target state: 9 fixtures PASS'
                assert marker in stdout, 'INCOMPLETE_FIXTURE_RECEIPT'
                if c['id'] == 'drafter':
                    entry['v2_drafter_receipts'] = validate_drafter_receipts(c)
                if c['id'] == 'target-state':
                    assert 'DFlash2 drafter on (' in stderr, 'FAIL_ACTIVATION'
                assert not re.search(r'falling back|capture.*fail|out of memory', stderr, re.I), 'FALLBACK_OR_RESOURCE_FAILURE'
            else:
                entry['metrics'] = s.parse_generation(c, stdout, stderr)
            entry['status'] = 'PASS'
        except BaseException as error:
            entry['status'] = 'FAIL'; entry['error'] = str(error)
            raise
        finally:
            s.cleanup()
            entry['exit_code'] = p.returncode
            entry['wall_seconds'] = time.monotonic() - start
            entry['finished_utc'] = s.utc()
            s.write('STATE.json', STATE)

def interrupted(signum, frame):
    raise RuntimeError('SIGNAL_' + str(signum))

def main():
    global STATE
    commands = preflight()
    if '--preflight' in sys.argv:
        print('CPU/FROZEN/STOPPED PREFLIGHT PASS'); return
    lock = (R.parent.parent / '.gpu.lock').open('r')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with (R / 'GPU_ATTEMPT.json').open('x') as f:
        json.dump({'utc': s.utc(), 'launch_limit': 8, 'qualification_programs': 2, 'fixtures': 16, 'generations': 6, 'no_retry': True, 'binding': str(Q / 'FINAL_FREEZE.json'), 'commands': str(Q / 'COMMANDS_V2.json')}, f)
    if '--detach' in sys.argv:
        pid = os.fork()
        if pid:
            print('supervisor_pid=' + str(pid), flush=True); return
        os.setsid()
        fd = os.open(R / 'supervisor.log', os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o644)
        os.dup2(fd, 1); os.dup2(fd, 2)
        fd = os.open('/dev/null', os.O_RDONLY); os.dup2(fd, 0)
    for sig in [signal.SIGTERM, signal.SIGINT]: signal.signal(sig, interrupted)
    started = dt.datetime.now(dt.timezone.utc); work_deadline = time.monotonic() + 3000
    all_steps = [{**c, 'kind': 'qualification'} for c in commands['qualification_programs']] + [{**c, 'kind': 'generation'} for c in commands['D1_generation_commands']]
    STATE = {'id': 'DF01-D1S-V2-20261102', 'status': 'RUNNING', 'started_utc': started.isoformat(), 'deadline_utc': (started + dt.timedelta(seconds=3600)).isoformat(), 'work_deadline_utc': (started + dt.timedelta(seconds=3000)).isoformat(), 'supervisor': s.identity(os.getpid()), 'steps': [], 'planned_steps': [x['id'] for x in all_steps], 'D2': 'NOT_AUTHORIZED_NOT_RUN', 'production_policy': 'KEEP_STOPPED'}
    env = {'PATH': '/usr/local/cuda-12.3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin', 'USER': 'hhtele', 'LOGNAME': 'hhtele', 'LANG': 'C.UTF-8', 'CUDA_VISIBLE_DEVICES': '0', 'CUDA_CACHE_PATH': str(R / 'cuda-cache'), **commands['env']}
    try:
        s.write('STATE.json', STATE)
        for c in all_steps:
            run_step(c, {**env, **c.get('env_add', {})}, work_deadline)
        STATE['status'] = 'D1_V2_QUALIFIED'
        STATE['D1_v2_qualified'] = True
    except BaseException as error:
        STATE['status'] = 'D1_STOPPED'
        STATE['D1_v2_qualified'] = False; STATE['first_failure'] = str(error)
    finally:
        for sig in [signal.SIGTERM, signal.SIGINT]: signal.signal(sig, signal.SIG_IGN)
        try:
            s.cleanup(); service = stopped()
            assert not s.gpu_pids(), 'GPU_PROCESS_REMAINS'
            STATE['GPU_processes_finished_utc'] = s.utc()
            s.write('STATE.json', STATE)
            frozen = verify_files()
            assert not s.gpu_pids(), 'GPU_PROCESS_REMAINS'
            STATE['final_readback'] = {'status': 'PASS', 'service': service, 'frozen_files': len(frozen['sha256']), 'GPU_compute_apps': [], 'service_starts': 0, 'service_stops': 0, 'utc': s.utc()}
        except BaseException as error:
            STATE['D1_v2_qualified'] = False
            STATE['status'] = 'D1_STOPPED'
            STATE['final_readback'] = {'status': 'FAIL', 'error': str(error), 'utc': s.utc()}
        STATE['not_run'] = [x for x in STATE['planned_steps'] if x not in {v['id'] for v in STATE['steps']}]
        STATE['qualification_programs_started'] = sum(v['kind'] == 'qualification' for v in STATE['steps'])
        STATE['generations_started'] = sum(v['kind'] == 'generation' for v in STATE['steps'])
        STATE['finished_utc'] = s.utc()
        STATE['qualification_fixtures_maximum'] = 16
        s.write('STATE.json', STATE)
        fcntl.flock(lock, fcntl.LOCK_UN)

if __name__ == '__main__': main()
