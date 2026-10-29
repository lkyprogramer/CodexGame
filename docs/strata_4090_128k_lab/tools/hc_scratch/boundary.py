"""Bounded P19 boundary qualification, preserving P13/P18 evidence and production."""
from datetime import datetime, timezone
import argparse
import difflib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/v027'), str(Path(__file__).parent),
               str(ROOT / 'tools/oracle_replay')]
import boundary_patch
import full_request_patch
import program_trace_patch
import compare_session
import run_reference_logits as reference
from lab.assets import verify as verify_assets
from lab.core import dump, sha256, load_config, gpu_lock, gpu_inventory, port_free
from lab.runner import make_run_config, wait_released

_analysis_spec = importlib.util.spec_from_file_location('hc_boundary_raw_analysis', ROOT / 'tools/oracle_replay/analyze.py')
raw_analysis = importlib.util.module_from_spec(_analysis_spec)
_analysis_spec.loader.exec_module(raw_analysis)

P13 = ROOT / 'workspace/combination/hc-scratch-20261028'
P18 = ROOT / 'workspace/combination/hc-c-complete-20261029'
TASK = ROOT / 'workspace/combination/hc-boundary-20261029'
TREE = ROOT / 'workspace/trees/hc-boundary-20261029'


def records(folder, marker):
    return [json.loads(s[len(marker) + 1:]) for s in (folder / 'stderr.log').read_text().splitlines()
            if s.startswith(marker + ' ')]


