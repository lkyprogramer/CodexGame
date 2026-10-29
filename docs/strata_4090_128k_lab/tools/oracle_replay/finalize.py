"""Close only the oracle stage after the user stopped further candidate validation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import prepare
from lab.core import dump, sha256, load_config, gpu_inventory, gpu_lock, port_free


def finalize():
    task, tree = prepare.TASK, prepare.TREE
    c = load_config(task / 'config.json')
    aa = json.loads((task / 'full-request/AA_ANALYSIS.json').read_text())
    if aa['status'] != 'PASS':
        raise RuntimeError('FULL_REQUEST_ORACLE_NOT_PASS')
    local = {name: json.loads((task / name / 'ANALYSIS.json').read_text())['status']
             for name in ('aa-3', 'negative-input', 'negative-dispatch', 'negative-mapping')}
    if local != {'aa-3': 'PASS', 'negative-input': 'NEGATIVE_CONTROL_PASS',
                 'negative-dispatch': 'NEGATIVE_CONTROL_PASS', 'negative-mapping': 'NEGATIVE_CONTROL_PASS'}:
        raise RuntimeError('LOCAL_ORACLE_NOT_PASS')
    if (task / 'full-request/replay-b').exists() or (task / 'full-request/natural-c').exists():
        raise RuntimeError('UNEXPECTED_CANDIDATE_PHASE')
    before = json.loads((task / 'production-before.json').read_text())
    with gpu_lock(c['gpu_lock_workspace']):
        service = prepare.baseline.combo.assert_service_inactive()
        protected = prepare.baseline.combo.assert_protected(c, before['file_sha256'])
        gpu = gpu_inventory('0')
        port_free(18089)
        if gpu['compute_processes']:
            raise RuntimeError('GPU_NOT_RELEASED')
        owned = [json.loads(p.read_text()) for p in task.rglob('owned-process.json')]
        if any((Path('/proc') / str(p['pid'])).exists() for p in owned):
            raise RuntimeError('OWNED_PID_NOT_EXITED')
        old = json.loads((task / 'P13_RAW_PROTECTION.json').read_text())
        for name, digest in old['files'].items():
            if sha256(prepare.P13 / name) != digest:
                raise RuntimeError('PRIOR_RAW_DRIFT: ' + name)
        source = prepare.baseline.source_receipt(Path(load_config(prepare.P6 / 'config.json')['deployed_repo']), prepare.P6)
        assets = prepare.verify_assets(c)
        evidence = task / 'full-request/source-evidence'
        evidence.mkdir(exist_ok=True)
        for name in ('src/prefill/prefill.cpp', 'src/program/generate.cpp'):
            shutil.copy2(tree / name, evidence / Path(name).name)
        binaries = task / 'binaries'
        binaries.mkdir(exist_ok=True)
        shutil.copy2(tree / 'build-lab/strata', binaries / 'strata-full-request-oracle')
        phases = sorted(p.parent for p in task.rglob('owned-process.json'))
        telemetry = [json.loads((p / 'telemetry.json').read_text()) for p in phases]
        samples = [s for t in telemetry for s in t['samples']]
        protection = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'production_service': service,
            'file_sha256': protected, 'gpu': gpu, 'port_18089_free': True, 'gpu_lock_acquired': True,
            'owned_pids_exited': [p['pid'] for p in owned], 'prior_P13_raw_files_unchanged': old['count'],
            'P6_source': source, 'asset_metadata_verified': len(assets), 'fresh_weight_content_hash': False,
            'resources': {'samples': len(samples), 'peak_gpu_c': max(float(s['gpu']['temperature_c']) for s in samples),
                'peak_gpu_mib': max(float(s['gpu']['used_mib']) for s in samples),
                'min_available_mib': min(s['mem_available_mib'] for s in samples),
                'guard_reasons': [t['abort_reason'] for t in telemetry if t['abort_reason']]}}
        dump(task / 'FINAL_PROTECTION.json', protection)
        completion = {'state': 'ORACLE_VALIDATED_STOPPED_AT_USER_REQUEST', 'scope': 'one frozen 4095-token GEN1; actual main prefill T4090',
            'local_FFN': local, 'full_request_AA': aa['status'], 'native_requests': len(phases),
            'local_phase_requests': 6, 'full_request_requests': 2, 'performance_samples': 0,
            'candidate_B_requests': 0, 'candidate_C_requests': 0, 'original_six_status': 'FAIL_UNCHANGED',
            'preserved_execution_failures': {'aa-1': 'stale remote runner precreated output directory',
                'aa-2': 'normal exit /proc race; run remained FAIL, all local raw bytes matched'},
            'stop_authority': 'user: complete numerical replay oracle, report, stop subsequent exploration/validation',
            'not_run': ['HC candidate B/C', 'HC boundary/lifecycle/sanitizer', 'cost/performance', 'GROUP_SCRATCH', 'IMMA'],
            'production_modified': False, 'deployment': False}
        dump(task / 'COMPLETION.json', completion)
    # Raw snapshots and both binaries stay in this isolated archive on host29.
    files = {str(p.relative_to(task)): {'sha256': sha256(p), 'bytes': p.stat().st_size}
             for p in sorted(task.rglob('*')) if p.is_file() and p.name != 'RAW_MANIFEST.json'}
    dump(task / 'RAW_MANIFEST.json', {'files': files, 'count': len(files),
         'bytes': sum(v['bytes'] for v in files.values()), 'remote_root': str(task),
         'export': 'local copy contains non-bin/non-executable metadata, source and logs; raw bytes retained on host29'})
    print(json.dumps({'completion': completion, 'protection': protection['resources'], 'raw_files': len(files)}), flush=True)


if __name__ == '__main__':
    finalize()
