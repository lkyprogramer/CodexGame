"""Bounded full-request oracle: capture A, replay A, replay B, then natural C."""
from datetime import datetime, timezone
import argparse
import difflib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import prepare
import full_request_patch
import program_trace_patch
import analyze as local_analysis
import compare_session
import run_reference_logits as reference
from lab.core import dump, sha256, load_config, gpu_lock, gpu_inventory
from lab.runner import make_run_config, wait_released
from lab.assets import verify as verify_assets

TASK = prepare.TASK / 'full-request'
TREE = prepare.TREE
PHASES = {'capture-a': ('A', None), 'replay-a': ('A', 'capture-a'),
          'replay-b': ('B', 'capture-a'), 'natural-c': ('C', None),
          'replay-control': ('C', 'natural-c')}


def prepare_full():
    if TASK.exists():
        raise RuntimeError('FULL_REQUEST_ALREADY_PREPARED')
    for name, status in [('aa-3', 'PASS'), ('negative-input', 'NEGATIVE_CONTROL_PASS'),
                         ('negative-dispatch', 'NEGATIVE_CONTROL_PASS'), ('negative-mapping', 'NEGATIVE_CONTROL_PASS')]:
        if json.loads((prepare.TASK / name / 'ANALYSIS.json').read_text())['status'] != status:
            raise RuntimeError('LOCAL_ORACLE_GATE: ' + name)
    TASK.mkdir()
    archive = prepare.TASK / 'local-stage-source'
    archive.mkdir()
    for name in ('src/prefill/prefill.cpp', 'build-lab/strata'):
        dest = archive / Path(name).name
        shutil.copy2(TREE / name, dest)
    dump(archive / 'IDENTITY.json', {p.name: sha256(p) for p in archive.iterdir() if p.is_file()})
    dump(TASK / 'PREREGISTRATION.json', {
        'registered_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'frozen 4095-token GEN1; full request normal single execution, actual T4090 main chunk',
        'local_stage_requests': 6, 'local_stage_failures_preserved': ['aa-1', 'aa-2'],
        'phases': PHASES, 'native_request_limit': 6, 'planned_requests': 4, 'targeted_failure_diagnostics_max': 2,
        'order': ['capture-a', 'replay-a', 'replay-b', 'natural-c'],
        'dispatch': 'A capture actual CPU arm/experts; replay A/B use that assignment, recompute routing and compare exact mappings',
        'layout': 'A original; B shared HC with original loan; C natural reduced loan and original auto CPUshare',
        'bytes': ['initial GDN/PLE and scalars', 'actual route/resident/row/group transcript for all FFN layers',
                  'target layer3 half1 HC values, body bo, half R and next-half fused norm cache',
                  'full FP32 chunk R', 'complete logits', 'SAVE logical live and checkpoint state with effective KV cells'],
        'state_validity': 'full SAVE checksum then byte compare; exclude LRU, page-tail cells and unused indexer tail; MTP ranges from successful actual calls',
        'MTP': 'record actual batched geometry and successful computed ranges; GEN1 must short-circuit drafting; record live PLE scalars separately',
        'stop': ['any missing guard/shape/actual extent: blocked', 'A/A difference: locate first recorded field, stop B/C',
                 'A/B difference: no C/performance', 'natural C changes numerical path: retain differences, no performance with failed quality gate'],
        'not_proven': ['all lifecycle cases', 'actual4096/16K computation', 'natural C from A/B', 'request performance', 'quality adoption'],
        'resource_limits': {'gpu_c': 85, 'available_mib': 4096, 'context': 131072, 'safety_tokens': 4096},
        'original_six_status': 'FAIL_UNCHANGED', 'performance_samples': 0,
    })
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'sha256': sha256(TASK / 'PREREGISTRATION.json'), 'gpu_requests_started': False})
    # Both inputs are still the frozen P13/P6 source; initial FFN probe is archived above.
    shutil.copy2(prepare.HC_TREE / 'src/prefill/prefill.cpp', TREE / 'src/prefill/prefill.cpp')
    shutil.copy2(prepare.HC_TREE / 'src/program/generate.cpp', TREE / 'src/program/generate.cpp')
    patch = full_request_patch.apply(TREE, TASK / 'prefill.patch')
    program = TREE / 'src/program/generate.cpp'
    old = program.read_text()
    new = program_trace_patch.transform(old)
    (TASK / 'program.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                            fromfile='a/src/program/generate.cpp', tofile='b/src/program/generate.cpp')))
    program.write_text(new)
    dump(TASK / 'PATCH.json', {'prefill': patch, 'program_sha256': sha256(program), 'program_patch_sha256': sha256(TASK / 'program.patch')})
    print(json.dumps({'state': 'PREREGISTERED', 'sha256': sha256(TASK / 'PREREGISTRATION.json')}), flush=True)


def build():
    if (TASK / 'BUILD_COMPLETE.json').exists():
        raise RuntimeError('FULL_BUILD_ALREADY_COMPLETE')
    commands = json.loads((prepare.TASK / 'build-commands.json').read_text())
    for index, cmd in enumerate(commands):
        with (TASK / f'build-{index}.log').open('w') as out:
            result = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT)
        if result.returncode:
            raise RuntimeError(f'BUILD_FAILED: build-{index}.log')
    source = {f: sha256(TREE / f) for f in ('src/prefill/prefill.cpp', 'src/program/generate.cpp')}
    receipt = {'exe_sha256': sha256(TREE / 'build-lab/strata'), 'source': source}
    dump(TASK / 'BUILD_COMPLETE.json', receipt)
    print(json.dumps(receipt), flush=True)


