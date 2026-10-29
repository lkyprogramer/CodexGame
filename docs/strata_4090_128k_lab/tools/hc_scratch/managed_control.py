"""P20: one managed-HC replay against the frozen P19 natural-C16K capture."""
from datetime import datetime, timezone
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

import boundary
import managed_control_patch
from lab.assets import verify as verify_assets
from lab.core import dump, sha256, load_config, gpu_lock, gpu_inventory, port_free
from lab.runner import make_run_config, wait_released

ROOT = boundary.ROOT
PRIOR = boundary.TASK
OLD_TREE = boundary.TREE
TASK = ROOT / 'workspace/combination/hc-managed-control-20261029'
TREE = ROOT / 'workspace/trees/hc-managed-control-20261029'
MARKER = {'T': 16384, 'bytes': 1038091264, 'managed_allocations': 4, 'device': 0,
          'managed_memory': 1, 'concurrent_managed_access': 1, 'cache_memory_type': 2,
          'region_memory_type': 2, 'cache_slots': 10272, 'loan_unchanged': True}


def validate_managed(rows):
    if rows != [MARKER]:
        raise RuntimeError('MANAGED_CONTROL_NOT_ACTUALLY_EXECUTED')


def prepare():
    if TASK.exists() or TREE.exists():
        raise RuntimeError('MANAGED_STAGE_EXISTS')
    if sha256(PRIOR / 'RAW_MANIFEST.json') != 'fab9a5500fd34e75fa99151386c89a70903336ac76d68584371129b156371f54':
        raise RuntimeError('P19_MANIFEST_DRIFT')
    manifest = json.loads((PRIOR / 'RAW_MANIFEST.json').read_text())
    reference_files = {n: r for n, r in manifest['files'].items() if n.startswith('c-16384/')}
    for n, r in reference_files.items():
        if (PRIOR / n).stat().st_size != r['bytes'] or sha256(PRIOR / n) != r['sha256']:
            raise RuntimeError('REFERENCE_RAW_DRIFT: ' + n)
    if json.loads((PRIOR / 'c-16384/RUN_RESULT.json').read_text())['status'] != 'CAPTURE_VALID':
        raise RuntimeError('REFERENCE_NOT_VALID')
    boundary.validate(PRIOR / 'c-16384', 16384)
    old_build = json.loads((PRIOR / 'BUILD_COMPLETE.json').read_text())
    if sha256(OLD_TREE / 'build-lab/strata') != old_build['exe_sha256'] or any(sha256(OLD_TREE / n) != h for n, h in old_build['source'].items()):
        raise RuntimeError('P19_BUILD_DRIFT')
    c = load_config(PRIOR / 'config.json')
    before = json.loads((PRIOR / 'FINAL_PROTECTION.json').read_text())
    service = boundary.reference.baseline.combo.assert_service_inactive()
    boundary.reference.baseline.combo.assert_protected(c, before['protected'])
    assets = verify_assets(c)
    with gpu_lock(c['gpu_lock_workspace']):
        port_free(18089)
        if gpu_inventory('0')['compute_processes']:
            raise RuntimeError('GPU_NOT_IDLE')
        TASK.mkdir()
    dump(TASK / 'production-before.json', {'service': service, 'protected': before['protected']})
    dump(TASK / 'ASSETS.json', {'metadata': assets, 'fresh_full_content_hash': False})
    inputs = json.loads((PRIOR / 'inputs.json').read_text())['16384']
    registration = {'registered_utc': datetime.now(timezone.utc).isoformat(),
        'authority': 'user: solve16K independent HC memory limit, same cache/residency/actual dispatch; then staged gates',
        'reference': str(PRIOR / 'c-16384'), 'reference_content_files_verified': len(reference_files),
        'reference_content_bytes_verified': sum(r['bytes'] for r in reference_files.values()),
        'reference_manifest_sha256': sha256(PRIOR / 'RAW_MANIFEST.json'), 'tokens': inputs,
        'scope': 'one GEN1 independent managed-HC control; no natural C rerun; strict original P19 full raw/logit/valid-state comparison',
        'native_GEN1_attempt_limit': 1, 'automatic_retries': 0, 'first_failure_stops': True,
        'change': 'four additional independent HC arrays use cudaMallocManaged; same padded bytes; original cudaMalloc cache/region remain Device',
        'capabilities': MARKER, 'fallback': 'none; unsupported device or wrong pointer types reject',
        'unchanged': 'all P19 args/env except control activation, executable and output paths; kernels/shapes/math/loan/host_res/actual dispatch unchanged',
        'build': 'reuse frozen P19 objects/libraries; rebuild only prefill.cpp object; replace that archive member and relink with identical original link flags',
        'later_gates': 'only strict16K PASS permits separately registered C lifecycle/sanitizer, then at most one A/C100K cost pair; signal required before original formal performance plan',
        'limits': {'wall_seconds': 1800, 'gpu_c': 85, 'available_mib': 4096, 'context': 131072, 'safety_tokens': 4096},
        'timing': 'managed migration and synchronous capture are diagnostic only; zero formal performance samples',
        'old_control_FAIL': 'preserved unchanged; no reinterpretation as PASS', 'original_six_status': 'FAIL_UNCHANGED',
        'documentation': 'https://docs.nvidia.com/cuda/archive/12.3.2/cuda-runtime-api/group__CUDART__MEMORY.html',
        'production_writes': False, 'deployment': False}
    dump(TASK / 'PREREGISTRATION.json', registration)
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'sha256': sha256(TASK / 'PREREGISTRATION.json'), 'gpu_requests_started': False})
    subprocess.run(['git', '-C', str(ROOT / 'workspace/repo'), 'worktree', 'add', '--detach', str(TREE),
                    '5e8a4cca7d690ac60ca37eb09e7d0e010099ad6d'], check=True)
    port = json.loads((boundary.P13 / 'P6_SOURCE.json').read_text())['python_port']['files']
    for n in port:
        shutil.copy2(OLD_TREE / n, TREE / n)
    p = TREE / 'src/prefill/prefill.cpp'; old = (OLD_TREE / 'src/prefill/prefill.cpp').read_text()
    new = managed_control_patch.transform(old); p.write_text(new)
    (TASK / 'prefill.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
          fromfile='a/src/prefill/prefill.cpp', tofile='b/src/prefill/prefill.cpp')))
    shutil.copy2(OLD_TREE / 'src/program/generate.cpp', TREE / 'src/program/generate.cpp')
    c['deployed_repo'] = str(TREE); dump(TASK / 'config.json', c)
    print('P20_PREREGISTERED', sha256(TASK / 'PREREGISTRATION.json'), flush=True)


