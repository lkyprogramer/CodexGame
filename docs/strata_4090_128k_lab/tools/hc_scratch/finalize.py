"""Close the stopped P13 qualification, restore its non-diagnostic candidate and attest protection."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/v027'), str(Path(__file__).parent)]
import prepare
import analyze
import make_patch
from lab.core import dump, gpu_inventory, load_config, port_free, sha256


def finalize():
    task, tree = prepare.TASK, prepare.TREE
    c = load_config(task / 'config.json')
    before = json.loads((task / 'production-before.json').read_text())
    prepare.base.combo.assert_service_inactive()
    protected = prepare.base.combo.assert_protected(c, before['file_sha256'])
    source = prepare.base.source_receipt(Path(load_config(prepare.P6 / 'config.json')['deployed_repo']), prepare.P6)
    gpu = gpu_inventory('0')
    port_free(18089)
    if gpu['compute_processes']:
        raise RuntimeError('LAB_RESOURCES_STILL_ACTIVE')
    processes = [json.loads(f.read_text()) for f in task.glob('*/owned-process.json')]
    if any((Path('/proc') / str(r['pid'])).exists() for r in processes):
        raise RuntimeError('OWNED_PID_STILL_PRESENT')
    prior = json.loads((task / 'prior-evidence-before.json').read_text())
    counts = {}
    for group, files in prior.items():
        for name, digest in files.items():
            if sha256(ROOT / name) != digest:
                raise RuntimeError('PRIOR_EVIDENCE_DRIFT: ' + name)
        counts[group] = len(files)
    src = tree / make_patch.RELATIVE
    diagnostic = json.loads((task / 'DIAGNOSTIC_PATCH_V2.json').read_text())
    if sha256(src) != diagnostic['after_sha256']:
        raise RuntimeError('DIAGNOSTIC_SOURCE_DRIFT')
    shutil.copy2(src, task / 'source-evidence/prefill-hc-diag-v2.cpp')
    shutil.copy2(tree / 'build-lab/strata', task / 'binaries/strata-hc-diagnostic-v2')
    plain = make_patch.transform((Path(source['native']['exe']).parents[1] / make_patch.RELATIVE).read_text())
    src.write_text(plain)
    shutil.copy2(task / 'binaries/strata-hc-only', tree / 'build-lab/strata')
    expected = json.loads((task / 'BUILD_COMPLETE.json').read_text())
    if sha256(src) != expected['patch']['after_sha256'] or sha256(tree / 'build-lab/strata') != expected['exe_sha256']:
        raise RuntimeError('CANDIDATE_RESTORE_MISMATCH')
    shutil.copy2(src, task / 'source-evidence/prefill-hc-only.cpp')
    for name in ('CMakeCache.txt', 'compile_commands.json'):
        shutil.copy2(tree / 'build-lab' / name, task / 'source-evidence' / name)
    generate = Path(source['native']['exe']).parents[1] / 'src/program/generate.cpp'
    lines = generate.read_text().splitlines()
    (task / 'source-evidence/generate-loan.cpp.txt').write_text(
        'Frozen P6 src/program/generate.cpp SHA256 ' + sha256(generate) + '\n' +
        '\n'.join(f'{i+1}: {lines[i]}' for i in range(9329,9357)) + '\n')
    result = analyze.analyze(task)
    result['raw_AA'] = json.loads((task / 'RAW_AA_COMPARISON.json').read_text())
    result['decision'] = 'BLOCKED_NUMERICAL_ORACLE'
    result['NOT_RUN'] = ['B/C candidate compute parity and valid-state comparison', 'candidate redzones/poison/compute-sanitizer',
                         'short-long-short, restore, cancel lifecycle on candidate', 'retained-expert route/copy/wait mechanism',
                         'formal paired TTFT/wall/full-decode', 'effective frequency', 'request/task-quality adoption']
    result['effective_chunk_correction'] = {'4095_input': 'observed T4090 prefill in diagnostic phases',
        '16384_input_P6_pair': 'observed 88+16295 prefill, not one16384 chunk; small-block CPUshare cannot be excluded',
        '16384_allocation': 'actual carve sizing at startup, not proof of a computed16384 chunk'}
    dump(task / 'ANALYSIS.json', result)
    telemetry = [json.loads(f.read_text()) for f in task.glob('*/telemetry.json')]
    samples = [s for t in telemetry for s in t['samples']]
    protection = {'service': subprocess.check_output(['systemctl','show','openclaw-qwen38-next.service',
                  '-p','ActiveState','-p','SubState','-p','UnitFileState'],text=True).splitlines(),
                  'file_sha256': protected, 'prior_evidence_unchanged': counts, 'owned_pids_exited': [r['pid'] for r in processes],
                  'gpu': gpu, 'port_18089_free': True, 'P6_source': source,
                  'candidate_restored': {'source_sha256': sha256(src), 'exe_sha256': sha256(tree/'build-lab/strata'),
                                         'default': 'HC off; isolated tree only'},
                  'resources': {'samples': len(samples), 'abort_reasons': [t['abort_reason'] for t in telemetry if t['abort_reason']],
                                'peak_gpu_c': max(float(s['gpu']['temperature_c']) for s in samples),
                                'peak_gpu_mib': max(float(s['gpu']['used_mib']) for s in samples),
                                'min_available_mib': min(s['mem_available_mib'] for s in samples)}}
    dump(task / 'FINAL_PROTECTION.json', protection)
    dump(task / 'BINARY_ARCHIVE.json', {f.name: {'bytes': f.stat().st_size, 'sha256': sha256(f)}
                                      for f in sorted((task/'binaries').iterdir())})
    dump(task / 'COMPLETION.json', {'state': 'QUALIFICATION_STOPPED', 'decision': result['decision'],
         'native_requests': 8, 'startup_only_phases': 2, 'formal_performance_samples': 0,
         'original_six_status': 'FAIL_UNCHANGED', 'production_changed': False, 'deployment': False})
    # Executables remain in the isolated host archive. Everything else is copied and checked at both ends.
    files = {str(f.relative_to(task)): sha256(f) for f in sorted(task.rglob('*'))
             if f.is_file() and 'binaries' not in f.parts and f.name != 'RAW_MANIFEST.json'}
    dump(task / 'RAW_MANIFEST.json', {'files': files, 'count': len(files),
         'bytes': sum((task/f).stat().st_size for f in files), 'excluded': ['binaries: remote archive with BINARY_ARCHIVE.json identities']})
    return {'decision': result['decision'], 'protection': protection['resources'], 'raw_count': len(files),
            'old_evidence_count': sum(counts.values())}


if __name__ == '__main__':
    print(json.dumps(finalize()), flush=True)
