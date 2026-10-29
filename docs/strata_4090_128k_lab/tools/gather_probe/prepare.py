"""Create the isolated P12 tree and freeze inputs before any gather measurement."""
from pathlib import Path
import json
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/v027')]
import run_baseline as base
from lab.core import dump, hash_obj, load_config, sha256

TASK = ROOT / 'workspace/gather-probe-20261028'
TREE = ROOT / 'workspace/trees/gather-probe-20261028'
P6 = ROOT / 'workspace/combination/v027-20261028'
P5 = ROOT / 'workspace/gu-probe-20261027'


def prepare():
    c = load_config(P6 / 'config.json')
    old_tree = Path(c['deployed_repo'])
    source = base.source_receipt(old_tree, P6)
    before = base.combo.protected_hashes(c)
    base.combo.assert_service_inactive()
    if TASK.exists() or TREE.exists():
        raise RuntimeError('P12_DESTINATION_ALREADY_EXISTS')
    TASK.mkdir()
    dump(TASK / 'production-before.json', {'file_sha256': before, 'service': base.combo.assert_service_inactive()})
    dump(TASK / 'P6_SOURCE.json', source)
    files = json.loads((P5 / 'FIXTURES.json').read_text())['files']
    fixture_dir = P5 / 'capture/fixtures'
    for name, digest in files.items():
        if sha256(fixture_dir / name) != digest:
            raise RuntimeError('P5_FIXTURE_DRIFT ' + name)
    if sha256(P5 / 'fixtures.txt') != json.loads((P5 / 'BENCH_FREEZE.json').read_text())['fixture_index_sha256']:
        raise RuntimeError('P5_FIXTURE_INDEX_DRIFT')
    deps = json.loads((P5 / 'ORACLE_DEPENDENCIES.json').read_text())['files']
    ggml = Path(next(flag.split('=', 1)[1] for flag in source['native']['flags']
                     if flag.startswith('-DSTRATA_GGML_DIR=')))
    actual = {name: sha256(ggml / name) for name in deps}
    if actual != deps:
        raise RuntimeError('P6_GGML_DIFFERS_FROM_P5')
    dump(TASK / 'FIXTURE_IDENTITY.json', {'source': str(fixture_dir), 'files': files,
         'index_sha256': sha256(P5 / 'fixtures.txt'), 'verified_count': len(files),
         'weight_bytes': 397516800, 'batches': 115, 'jobs': 317, 'entries': 509,
         'nt1_jobs': 196, 'scope': 'P5 captured real batches, not all current production requests'})
    dump(TASK / 'ORACLE_DEPENDENCIES.json', {'ggml': str(ggml), 'files': actual})
    shutil.copy2(P5 / 'fixtures.txt', TASK / 'fixtures.txt')
    subprocess.run(['git', '-C', str(ROOT / 'workspace/repo'), 'worktree', 'add', '--detach', str(TREE), base.TAG], check=True)
    for name, digest in source['python_port']['files'].items():
        shutil.copy2(old_tree / name, TREE / name)
        assert sha256(TREE / name) == digest
    c['deployed_repo'] = str(TREE)
    c['ggml_dir'] = str(ggml)
    c['request_timeout_s'] = 300
    c['gpu_monitor_interval_s'] = 1
    dump(TASK / 'config.json', c)
    cases = json.loads((ROOT / 'workspace/combination/ada-delta-20261028/cases.json').read_text())
    for case in cases:
        assert case['request_sha256'] == hash_obj(case['body']) and case['fixed_output'] == 2048
    dump(TASK / 'coverage-corpus.json', {'cases': cases, 'corpus_sha256': hash_obj(cases)})
    dump(TASK / 'PREREGISTRATION.json', {
        'mechanism': 'IQ3_S nt1: replace only two scalar codebook vector constructions with AVX2 gather',
        'oracle': 'actual linked ggml vec_dot; P6 compiler and dependency identity',
        'source': base.TAG, 'config': 'P6 complete conservative configuration including EXACT6 and Python reply/PT port',
        'qualification': 'two original P3/P11 fixed2048 requests with candidate disabled; counters are not performance evidence',
        'candidate': 'type21 nt1 no tail only; original arithmetic and ISA gates preserved; no VNNI combination',
        'correctness': 'codebook index/lane parity, actual ggml dot and complete ExpertPool byte equality, ISA and actual hits',
        'primary': 'full GU-SwiGLU-quant-down ExpertPool replay, 15 workers plus host',
        'orders': [['off','on'],['on','off'],['on','off'],['off','on'],['off','on'],['on','off']],
        'pairs': 6, 'warmup_s': 30, 'measurement_s': 60,
        'expansion_gate': 'improvement >=3 percent and paired-round 95 percent CI excludes zero',
        'micro': 'three hot single-core pairs, warm2s measure10s; diagnostic only',
        'frequency': 'root read-only APERF/MPERF; benchmark executes as hhtele; no host settings changed',
        'limits': {'gpu_abort_c': 85, 'min_available_mib': 4096, 'max_context': 131072, 'safety_tokens': 4096},
        'original_six_status': 'FAIL_UNCHANGED', 'request_adoption_gate': 'separate, not passed by CPU probe',
        'production_writes': False, 'deployment': False})
    return {'state': 'PREPARED', 'tree': str(TREE), 'fixture_files': len(files)}


if __name__ == '__main__':
    print(json.dumps(prepare()))