def build():
    if (TASK / 'BUILD_COMPLETE.json').exists():
        raise RuntimeError('P20_BUILD_EXISTS')
    old = OLD_TREE / 'build-lab'; new = TREE / 'build-lab'; new.mkdir()
    entries = json.loads((old / 'compile_commands.json').read_text())
    entry = next(r for r in entries if r['file'].endswith('/src/prefill/prefill.cpp'))
    compile_cmd = shlex.split(entry['command'])
    compile_cmd[compile_cmd.index('-o') + 1] = str(new / 'prefill.cpp.o')
    compile_cmd[compile_cmd.index('-c') + 1] = str(TREE / 'src/prefill/prefill.cpp')
    with (TASK / 'compile.log').open('w') as log:
        subprocess.run(compile_cmd, cwd=entry['directory'], stdout=log, stderr=subprocess.STDOUT, check=True)
    archive = 'libstrata_prefill.a'
    before_sha = sha256(old / archive)
    shutil.copy2(old / archive, new / archive)
    members = subprocess.check_output(['/usr/bin/ar', 't', str(old / archive)], text=True).splitlines()
    if members.count('prefill.cpp.o') != 1:
        raise RuntimeError('ARCHIVE_MEMBER_AMBIGUOUS')
    subprocess.run(['/usr/bin/ar', 'r', str(new / archive), str(new / 'prefill.cpp.o')], check=True)
    subprocess.run(['/usr/bin/ranlib', str(new / archive)], check=True)
    if subprocess.check_output(['/usr/bin/ar', 't', str(new / archive)], text=True).splitlines() != members:
        raise RuntimeError('ARCHIVE_MEMBER_SET_CHANGED')
    for name in members:
        if name != 'prefill.cpp.o':
            a = subprocess.check_output(['/usr/bin/ar', 'p', str(old / archive), name])
            b = subprocess.check_output(['/usr/bin/ar', 'p', str(new / archive), name])
            if a != b: raise RuntimeError('REUSED_ARCHIVE_MEMBER_CHANGED: ' + name)
    ninja = '/home/hhtele/strata-0.1.43.1/.venv/bin/ninja'
    last = subprocess.check_output([ninja, '-t', 'commands', 'strata'], cwd=old, text=True).splitlines()[-1]
    if not last.startswith(': && ') or not last.endswith(' && :'):
        raise RuntimeError('LINK_RULE_SHAPE')
    link_cmd = shlex.split(last[5:-5]); link_cmd[link_cmd.index('-o') + 1] = str(new / 'strata')
    link_cmd = [str(new / archive) if s == archive else s for s in link_cmd]
    reused = {str((old / s).resolve()): sha256((old / s).resolve()) for s in link_cmd
              if s.endswith(('.a', '.o')) and (old / s).resolve() != (new / archive).resolve()}
    with (TASK / 'link.log').open('w') as log:
        subprocess.run(link_cmd, cwd=old, stdout=log, stderr=subprocess.STDOUT, check=True)
    if sha256(old / archive) != before_sha:
        raise RuntimeError('ORIGINAL_ARCHIVE_MUTATED')
    dump(TASK / 'BUILD_COMPLETE.json', {'kind': 'P19_OBJECT_REUSE_ONE_CPP_OVERLAY',
         'exe_sha256': sha256(new / 'strata'), 'source': {n: sha256(TREE / n) for n in ('src/prefill/prefill.cpp', 'src/program/generate.cpp')},
         'compile_argv': compile_cmd, 'link_argv': link_cmd, 'working_directory': str(old),
         'original_archive_sha256': before_sha, 'new_archive_sha256': sha256(new / archive),
         'unchanged_archive_members': len(members) - 1, 'reused_link_inputs': reused,
         'patch_sha256': sha256(TASK / 'prefill.patch')})
    print('P20_BUILD_COMPLETE', flush=True)


