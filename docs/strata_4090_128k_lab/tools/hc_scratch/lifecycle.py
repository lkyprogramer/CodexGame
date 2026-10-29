"""P21 native-C lifecycle and one separate16K memcheck, with original cache settings."""
from datetime import datetime, timezone
import argparse
import copy
import difflib
import json
from pathlib import Path
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time
from types import SimpleNamespace

import boundary
import managed_control as managed
import lifecycle_patch
from boundary_memory import MemorySampler
from run_boundaries import descendants
from lab.core import dump, sha256, load_config, gpu_lock, gpu_inventory, check_budget
from lab.runner import make_run_config, wait_released

ROOT = boundary.ROOT
TASK = ROOT / 'workspace/combination/hc-lifecycle-20261029'
TREE = ROOT / 'workspace/trees/hc-lifecycle-20261029'
PRIOR = managed.TASK
OLD_TREE = managed.TREE


def parse_done(line):
    x = line.split()
    if len(x) < 18 or x[0] != 'DONE': raise RuntimeError('DONE_SHAPE')
    return {'produced': int(x[1]), 'input_tokens': int(x[2]), 'finish': x[5],
            'reused': int(x[8]), 'read_tokens': int(x[14]),
            'chunk': int(next(s.split('=', 1)[1] for s in x if s.startswith('chunk=')))}


def cancel_trigger(mode, line, emitted):
    if mode == 'prefill' and line.startswith('PP '):
        p = line.split(); return 16384 <= int(p[1]) < int(p[2]) and emitted == 0
    return mode == 'decode' and line.startswith('T ') and emitted >= 8


def validate_memcheck(log):
    summaries = re.findall(r'ERROR SUMMARY: (\d+) errors?', log)
    if not summaries or any(int(n) != 0 for n in summaries):
        raise RuntimeError('MEMCHECK_NOT_ZERO')


def validate_cancel(mode, done, sent):
    if not sent or done['finish'] != 'cancel': raise RuntimeError('CANCEL_NOT_ACTUAL')
    if mode == 'prefill' and (done['produced'] != 0 or not 16384 <= done['reused'] + done['read_tokens'] < done['input_tokens']):
        raise RuntimeError('PREFILL_CANCEL_TERMINAL_NOT_PARTIAL')
    if mode == 'decode' and done['produced'] < 8: raise RuntimeError('DECODE_CANCEL_NOT_ACTUAL')


INFO_FIELDS = ('context', 'kv', 'kv_resident', 'expert_slots', 'expert_cache_mib', 'expert_slots_primary',
               'expert_cache_primary_mib', 'spec', 'mtp_max', 'lookup', 'pool_workers', 'pcie_frac', 'spec_min_p',
               'conversation_cache_mib', 'conversation_cache_slots', 'tail_role_token', 'vram_elastic',
               'prefill_cap', 'prefill_stages', 'stream_all_min', 'prefill_pipe')


def native_info(text):
    rows = [dict(s.split('=', 1) for s in l.split()[1:]) for l in text.splitlines() if l.startswith('INFO ')]
    if len(rows) != 1: raise RuntimeError('NATIVE_INFO_COVERAGE')
    return rows[0]


def validate_startup(actual, expected):
    if any(k not in actual or k not in expected or actual[k] != expected[k] for k in INFO_FIELDS):
        raise RuntimeError('EFFECTIVE_NATIVE_CONFIG_CHANGED')