def prepare():
    if TASK.exists() or TREE.exists():
        raise RuntimeError('BOUNDARY_ALREADY_PREPARED')
    c = load_config(P13 / 'config.json')
    before = json.loads((P18 / 'FINAL_PROTECTION.json').read_text())
    reference.baseline.combo.assert_service_inactive()
    reference.baseline.combo.assert_protected(c, before['protected'])
    assets = verify_assets(c)
    with gpu_lock(c['gpu_lock_workspace']):
        port_free(18089)
        if gpu_inventory('0')['compute_processes']:
            raise RuntimeError('GPU_NOT_IDLE')
        TASK.mkdir()
    dump(TASK / 'production-before.json', before)
    dump(TASK / 'ASSETS.json', {'metadata': assets, 'fresh_full_content_hash': False})
    original = P13 / 'think-4096.ids'
    ids = reference.read_ids(original)
    if len(ids) != 4095 or sha256(original) != '3c4f5016a093346a0c6f8aaeec401592c15f9326c044fe89051ba7b2f168367d':
        raise RuntimeError('ORIGINAL_FIXTURE_DRIFT')
    turn = ids[-5]
    if turn != 248045 or ids[-5:] != [248045, 74455, 198, 248068, 198]:
        raise RuntimeError('FROZEN_HEADER_DRIFT')
    inputs = {}
    for size in (4096, 16384):
        padded = ids[:-5] + [13] * (size - 4090) + ids[-5:]
        assert len(padded) == size + 5 and max(i for i, t in enumerate(padded) if t == turn) == size
        p = TASK / f'boundary-{size}.ids'
        p.write_text(','.join(map(str, padded)) + '\n')
        inputs[str(size)] = {'name': f'boundary-{size}', 'count': len(padded), 'path': str(p), 'sha256': sha256(p),
                             'expected_main_chunk': size, 'fixture_only': True}
    dump(TASK / 'inputs.json', inputs)
    registration = {
        'registered_utc': datetime.now(timezone.utc).isoformat(),
        'authority': 'user: continue the proposed staged boundary/lifecycle, then cost-signal tests',
        'scope': 'actual 4096/16384 numerical safety before lifecycle and one long-request A/C mechanism pair',
        'phases': ['c-4096', 'control-4096', 'c-16384', 'control-16384'], 'native_GEN1_limit': 4,
        'retries': 0, 'first_failure_stops': True,
        'input': inputs, 'all_original_failures': 'FAIL_UNCHANGED',
        'frozen': 'original complete P6 config, CPUshare MAX4096, AUTO MAX16384, kernels, weights, resident20480, MTP and checkpoints',
        'boundary': 'pad ordinary period tokens before original assistant turn; require actual single chunk 4096/16384, not allocated size',
        'oracle': 'same reduced C loan/resident; capture/replay actual stream/fused/CPU decisions and route/group mapping; independent HC allocations',
        'bytes': 'all raw fields, target HC/half/handoff, full chunk R, full logits and actual-effective SAVE state; tolerance zero',
        'streamed_extension': 'record actual streamed/fused branch, resident map and fused slot/src; CPUshare eligibility unchanged',
        'control_memory': 'extra private HC bytes, fail if unavailable; never change cache/reserve to fit',
        'stop': 'any missing extent, mismatch, resource/ownership error or unsupported shape prevents lifecycle, cost and performance',
        'later_stages': 'only after four valid captures and both strict boundary gates; separately preregister lifecycle/sanitizer, then one A/C100K trace',
        'formal_performance': 'only after clear retained-expert critical-path cost signal and all safety gates; existing six-pair 4% and CI rules unchanged',
        'formal_performance_samples': 0, 'production_writes': False, 'deployment': False,
        'limits': {'gpu_c': 85, 'available_mib': 4096, 'context': 131072, 'safety_tokens': 4096},
    }
    dump(TASK / 'PREREGISTRATION.json', registration)
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'sha256': sha256(TASK / 'PREREGISTRATION.json'), 'gpu_requests_started': False})
    commands = json.loads((P18 / 'build-commands.json').read_text())
    old_tree = str(P18).replace('/combination/hc-c-complete-', '/trees/hc-c-complete-')
    commands = [[s.replace(old_tree, str(TREE)) for s in cmd] for cmd in commands]
    dump(TASK / 'build-commands.json', commands)
    subprocess.run(['git', '-C', str(ROOT / 'workspace/repo'), 'worktree', 'add', '--detach', str(TREE),
                    '5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d'], check=True)
    hc_tree = Path(c['deployed_repo'])
    for name in json.loads((P13 / 'P6_SOURCE.json').read_text())['python_port']['files']:
        shutil.copy2(hc_tree / name, TREE / name)
    p = TREE / 'src/prefill/prefill.cpp'
    old = (hc_tree / 'src/prefill/prefill.cpp').read_text()
    new = boundary_patch.transform(old)
    p.write_text(new)
    (TASK / 'prefill.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                              fromfile='a/src/prefill/prefill.cpp', tofile='b/src/prefill/prefill.cpp')))
    p = TREE / 'src/program/generate.cpp'
    p.write_text(program_trace_patch.transform((hc_tree / 'src/program/generate.cpp').read_text()))
    c['deployed_repo'] = str(TREE)
    dump(TASK / 'config.json', c)
    print('P19_PREREGISTERED', sha256(TASK / 'PREREGISTRATION.json'), flush=True)


def build():
    if (TASK / 'BUILD_COMPLETE.json').exists():
        raise RuntimeError('BUILD_ALREADY_COMPLETE')
    for i, cmd in enumerate(json.loads((TASK / 'build-commands.json').read_text())):
        with (TASK / f'build-{i}.log').open('w') as log:
            subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    dump(TASK / 'BUILD_COMPLETE.json', {'exe_sha256': sha256(TREE / 'build-lab/strata'),
          'source': {n: sha256(TREE / n) for n in ('src/prefill/prefill.cpp', 'src/program/generate.cpp')},
          'prefill_patch_sha256': sha256(TASK / 'prefill.patch')})
    print('P19_BUILD_COMPLETE', flush=True)


def validate(folder, size, control=False):
    complete = json.loads((folder / 'oracle/COMPLETE.json').read_text())
    if complete.get('chunks') != 1 or complete.get('ffn') != 48:
        raise RuntimeError('CHUNK_FFN_COVERAGE')
    rows = [json.loads(l) for l in (folder / 'oracle/records.jsonl').read_text().splitlines()]
    if len(rows) != complete['records'] or any(r['first_mismatch_byte'] != -1 or r['T'] != size or r['p0'] != 0 for r in rows):
        raise RuntimeError('RAW_COVERAGE_OR_MISMATCH')
    prefix = f'p0-T{size}'
    paths = {p.name: p for p in (folder / 'oracle').glob('*.bin')}
    expected = {f"p{r['p0']}-T{r['T']}-l{r['layer']}-h{r['half']}-{r['field']}.bin": r['bytes'] for r in rows}
    if len(expected) != len(rows) or paths.keys() != expected.keys() or any(paths[n].stat().st_size != b for n, b in expected.items()):
        raise RuntimeError('RAW_FILE_SET_OR_SIZE')
    geometry = struct.unpack('<10q', paths[f'{prefix}-l-1-h-1-chunk_begin.bin'].read_bytes())
    if geometry != (0, size, 2560, 10240, 4, 320, 10, 512, 0, 48):
        raise RuntimeError('COMPUTED_CHUNK_GEOMETRY')
    for layer in range(48):
        execution = struct.unpack('<5q', paths[f'{prefix}-l{layer}-h1-stream_execution.bin'].read_bytes())
        if execution[0] != 1 or execution[2:4] != (1, 4096) or execution[4] <= 8:
            raise RuntimeError('STREAMED_BRANCH_NOT_ACTUAL')
    for n in ('hc_entry_R', 'hc_write_R', 'hc_xn16', 'hc_lo', 'hc_lo16', 'hc_gated', 'hc_mixed', 'body_bo'):
        if f'{prefix}-l3-h1-{n}.bin' not in paths:
            raise RuntimeError('HC_TARGET_MISSING: ' + n)
    if f'{prefix}-l4-h0-normed_handoff.bin' not in paths or f'{prefix}-l-1-h-1-chunk_end_R.bin' not in paths:
        raise RuntimeError('HANDOFF_OR_CHUNK_END_MISSING')
    required_sizes = {'hc_entry_R': size * 10240 * 4, 'hc_write_R': size * 10240 * 4,
                      'hc_xn16': size * 10240 * 2, 'hc_lo': size * 320 * 4,
                      'hc_lo16': size * 320 * 2, 'hc_gated': size * 10240 * 4,
                      'hc_mixed': size * 2560 * 4, 'body_bo': size * 2560 * 4}
    if any(paths[f'{prefix}-l3-h1-{n}.bin'].stat().st_size != b for n, b in required_sizes.items()):
        raise RuntimeError('HC_RAW_SHAPE')
    if paths[f'{prefix}-l-1-h-1-chunk_end_R.bin'].stat().st_size != size * 10240 * 4:
        raise RuntimeError('CHUNK_END_SHAPE')
    chunks = records(folder, 'P19_CHUNK')
    if chunks != [{'p0': 0, 'T': size, 'allocated_T': size, 'stream_all': True, 'cpu_share_limit': 4096}]:
        raise RuntimeError('ACTUAL_BOUNDARY_GEOMETRY')
    if control and records(folder, 'P19_PRIVATE_HC') != [{'T': size, 'bytes': size * 63360 + 1024,
                                                          'separate_allocations': 4, 'loan_unchanged': True}]:
        raise RuntimeError('PRIVATE_HC_CONTROL_NOT_EXECUTED')
    ranges = [[r['start'], r['end']] for r in records(folder, 'P14_FULL_MTP_RANGE') if r['end'] > r['start']]
    if ranges != [[0, size]] or not records(folder, 'P14_FULL_MTP_BATCH'):
        raise RuntimeError('ACTUAL_MTP_RANGE')
    if records(folder, 'P14_FULL_REQUEST') != [{'input_tokens': size + 5, 'max_new': 1, 'use_mtp': True}]:
        raise RuntimeError('REQUEST_GEOMETRY')
    saved = json.loads((folder / 'SAVED.json').read_text())
    if saved['live_tokens'] != size + 5 or len(records(folder, 'P14_FULL_STATE_META')) != 1:
        raise RuntimeError('LIVE_STATE_GEOMETRY')
    calls = records(folder, 'P14_FULL_DRAFT_CALL')
    if not calls or any(r['called'] or r['produced'] != 1 or r['max_new'] != 1 for r in calls):
        raise RuntimeError('UNACCOUNTED_DRAFT_CALL')
    logits = raw_analysis.compare_files(folder / f'boundary-{size}.f32', folder / f'boundary-{size}.f32', 248320 * 4, 4)
    if not logits['all_finite']:
        raise RuntimeError('NONFINITE_LOGITS')
    return {'raw_records': len(rows), 'raw_bytes': sum(expected.values()), 'MTP_ranges': ranges, 'actual_chunks': chunks}


def run(name):
    phases = json.loads((TASK / 'PREREGISTRATION.json').read_text())['phases']
    index = phases.index(name)
    if any((TASK / p / 'RUN_RESULT.json').exists() and json.loads((TASK / p / 'RUN_RESULT.json').read_text())['status'] != 'CAPTURE_VALID' for p in phases):
        raise RuntimeError('EARLIER_FAILURE_STOP')
    if index and not (TASK / phases[index - 1] / 'RUN_RESULT.json').exists():
        raise RuntimeError('PHASE_ORDER')
    if index == 2 and json.loads((TASK / 'PAIR-4096.json').read_text())['status'] != 'PASS':
        raise RuntimeError('FIRST_BOUNDARY_NOT_PASS')
    if json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())['sha256'] != sha256(TASK / 'PREREGISTRATION.json'):
        raise RuntimeError('REGISTRATION_DRIFT')
    build_receipt = json.loads((TASK / 'BUILD_COMPLETE.json').read_text())
    if sha256(TREE / 'build-lab/strata') != build_receipt['exe_sha256'] or any(sha256(TREE / n) != h for n, h in build_receipt['source'].items()):
        raise RuntimeError('BUILD_DRIFT')
    size = int(name.split('-')[-1]); control = name.startswith('control')
    folder = TASK / name; folder.mkdir()
    c = load_config(TASK / 'config.json')
    c['extra_frozen_env'].update(STRATA_LAB_HC_REGION='1', STRATA_LAB_HC_KEEP_LOAN='0', STRATA_LAB_HC_MANIFEST='1',
        STRATA_LAB_BOUNDARY_TRACE='1', STRATA_LAB_ORACLE_DIR=str(folder / 'oracle'),
        STRATA_LAB_HC_PRIVATE_CONTROL='1' if control else '0')
    if control: c['extra_frozen_env']['STRATA_LAB_ORACLE_REF'] = str(TASK / f'c-{size}/oracle')
    cfg = make_run_config(c, TREE, 'cfg', {}, folder)
    for key, value in {**reference.baseline.CONSERVATIVE, **reference.baseline.combo.FROZEN_ENV}.items():
        if cfg['env'].get(key) != value: raise RuntimeError('FROZEN_ENV_DRIFT: ' + key)
    reference.baseline.assert_kvres(cfg)
    before = json.loads((TASK / 'production-before.json').read_text())
    reference.baseline.combo.assert_service_inactive()
    reference.baseline.combo.assert_protected(c, before['protected'])
    verify_assets(c)
    selected = json.loads((TASK / 'inputs.json').read_text())[str(size)]
    if sha256(Path(selected['path'])) != selected['sha256']: raise RuntimeError('TOKEN_DRIFT')
    (folder / 'empty.ids').write_text('\n')
    dump(folder / 'plan.json', {'name': name, 'registration_sha256': sha256(TASK / 'PREREGISTRATION.json'),
         'tokens': selected, 'args': cfg['args'], 'env': {k: v for k, v in cfg['env'].items() if k.startswith('STRATA_')},
         'build': build_receipt, 'performance_sample': False})
    result = {'status': 'FAIL', 'error': None}
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            dump(folder / 'cooldown.json', reference.baseline.combo.wait_cool(c))
            try:
                reference.run_native(c, folder, [{'name': selected['name'], 'tokens': selected,
                                                'prefix': {'path': str(folder / 'empty.ids')}}], save_session=True)
            finally:
                wait_released(c)
        result.update(capture=validate(folder, size, control), status='CAPTURE_VALID')
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        dump(folder / 'RUN_RESULT.json', result)
        dump(folder / 'production-after.json', {'service': reference.baseline.combo.assert_service_inactive(),
             'protected': reference.baseline.combo.assert_protected(c, before['protected']), 'gpu': gpu_inventory('0')})
    print(json.dumps(result), flush=True)
    return result