def run():
    if sha256(TASK / 'PREREGISTRATION.json') != json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())['sha256']:
        raise RuntimeError('REGISTRATION_DRIFT')
    folder = TASK / 'control-16384'; folder.mkdir()
    receipt = json.loads((TASK / 'BUILD_COMPLETE.json').read_text())
    if sha256(TREE / 'build-lab/strata') != receipt['exe_sha256'] or any(sha256(TREE / n) != h for n, h in receipt['source'].items()):
        raise RuntimeError('NEW_BUILD_DRIFT')
    c = load_config(TASK / 'config.json')
    c['extra_frozen_env'].update(STRATA_LAB_HC_REGION='1', STRATA_LAB_HC_KEEP_LOAN='0', STRATA_LAB_HC_MANIFEST='1',
        STRATA_LAB_BOUNDARY_TRACE='1', STRATA_LAB_ORACLE_DIR=str(folder / 'oracle'),
        STRATA_LAB_ORACLE_REF=str(PRIOR / 'c-16384/oracle'), STRATA_LAB_HC_PRIVATE_CONTROL='1')
    cfg = make_run_config(c, TREE, 'cfg', {}, folder)
    old_plan = json.loads((PRIOR / 'c-16384/plan.json').read_text())
    env = {k: v for k, v in cfg['env'].items() if k.startswith('STRATA_')}
    mutable = {'STRATA_LAB_ORACLE_DIR', 'STRATA_LAB_ORACLE_REF', 'STRATA_LAB_HC_PRIVATE_CONTROL'}
    if cfg['args'] != old_plan['args'] or {k: v for k, v in env.items() if k not in mutable} != {k: v for k, v in old_plan['env'].items() if k not in mutable}:
        raise RuntimeError('FROZEN_CONFIGURATION_CHANGED')
    boundary.reference.baseline.assert_kvres(cfg)
    before = json.loads((TASK / 'production-before.json').read_text())
    boundary.reference.baseline.combo.assert_service_inactive()
    boundary.reference.baseline.combo.assert_protected(c, before['protected']); verify_assets(c)
    selected = json.loads((TASK / 'PREREGISTRATION.json').read_text())['tokens']
    if sha256(Path(selected['path'])) != selected['sha256']: raise RuntimeError('TOKEN_DRIFT')
    (folder / 'empty.ids').write_text('\n')
    dump(folder / 'plan.json', {'tokens': selected, 'args': cfg['args'], 'env': env, 'build': receipt,
         'registration_sha256': sha256(TASK / 'PREREGISTRATION.json'), 'performance_sample': False})
    result = {'status': 'FAIL', 'error': None}
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            boundary.reference.baseline.combo.assert_service_inactive()
            dump(folder / 'cooldown.json', boundary.reference.baseline.combo.wait_cool(c))
            try:
                boundary.reference.run_native(c, folder, [{'name': selected['name'], 'tokens': selected,
                    'prefix': {'path': str(folder / 'empty.ids')}}], save_session=True)
            finally: wait_released(c)
        validate_managed(boundary.records(folder, 'P20_MANAGED_HC'))
        result.update(capture=boundary.validate(folder, 16384, control=True), status='CAPTURE_VALID')
    except Exception as exc:
        result['error'] = str(exc)
    finally:
        dump(folder / 'RUN_RESULT.json', result)
        dump(folder / 'production-after.json', {'service': boundary.reference.baseline.combo.assert_service_inactive(),
             'protected': boundary.reference.baseline.combo.assert_protected(c, before['protected']), 'gpu': gpu_inventory('0')})
    print(json.dumps(result), flush=True)
    return result