def prepare_build():
    if TASK.exists() or TREE.exists(): raise RuntimeError('LIFECYCLE_STAGE_EXISTS')
    if json.loads((PRIOR / 'PAIR-16384.json').read_text())['status'] != 'PASS':
        raise RuntimeError('NUMERICAL_16K_NOT_PASS')
    receipt = json.loads((PRIOR / 'BUILD_COMPLETE.json').read_text())
    if sha256(OLD_TREE / 'build-lab/strata') != receipt['exe_sha256'] or any(sha256(OLD_TREE / n) != h for n, h in receipt['source'].items()):
        raise RuntimeError('P20_BUILD_DRIFT')
    if sha256(OLD_TREE / 'build-lab/libstrata_prefill.a') != receipt['new_archive_sha256'] or any(
            sha256(Path(n)) != h for n, h in receipt['reused_link_inputs'].items()):
        raise RuntimeError('P20_LINK_INPUT_DRIFT')
    c = load_config(PRIOR / 'config.json')
    before = json.loads((PRIOR / 'production-before.json').read_text())
    boundary.reference.baseline.combo.assert_service_inactive()
    boundary.reference.baseline.combo.assert_protected(c, before['protected'])
    TASK.mkdir(); dump(TASK / 'production-before.json', before)
    original = json.loads((boundary.TASK / 'inputs.json').read_text())
    short = boundary.reference.read_ids(original['4096']['path'])
    long = boundary.reference.read_ids(original['16384']['path']); long[3] += 2
    short2 = list(short); short2[3] += 1
    cancel = short[:-5] + [13] * (32768 - 4096) + short[-5:]; cancel[3] += 3
    decode = list(short); decode[3] += 4
    inputs = {}
    for name, ids in [('short', short), ('long', long), ('short2', short2), ('cancel', cancel), ('decode', decode),
                      ('memcheck', boundary.reference.read_ids(original['16384']['path']))]:
        path = TASK / (name + '.ids'); path.write_text(','.join(map(str, ids)) + '\n')
        inputs[name] = {'path': str(path), 'count': len(ids), 'sha256': sha256(path)}
    dump(TASK / 'inputs.json', inputs)
    dump(TASK / 'PREREGISTRATION.json', {
        'registered_utc': datetime.now(timezone.utc).isoformat(), 'authority': 'user: after16K numerical PASS continue staged safety/cost gates',
        'numerical_gate': str(PRIOR / 'PAIR-16384.json'), 'numerical_gate_sha256': sha256(PRIOR / 'PAIR-16384.json'),
        'sequence': ['short', 'SAVE-short', 'long', 'short2', 'RESTORE-short', 'SAVE-restored', 'restore-follow',
                     'cancel-prefill', 'continue-prefill', 'cancel-decode', 'continue-decode'],
        'native_GEN_attempt_limit': 8, 'separate_memcheck_GEN1_limit': 1, 'automatic_retries': 0,
        'actual_extents': 'first three requests must compute4096,16384,4096, all with C region; oracle/private-control disabled',
        'restore': 'native SAVE/RESTORE; compare original/restored valid logical bytes, MTP range from actual first request traces and PLE scalars',
        'cancel_prefill': 'STOP after observed PP>=16384, <total and no T; DONE cancel within30s; same prompt subsequently reuses>=16384',
        'cancel_decode': 'STOP after8 native T tokens; DONE cancel within30s; continuation uses actual emitted IDs and prefix reuse',
        'continuations': 'original IDs + actual emitted token(s) +1024 ordinary token13 + original assistant header; explicit ID/hash archive',
        'memory_tool': 'CUDA12.3 compute-sanitizer --tool memcheck --error-exitcode87; one real16K GEN1 after normal lifecycle PASS',
        'memcheck_scope': 'device memory access errors; no claim of exhaustive race/redzone or allocator-leak validation',
        'unchanged': 'P19/P20 original args/cache/resident/MAX4096/AUTO16384; C loan; no managed allocations in lifecycle or memcheck',
        'build': 'P20 prefill plus P19 program sources, log-only changes; two C++ objects rebuilt, frozen CUDA inputs reused',
        'limits': {'wall_seconds_per_engine': 1800, 'cancel_release_seconds': 30, 'gpu_c': 85, 'available_mib': 4096,
                   'context': 131072, 'safety_tokens': 4096},
        'stop': 'first functional, ownership, resource or memcheck failure stops before cost/performance',
        'formal_performance_samples': 0, 'original_six_status': 'FAIL_UNCHANGED', 'production_writes': False})
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'sha256': sha256(TASK / 'PREREGISTRATION.json'), 'gpu_requests_started': False})
    subprocess.run(['git', '-C', str(ROOT / 'workspace/repo'), 'worktree', 'add', '--detach', str(TREE),
                    '5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d'], check=True)
    for name in json.loads((boundary.P13 / 'P6_SOURCE.json').read_text())['python_port']['files']:
        shutil.copy2(OLD_TREE / name, TREE / name)
    for name, transform in [('src/prefill/prefill.cpp', lifecycle_patch.prefill), ('src/program/generate.cpp', lifecycle_patch.program)]:
        old = (OLD_TREE / name).read_text(); new = transform(old); (TREE / name).write_text(new)
        (TASK / (Path(name).stem + '.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
            fromfile='a/' + name, tofile='b/' + name)))
    c['deployed_repo'] = str(TREE); dump(TASK / 'config.json', c)
    base = boundary.TREE / 'build-lab'; out = TREE / 'build-lab'; out.mkdir()
    commands = json.loads((base / 'compile_commands.json').read_text()); compiled = []
    for source in ('src/prefill/prefill.cpp', 'src/program/generate.cpp'):
        entry = next(x for x in commands if x['file'].endswith('/' + source))
        argv = shlex.split(entry['command']); argv[argv.index('-o') + 1] = str(out / (Path(source).name + '.o'))
        argv[argv.index('-c') + 1] = str(TREE / source)
        with (TASK / (Path(source).stem + '-compile.log')).open('w') as log:
            subprocess.run(argv, cwd=entry['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
        compiled.append(argv)
    archive = out / 'libstrata_prefill.a'; shutil.copy2(OLD_TREE / 'build-lab/libstrata_prefill.a', archive)
    subprocess.run(['/usr/bin/ar', 'r', str(archive), str(out / 'prefill.cpp.o')], check=True)
    subprocess.run(['/usr/bin/ranlib', str(archive)], check=True)
    last = subprocess.check_output(['/home/hhtele/strata-0.1.43.1/.venv/bin/ninja', '-t', 'commands', 'strata'], cwd=base, text=True).splitlines()[-1]
    if not last.startswith(': && ') or not last.endswith(' && :'): raise RuntimeError('LINK_RULE_SHAPE')
    link = shlex.split(last[5:-5]); link[link.index('-o') + 1] = str(out / 'strata')
    link = [str(archive) if s == 'libstrata_prefill.a' else str(out / 'generate.cpp.o')
            if s == 'CMakeFiles/strata.dir/src/program/generate.cpp.o' else s for s in link]
    with (TASK / 'link.log').open('w') as log: subprocess.run(link, cwd=base, stdout=log, stderr=subprocess.STDOUT, check=True)
    dump(TASK / 'BUILD_COMPLETE.json', {'exe_sha256': sha256(out / 'strata'), 'compile_argv': compiled, 'link_argv': link,
         'source': {n: sha256(TREE / n) for n in ('src/prefill/prefill.cpp', 'src/program/generate.cpp')},
         'new_prefill_archive_sha256': sha256(archive), 'reused_P20_receipt_sha256': sha256(PRIOR / 'BUILD_COMPLETE.json')})
    print('P21_PREREGISTERED_AND_BUILT', flush=True)


def run(mode):
    if mode == 'memcheck' and json.loads((TASK / 'lifecycle/RUN_RESULT.json').read_text())['status'] != 'PASS':
        raise RuntimeError('LIFECYCLE_NOT_PASS')
    folder = TASK / mode; folder.mkdir()
    if sha256(TASK / 'PREREGISTRATION.json') != json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())['sha256']:
        raise RuntimeError('REGISTRATION_DRIFT')
    if sha256(TASK / 'VALIDATION_ADDENDUM.json') != json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())['validation_addendum_sha256']:
        raise RuntimeError('VALIDATION_ADDENDUM_DRIFT')
    c = load_config(TASK / 'config.json'); receipt = json.loads((TASK / 'BUILD_COMPLETE.json').read_text())
    if sha256(TREE / 'build-lab/strata') != receipt['exe_sha256'] or any(sha256(TREE / n) != h for n, h in receipt['source'].items()):
        raise RuntimeError('BUILD_DRIFT')
    c['extra_frozen_env'].update(STRATA_LAB_HC_REGION='1', STRATA_LAB_HC_KEEP_LOAN='0', STRATA_LAB_HC_MANIFEST='1',
        STRATA_LAB_BOUNDARY_TRACE='1', STRATA_LAB_HC_LIFECYCLE_TRACE='1', STRATA_LAB_HC_PRIVATE_CONTROL='0')
    for key in ('STRATA_LAB_ORACLE_DIR', 'STRATA_LAB_ORACLE_REF'): c['extra_frozen_env'].pop(key, None)
    cfg = make_run_config(c, TREE, 'cfg', {}, folder)
    expected = json.loads((boundary.TASK / 'c-16384/plan.json').read_text())
    stable = {k: v for k, v in cfg['env'].items() if k.startswith('STRATA_') and not k.startswith('STRATA_LAB_')}
    if cfg['args'] != expected['args'] or stable != {k: v for k, v in expected['env'].items() if not k.startswith('STRATA_LAB_')}:
        raise RuntimeError('FROZEN_CONFIGURATION_CHANGED')
    before = json.loads((TASK / 'production-before.json').read_text())
    boundary.reference.baseline.combo.assert_service_inactive(); boundary.reference.baseline.combo.assert_protected(c, before['protected'])
    inputs = json.loads((TASK / 'inputs.json').read_text())
    for r in inputs.values():
        if sha256(Path(r['path'])) != r['sha256']: raise RuntimeError('INPUT_DRIFT')
    cmd = [cfg['exe'], '--serve', *cfg['args']]
    if mode == 'memcheck':
        cmd = ['/usr/local/cuda-12.3/bin/compute-sanitizer', '--tool', 'memcheck', '--error-exitcode', '87',
               '--target-processes', 'all', '--log-file', str(folder / 'sanitizer.log'), *cmd]
    env = boundary.reference.clean_env(); env.update(cfg['env']); env['STRATA_DUMP_FIRST_LOGITS'] = str(folder / 'first')
    dump(folder / 'plan.json', {'args': cfg['args'], 'env': {k: v for k, v in cfg['env'].items() if k.startswith('STRATA_')},
         'command': cmd, 'registration_sha256': sha256(TASK / 'PREREGISTRATION.json'), 'performance_sample': False})
    result = {'status': 'FAIL', 'error': None, 'requests': []}
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            boundary.reference.baseline.combo.assert_service_inactive()
            dump(folder / 'cooldown.json', boundary.reference.baseline.combo.wait_cool(c))
            q = queue.Queue()
            with (folder / 'stderr.log').open('w') as err, (folder / 'stdout.log').open('w') as out:
                proc = subprocess.Popen(cmd, cwd=cfg['cwd'], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=err, text=True, bufsize=1, start_new_session=True)
                def pump():
                    for line in proc.stdout: out.write(line); out.flush(); q.put(line.strip())
                    q.put(None)
                thread = threading.Thread(target=pump, daemon=True); thread.start()
                with boundary.reference.Guard(c, folder, proc, cfg['exe'], 1800) as guard, MemorySampler(
                        folder, lambda: descendants(SimpleNamespace(process=proc))) as memory:
                    def send(text): proc.stdin.write(text + '\n'); proc.stdin.flush()
                    def until(prefix, on_line=None):
                        while True:
                            try: line = q.get(timeout=1)
                            except queue.Empty:
                                if proc.poll() is not None: raise RuntimeError('NATIVE_ENDED_WITHOUT_TERMINAL_LINE')
                                if on_line: on_line(None)
                                continue
                            if line is None or line.startswith(('ERR', 'SERR ')): raise RuntimeError('NATIVE_PROTOCOL: ' + str(line))
                            if on_line: on_line(line)
                            if line.startswith(prefix): return line
                    if until('READY ') != 'READY 131072 stop': raise RuntimeError('READY_CONTRACT')
                    actual_info = native_info((folder / 'stdout.log').read_text())
                    validate_startup(actual_info, native_info((boundary.TASK / 'c-16384/stdout.log').read_text()))
                    dump(folder / 'effective-info.json', actual_info)
                    memory.checkpoint('loaded')
                    def request(name, ids, limit=1, cancel=None):
                        check_budget(len(ids), limit, c['max_context'], c['safety_tokens'])
                        p = folder / (name + '.ids'); p.write_text(','.join(map(str, ids)) + '\n')
                        row = {'name': name, 'input_count': len(ids), 'input_sha256': sha256(p), 'max_new': limit,
                               'status': 'STARTED'}
                        result['requests'].append(row); dump(folder / 'requests.json', result['requests'])
                        offset = (folder / 'stderr.log').stat().st_size
                        outputs, stopped = [], {'at': None, 'line': None}; memory.stage = name
                        previous = set(folder.glob('first.*'))
                        def handle(line):
                            if line and line.startswith('T '): outputs.append(int(line.split()[1]))
                            if stopped['at'] is None and line and cancel_trigger(cancel, line, len(outputs)):
                                send('STOP'); stopped.update(at=time.monotonic(), line=line)
                            if stopped['at'] is not None and time.monotonic() - stopped['at'] > 30:
                                raise RuntimeError('CANCEL_RELEASE_TIMEOUT')
                        send('GEN ' + str(limit) + ' ' + ','.join(map(str, ids)))
                        done = parse_done(until('DONE ', handle))
                        delta = (folder / 'stderr.log').read_bytes()[offset:].decode(errors='replace')
                        (folder / (name + '.engine.log')).write_text(delta)
                        row.update(done=done, emitted_ids=outputs, stop=stopped, status='NATIVE_TERMINAL_RECEIVED')
                        dump(folder / 'requests.json', result['requests'])
                        if done['input_tokens'] != len(ids) or done['produced'] != len(outputs): raise RuntimeError('DONE_REQUEST_COUNT')
                        if cancel:
                            validate_cancel(cancel, done, stopped['at'] is not None)
                        elif done['finish'] != 'length' or done['produced'] != limit: raise RuntimeError('INCOMPLETE_GENERATION')
                        fresh = set(folder.glob('first.*')) - previous
                        if done['produced']:
                            if len(fresh) != 1: raise RuntimeError('FIRST_LOGITS_COVERAGE')
                            path = fresh.pop(); logits = boundary.raw_analysis.compare_files(path, path, 248320 * 4, 4)
                            if not logits['all_finite']: raise RuntimeError('NONFINITE_LOGITS')
                        chunks = [json.loads(l[len('P19_CHUNK '):]) for l in delta.splitlines() if l.startswith('P19_CHUNK ')]
                        ranges = [json.loads(l[len('P14_FULL_MTP_RANGE '):]) for l in delta.splitlines() if l.startswith('P14_FULL_MTP_RANGE ')]
                        batches = [json.loads(l[len('P14_FULL_MTP_BATCH '):]) for l in delta.splitlines() if l.startswith('P14_FULL_MTP_BATCH ')]
                        actual_request = [json.loads(l[len('P21_REQUEST '):]) for l in delta.splitlines() if l.startswith('P21_REQUEST ')]
                        if actual_request != [{'input_tokens': len(ids), 'max_new': limit}]: raise RuntimeError('REQUEST_TRACE_MISSING')
                        if 'P20_MANAGED_HC ' in delta or 'P15_ORACLE ' in delta: raise RuntimeError('CONTROL_OR_ORACLE_LEAKED_INTO_LIFECYCLE')
                        row.update(actual_chunks=chunks, MTP=ranges, MTP_batches=batches, status='VALIDATED')
                        dump(folder / 'requests.json', result['requests'])
                        return row
                    def read(name): return boundary.reference.read_ids(inputs[name]['path'])
                    if mode == 'memcheck':
                        row = request('memcheck-16384', read('memcheck'))
                        if [x['T'] for x in row['actual_chunks']] != [16384] or not row['MTP_batches']:
                            raise RuntimeError('MEMCHECK_16K_NOT_ACTUAL')
                    else:
                        first = request('short', read('short'))
                        meta_count = len(boundary.records(folder, 'P14_FULL_STATE_META'))
                        send('SAVE ' + str(folder / 'saved-short.bin')); original_saved = until('SAVED ')
                        metas = boundary.records(folder, 'P14_FULL_STATE_META')
                        if len(metas) != meta_count + 1: raise RuntimeError('SAVE_META_COVERAGE')
                        original_meta = metas[meta_count]
                        request('long', read('long')); request('short2', read('short2'))
                        if [[x['T'] for x in row['actual_chunks']] for row in result['requests']] != [[4096], [16384], [4096]]:
                            raise RuntimeError('SHORT_LONG_SHORT_NOT_ACTUAL')
                        send('RESTORE ' + str(folder / 'saved-short.bin')); restored = until('RESTORED ')
                        if restored.split()[1:3] != original_saved.split()[1:3]: raise RuntimeError('RESTORE_IDENTITY')
                        meta_count = len(boundary.records(folder, 'P14_FULL_STATE_META'))
                        send('SAVE ' + str(folder / 'restored-short.bin')); until('SAVED ')
                        metas = boundary.records(folder, 'P14_FULL_STATE_META')
                        if len(metas) != meta_count + 1: raise RuntimeError('RESTORE_SAVE_META_COVERAGE')
                        if metas[meta_count] != original_meta: raise RuntimeError('RESTORED_META_DIFFERS')
                        ranges = [[r['start'], r['end']] for r in first['MTP'] if r['end'] > r['start']]
                        if ranges != [[0, 4096]] or not first['MTP_batches']: raise RuntimeError('RESTORE_MTP_ACTUAL_RANGE')
                        state = boundary.compare_session.compare(folder / 'saved-short.bin', folder / 'restored-short.bin', draft_ranges=ranges)
                        dump(folder / 'RESTORE_BYTES.json', state)
                        if state['status'] != 'PASS': raise RuntimeError('RESTORED_VALID_BYTES_DIFFER')
                        follow = read('short') + first['emitted_ids'] + [13] * 1024 + read('short')[-5:]
                        row = request('restore-follow', follow)
                        if row['done']['reused'] < 4096: raise RuntimeError('RESTORE_REUSE_NOT_ACTUAL')
                        request('cancel-prefill', read('cancel'), 128, 'prefill')
                        row = request('continue-prefill', read('cancel'))
                        if row['done']['reused'] < 16384: raise RuntimeError('CANCEL_PREFIX_NOT_REUSED')
                        row = request('cancel-decode', read('decode'), 512, 'decode')
                        follow = read('decode') + row['emitted_ids'] + [13] * 1024 + read('decode')[-5:]
                        row = request('continue-decode', follow)
                        if row['done']['reused'] < 4096: raise RuntimeError('DECODE_CANCEL_PREFIX_NOT_REUSED')
                    memory.checkpoint('finished'); guard.finish(); send('QUIT'); proc.wait(timeout=60)
                    if proc.returncode: raise RuntimeError('NATIVE_OR_SANITIZER_EXIT_' + str(proc.returncode))
                thread.join(timeout=5)
            wait_released(c)
        if mode == 'memcheck':
            validate_memcheck((folder / 'sanitizer.log').read_text())
        result['status'] = 'PASS'
    except Exception as exc:
        result['error'] = str(exc)
        wait_released(c)
    finally:
        dump(folder / 'RUN_RESULT.json', result)
        dump(folder / 'production-after.json', {'service': boundary.reference.baseline.combo.assert_service_inactive(),
             'protected': boundary.reference.baseline.combo.assert_protected(c, before['protected']), 'gpu': gpu_inventory('0')})
    print(json.dumps({'status': result['status'], 'error': result['error'], 'requests': len(result['requests'])}), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['prepare-build', 'lifecycle', 'memcheck'])
    a = p.parse_args()
    if a.mode == 'prepare-build': prepare_build()
    elif run(a.mode)['status'] != 'PASS': raise SystemExit(2)