def analyze(size):
    left, right = TASK / f'c-{size}', TASK / f'control-{size}'
    result = {'status': 'FAIL', 'issues': [], 'formal_performance_samples': 0}
    try:
        for folder, control in ((left, False), (right, True)):
            if json.loads((folder / 'RUN_RESULT.json').read_text())['status'] != 'CAPTURE_VALID':
                raise RuntimeError('CAPTURE_NOT_VALID: ' + folder.name)
            validate(folder, size, control)
        for marker in ('P14_FULL_MTP_RANGE', 'P14_FULL_MTP_BATCH', 'P14_FULL_DRAFT_CALL', 'P14_FULL_STATE_META'):
            if records(left, marker) != records(right, marker):
                raise RuntimeError('METADATA_DIFFERS: ' + marker)
        paths = list((left / 'oracle').glob('*.bin'))
        if {p.name for p in paths} != {p.name for p in (right / 'oracle').glob('*.bin')}:
            raise RuntimeError('RAW_FIELD_SET_DIFFERS')
        for p in paths:
            comparison = raw_analysis.compare_files(p, right / 'oracle' / p.name, p.stat().st_size)
            if not comparison['bitwise_equal']: raise RuntimeError('RAW_DIFFERENCE: ' + p.name)
        result['raw'] = {'records': len(paths), 'bytes': sum(p.stat().st_size for p in paths), 'bytewise_equal': True}
        result['logits'] = raw_analysis.compare_files(left / f'boundary-{size}.f32', right / f'boundary-{size}.f32', 248320 * 4, 4)
        if not result['logits']['bitwise_equal'] or not result['logits']['all_finite']: raise RuntimeError('LOGITS_DIFFER')
        result['state'] = compare_session.compare(left / 'session.bin', right / 'session.bin', draft_ranges=[[0, size]])
        if result['state']['status'] != 'PASS': raise RuntimeError('STATE_DIFFERS')
        result['status'] = 'PASS'
    except Exception as exc:
        result['issues'].append(str(exc))
    dump(TASK / f'PAIR-{size}.json', result)
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'build', 'run', 'analyze'])
    parser.add_argument('--name')
    parser.add_argument('--size', type=int, choices=[4096, 16384])
    args = parser.parse_args()
    if args.mode == 'prepare': prepare()
    elif args.mode == 'build': build()
    elif args.mode == 'run':
        if run(args.name)['status'] != 'CAPTURE_VALID': sys.exit(2)
    elif analyze(args.size)['status'] != 'PASS': sys.exit(2)