def log_records(folder, marker):
    prefix = marker + ' '
    return [json.loads(s[len(prefix):]) for s in (folder / 'stderr.log').read_text().splitlines() if s.startswith(prefix)]


def validate_capture(folder):
    if folder.name == 'replay-control':
        control = log_records(folder, 'P18_PRIVATE_HC')
        if control != [{'T': 4090, 'bytes': 259523584, 'separate_allocations': 4, 'loan_unchanged': True}]:
            raise RuntimeError('PRIVATE_HC_CONTROL_NOT_EXECUTED')
    completed = json.loads((folder / 'oracle/COMPLETE.json').read_text())
    if completed['marker'] != 'P15_ORACLE_COMPLETE' or completed['chunks'] != 1 or completed['ffn'] != 48:
        raise RuntimeError('FULL_CAPTURE_COVERAGE')
    raw = folder / 'oracle'
    records = [json.loads(s) for s in (raw / 'records.jsonl').read_text().splitlines()]
    names = [f"p{r['p0']}-T{r['T']}-l{r['layer']}-h{r['half']}-{r['field']}.bin" for r in records]
    if len(records) != completed['records'] or len(set(names)) != len(names) or set(names) != {p.name for p in raw.glob('*.bin')}:
        raise RuntimeError('RAW_MANIFEST_COVERAGE')
    for name, record in zip(names, records):
        if record['first_mismatch_byte'] != -1 or (raw / name).stat().st_size != record['bytes']:
            raise RuntimeError('RAW_MANIFEST_SHAPE: ' + name)
    layers = {(r['p0'], r['T'], r['layer'], r['half']) for r in records if r['field'] == 'mmq_geometry'}
    if layers != {(0, 4090, l, 1) for l in range(48)}:
        raise RuntimeError('ACTUAL_FFN_LAYER_COVERAGE')
    target = 'p0-T4090-l3-h1-'
    required = {target + 'hc_entry_R.bin': 4090 * 10240 * 4,
                target + 'hc_write_R.bin': 4090 * 10240 * 4,
                target + 'body_bo.bin': 4090 * 2560 * 4,
                target + 'body_inj.bin': 4090 * 4 * 4,
                target + 'hc_path.bin': 10 * 8,
                'p0-T4090-l4-h0-normed_handoff.bin': 5 * 8,
                'p0-T4090-l-1-h-1-chunk_begin.bin': 10 * 8,
                'p0-T4090-l-1-h-1-chunk_end_R.bin': 4090 * 10240 * 4}
    for name, size in required.items():
        if not (raw / name).is_file() or (raw / name).stat().st_size != size:
            raise RuntimeError('TARGET_CAPTURE_SHAPE: ' + name)
    shape = struct.unpack('<10q', (raw / 'p0-T4090-l-1-h-1-chunk_begin.bin').read_bytes())
    if shape != (0, 4090, 2560, 10240, 4, 320, 10, 512, 0, 48):
        raise RuntimeError('ACTUAL_CHUNK_GEOMETRY')
    hc = struct.unpack('<10q', (raw / (target + 'hc_path.bin')).read_bytes())
    _, unfused, _, _, _, _, upmixed, xnlo, lolo, mixedlo = hc
    fields = {'hc_xn16': 4090 * 10240 * 2, 'hc_lo': 4090 * 320 * 4, 'hc_lo16': 4090 * 320 * 2,
              'hc_mixed': 4090 * 2560 * 4, 'hc_mixed_h': 4090 * 2560 * 2,
              'hc_mixed_bf': 4090 * 2560 * 2, 'hc_inj': 4090 * 4 * 4,
              'hc_xn' if unfused else 'hc_grs': 4090 * (10240 if unfused else 4) * 4}
    if not upmixed: fields['hc_gated'] = 4090 * 10240 * 4
    if xnlo: fields['hc_xn16_lo'] = 4090 * 10240 * 2
    if lolo: fields['hc_lo16_lo'] = 4090 * 320 * 2
    if mixedlo: fields['hc_mixed_bf_lo'] = 4090 * 2560 * 2
    required.update({target + name + '.bin': size for name, size in fields.items()})
    initial = 'p0-T4090-l-2-h-1-'
    init = struct.unpack('<10q', (raw / (initial + 'initial_geometry.bin')).read_bytes())
    if init[:2] != (0, 4090) or init[8:] != (9, 10240):
        raise RuntimeError('INITIAL_STATE_GEOMETRY')
    required[initial + 'initial_gdn_state.bin'] = init[3] * init[6] * 4
    required[initial + 'initial_ple_tokens.bin'] = 12
    if init[7]: required[initial + 'initial_ple_hist.bin'] = 9 * 10240 * 4
    handoff = 'p0-T4090-l4-h0-'
    cache = struct.unpack('<5q', (raw / (handoff + 'normed_handoff.bin')).read_bytes())
    if cache[0]:
        required[handoff + 'cached_grs.bin'] = 4090 * 4 * 4
        required[handoff + 'cached_xn16.bin'] = 4090 * 10240 * 2
        if cache[4]: required[handoff + 'cached_xn16_lo.bin'] = 4090 * 10240 * 2
    for name, size in required.items():
        if not (raw / name).is_file() or (raw / name).stat().st_size != size:
            raise RuntimeError('TARGET_CAPTURE_SHAPE: ' + name)
    saved = json.loads((folder / 'SAVED.json').read_text())
    metas = log_records(folder, 'P14_FULL_STATE_META')
    calls = log_records(folder, 'P14_FULL_DRAFT_CALL')
    ranges = log_records(folder, 'P14_FULL_MTP_RANGE')
    batches = log_records(folder, 'P14_FULL_MTP_BATCH')
    request = log_records(folder, 'P14_FULL_REQUEST')
    if len(metas) != 1 or metas[0]['live_tokens'] != saved['live_tokens'] or saved['live_tokens'] != 4095:
        raise RuntimeError('LIVE_STATE_IDENTITY')
    if len(request) != 1 or request[0] != {'input_tokens': 4095, 'max_new': 1, 'use_mtp': True}:
        raise RuntimeError('REQUEST_GEOMETRY')
    if not calls or any(r['called'] or r['produced'] != 1 or r['max_new'] != 1 for r in calls):
        raise RuntimeError('UNACCOUNTED_DRAFT_CALL')
    if not ranges or not batches:
        raise RuntimeError('MISSING_MTP_EXTENT')
    valid = [[r['start'], r['end']] for r in ranges if r['end'] > r['start']]
    if not valid:
        raise RuntimeError('EMPTY_MTP_EXTENT')
    dump(folder / 'MTP_RANGES.json', {'ranges': valid, 'evidence': ranges, 'actual_batches': batches, 'draft_calls': calls})
    logits = local_analysis.compare_files(folder / 'think-4096.f32', folder / 'think-4096.f32', 248320 * 4, 4)
    if not logits['all_finite']:
        raise RuntimeError('NONFINITE_LOGITS')
    return {'capture': completed, 'saved': saved, 'state_meta': metas[0], 'MTP': valid}