def analyze():
    left, right = PRIOR / 'c-16384', TASK / 'control-16384'
    out = {'status': 'FAIL', 'issues': [], 'formal_performance_samples': 0}
    try:
        if json.loads((right / 'RUN_RESULT.json').read_text())['status'] != 'CAPTURE_VALID':
            raise RuntimeError('MANAGED_CAPTURE_NOT_VALID')
        boundary.validate(left, 16384); boundary.validate(right, 16384, True)
        validate_managed(boundary.records(right, 'P20_MANAGED_HC'))
        for marker in ('P14_FULL_MTP_RANGE', 'P14_FULL_MTP_BATCH', 'P14_FULL_DRAFT_CALL', 'P14_FULL_STATE_META'):
            if boundary.records(left, marker) != boundary.records(right, marker): raise RuntimeError('METADATA_DIFFERS: ' + marker)
        a, b = ({p.name: p for p in (f / 'oracle').glob('*.bin')} for f in (left, right))
        if a.keys() != b.keys(): raise RuntimeError('RAW_FIELD_SET_DIFFERS')
        for n, p in a.items():
            if p.stat().st_size != b[n].stat().st_size: raise RuntimeError('RAW_SHAPE_DIFFERS: ' + n)
            row = boundary.raw_analysis.compare_files(p, b[n], p.stat().st_size)
            if not row['bitwise_equal']: raise RuntimeError('RAW_DIFFERS: ' + n)
        out['raw'] = {'records': len(a), 'bytes': sum(p.stat().st_size for p in a.values()), 'bytewise_equal': True}
        out['logits'] = boundary.raw_analysis.compare_files(left / 'boundary-16384.f32', right / 'boundary-16384.f32', 248320 * 4, 4)
        out['state'] = boundary.compare_session.compare(left / 'session.bin', right / 'session.bin', draft_ranges=[[0, 16384]])
        if not out['logits']['bitwise_equal'] or not out['logits']['all_finite'] or out['state']['status'] != 'PASS':
            raise RuntimeError('LOGITS_OR_VALID_STATE_DIFFERS')
        out['status'] = 'PASS'
    except Exception as exc: out['issues'].append(str(exc))
    dump(TASK / 'PAIR-16384.json', out)
    print(json.dumps({k: v for k, v in out.items() if k != 'state'}), flush=True)
    return out


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('mode', choices=['prepare', 'build', 'run', 'analyze'])
    a = p.parse_args()
    if a.mode == 'prepare': prepare()
    elif a.mode == 'build': build()
    elif a.mode == 'run':
        if run()['status'] != 'CAPTURE_VALID': sys.exit(2)
    elif analyze()['status'] != 'PASS': sys.exit(2)