def run(name):
    variant, ref = PHASES[name]
    if name == 'replay-b' and json.loads((TASK / 'AA_ANALYSIS.json').read_text())['status'] != 'PASS':
        raise RuntimeError('FULL_AA_NOT_PASS')
    if name == 'natural-c' and json.loads((TASK / 'AB_ANALYSIS.json').read_text())['status'] != 'PASS':
        raise RuntimeError('FULL_AB_NOT_PASS')
    if ref and json.loads((TASK / ref / 'RUN_RESULT.json').read_text())['status'] != 'CAPTURE_VALID':
        raise RuntimeError('REFERENCE_CAPTURE_NOT_VALID')
    if ref:
        validate_capture(TASK / ref)
    reg = json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())
    if reg['sha256'] != sha256(TASK / 'PREREGISTRATION.json') or len(list(TASK.glob('*/plan.json'))) >= 6:
        raise RuntimeError('REGISTRATION_OR_BUDGET')
    receipt = json.loads((TASK / 'BUILD_COMPLETE.json').read_text())
    if name == 'replay-control' and not receipt.get('private_hc_control'):
        raise RuntimeError('PRIVATE_HC_CONTROL_NOT_IN_BUILD')
    if sha256(TREE / 'build-lab/strata') != receipt['exe_sha256'] or any(sha256(TREE / f) != h for f, h in receipt['source'].items()):
        raise RuntimeError('FULL_BUILD_DRIFT')
    folder = TASK / name
    folder.mkdir(exist_ok=False)
    c = load_config(prepare.TASK / 'config.json')
    c['extra_frozen_env'].update(STRATA_LAB_HC_REGION='0' if variant == 'A' else '1',
        STRATA_LAB_HC_KEEP_LOAN='1' if variant == 'B' else '0', STRATA_LAB_HC_MANIFEST='1',
        STRATA_LAB_ORACLE_DIR=str(folder / 'oracle'),
        STRATA_LAB_HC_PRIVATE_CONTROL='1' if name == 'replay-control' else '0')
    if ref:
        c['extra_frozen_env']['STRATA_LAB_ORACLE_REF'] = str(TASK / ref / 'oracle')
    cfg = make_run_config(c, TREE, 'cfg', {}, folder)
    for key, value in {**reference.baseline.CONSERVATIVE, **reference.baseline.combo.FROZEN_ENV}.items():
        if cfg['env'].get(key) != value:
            raise RuntimeError('FROZEN_ENV_DRIFT: ' + key)
    reference.baseline.assert_kvres(cfg)
    before = json.loads((prepare.TASK / 'production-before.json').read_text())
    verify_assets(c)
    reference.baseline.combo.assert_protected(c, before['file_sha256'])
    selected = json.loads((prepare.TASK / 'tokens.json').read_text())
    if sha256(Path(selected['path'])) != selected['sha256']:
        raise RuntimeError('TOKEN_DRIFT')
    (folder / 'empty.ids').write_text('\n')
    case = {'name': selected['name'], 'tokens': selected, 'prefix': {'path': str(folder / 'empty.ids')}}
    dump(folder / 'plan.json', {'started_utc': datetime.now(timezone.utc).isoformat(), 'variant': variant,
         'reference': ref, 'registration_sha256': reg['sha256'], 'tokens': selected,
         'exe_sha256': receipt['exe_sha256'], 'source': receipt['source'], 'args': cfg['args'],
         'strata_env': {k: v for k, v in cfg['env'].items() if k.startswith('STRATA_')}, 'performance_sample': False})
    result = {'status': 'FAIL', 'native_error': None, 'original_six_status': 'FAIL_UNCHANGED'}
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            reference.baseline.combo.assert_service_inactive()
            dump(folder / 'cooldown.json', reference.baseline.combo.wait_cool(c))
            try:
                reference.run_native(c, folder, [case], save_session=True)
            except Exception as exc:
                result['native_error'] = str(exc)
            wait_released(c)
        if not result['native_error']:
            result['capture'] = validate_capture(folder)
            result['status'] = 'CAPTURE_VALID'
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        dump(folder / 'production-after.json', {'service': reference.baseline.combo.assert_service_inactive(),
             'file_sha256': reference.baseline.combo.assert_protected(c, before['file_sha256']), 'gpu': gpu_inventory('0')})
        dump(folder / 'RUN_RESULT.json', result)
    print(json.dumps(result), flush=True)
    return result


def analyze_pair(other):
    left = TASK / ('natural-c' if other == 'replay-control' else 'capture-a')
    right = TASK / other
    natural = other == 'natural-c'
    output = {'status': 'FAIL', 'scope': 'logical state and bounded full-request raw capture',
              'issues': [], 'raw': [], 'execution_changes': []}
    try:
        for path in (left, right):
            if json.loads((path / 'RUN_RESULT.json').read_text())['status'] != 'CAPTURE_VALID':
                raise RuntimeError('CAPTURE_NOT_VALID: ' + path.name)
        for marker in ('P14_FULL_MTP_RANGE', 'P14_FULL_MTP_BATCH', 'P14_FULL_DRAFT_CALL', 'P14_FULL_STATE_META'):
            if log_records(left, marker) != log_records(right, marker):
                target_list = 'execution_changes' if natural and marker != 'P14_FULL_STATE_META' else 'issues'
                output[target_list].append('metadata differs: ' + marker)
        aa = {p.name: p for p in (left / 'oracle').glob('*.bin')}
        bb = {p.name: p for p in (right / 'oracle').glob('*.bin')}
        if not natural and aa.keys() != bb.keys():
            raise RuntimeError('RAW_FIELD_SET_DIFFERS')
        numeric_suffixes = ('hc_entry_R', 'hc_write_R', 'body_bo', 'body_inj', 'chunk_end_R',
                            'initial_gdn_state', 'initial_ple_hist', 'initial_ple_tokens', 'cached_grs',
                            'cached_xn16', 'cached_xn16_lo', 'hc_grs', 'hc_xn', 'hc_xn16', 'hc_xn16_lo',
                            'hc_lo', 'hc_lo16', 'hc_lo16_lo', 'hc_gated', 'hc_mixed', 'hc_mixed_h',
                            'hc_mixed_bf', 'hc_mixed_bf_lo', 'hc_inj')
        def numerical(name):
            return any(name.endswith('-' + field + '.bin') for field in numeric_suffixes)
        missing = sorted(aa.keys() ^ bb.keys())
        if any(numerical(name) for name in missing):
            raise RuntimeError('NUMERICAL_FIELD_SET_DIFFERS')
        output['execution_changes'].extend('field coverage differs: ' + name for name in missing)
        for name in sorted(aa.keys() & bb.keys()):
            size = aa[name].stat().st_size
            if bb[name].stat().st_size != size:
                output['raw'].append({'field': name, 'bitwise_equal': False, 'shape_mismatch': True})
                continue
            value = local_analysis.compare_files(aa[name], bb[name], size)
            value['field'] = name
            output['raw'].append(value)
        output['raw_differences'] = [x['field'] for x in output['raw'] if not x['bitwise_equal']]
        output['numerical_raw_differences'] = [name for name in output['raw_differences'] if numerical(name)]
        output['execution_changes'].extend('dispatch/geometry differs: ' + name for name in output['raw_differences'] if not numerical(name))
        output['logits'] = local_analysis.compare_files(left / 'think-4096.f32', right / 'think-4096.f32', 248320 * 4, 4)
        ranges = json.loads((left / 'MTP_RANGES.json').read_text())['ranges']
        if ranges != json.loads((right / 'MTP_RANGES.json').read_text())['ranges']:
            raise RuntimeError('MTP_EFFECTIVE_RANGES_DIFFER: no complete state parity claim')
        output['state'] = compare_session.compare(left / 'session.bin', right / 'session.bin', draft_ranges=ranges)
        changed = output['numerical_raw_differences'] if natural else output['raw_differences']
        if changed or not output['logits']['bitwise_equal'] or output['state']['status'] != 'PASS':
            output['issues'].append('effective bytes differ or state not proven')
        if not output['issues']:
            output['status'] = 'PASS'
        elif natural and (changed or not output['logits']['bitwise_equal'] or output['state'].get('first_different_field') or
                          'metadata differs: P14_FULL_STATE_META' in output['issues']):
            output['status'] = 'NATURAL_C_NUMERICAL_DIFFERENCE'
    except Exception as exc:
        output['issues'].append(str(exc))
    dest = {'replay-a': 'AA_ANALYSIS.json', 'replay-b': 'AB_ANALYSIS.json',
            'natural-c': 'AC_ANALYSIS.json', 'replay-control': 'CC_CONTROL_ANALYSIS.json'}[other]
    dump(TASK / dest, output)
    print(json.dumps({'status': output['status'], 'issues': output['issues'], 'output': dest}), flush=True)
    return output


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'build', 'run', 'analyze'])
    p.add_argument('--name', choices=PHASES)
    args = p.parse_args()
    if args.action == 'prepare': prepare_full()
    elif args.action == 'build': build()
    elif args.action == 'run': run(args.name)
    else: analyze_pair(args.name)
