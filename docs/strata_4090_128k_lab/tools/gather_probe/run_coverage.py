"""Reuse P5's passive counters on the frozen P6 configuration; candidate off."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools/gu_probe'), str(ROOT / 'tools/v027'), str(ROOT)]
import run_profile as prior
import run_baseline as baseline
from lab.core import dump, sha256

TASK = ROOT / 'workspace/gather-probe-20261028'
TREE = ROOT / 'workspace/trees/gather-probe-20261028'


def run():
    p6 = ROOT / 'workspace/combination/v027-20261028'
    baseline.source_receipt(ROOT / 'workspace/trees/v027-20261028', p6)
    build = json.loads((TASK / 'BUILD_COMPLETE.json').read_text())
    if sha256(TREE / 'build-lab/strata') != build['engine_sha256']:
        raise RuntimeError('P12_BUILD_DRIFT')
    validate = prior.boundary.combo.validate_startup
    def validate_live(server, arm):
        receipt = baseline.activation_receipt(server)
        if receipt['expert_cache_slots'] != 10272:
            raise RuntimeError('P6_AUTO_CACHE_CAPACITY_DRIFT')
        live = Path(f'/proc/{server.engine_audit[0]["pid"]}/environ').read_bytes().split(b'\0')
        live = dict(x.decode().split('=', 1) for x in live if x.startswith(b'STRATA_'))
        expected = {**baseline.combo.FROZEN_ENV, **baseline.CONSERVATIVE}
        if any(live.get(k) != v for k, v in expected.items()):
            raise RuntimeError('ACTUAL_ENGINE_ENV_DRIFT')
        if live.get('STRATA_LAB_GU_GATHER', '0') != '0' or live.get('STRATA_IQ_MT_MIN', '2') != '2':
            raise RuntimeError('GATHER_OR_MT_MIN_DRIFT')
        receipt['live_strata_env'] = live
        return receipt
    prior.boundary.combo.validate_startup = validate_live
    try:
        result = prior.run(argparse.Namespace(config=str(TASK / 'config.json'), tree=str(TREE),
                            corpus=str(TASK / 'coverage-corpus.json'), out=str(TASK / 'coverage'), capture_type=None))
    finally:
        prior.boundary.combo.validate_startup = validate
    folder = TASK / 'coverage'
    response = json.loads((folder / 'result.json').read_text())
    cases = json.loads((TASK / 'coverage-corpus.json').read_text())['cases']
    rows = response['requests']
    if response['error'] or response['abort_reason'] or [x['name'] for x in rows] != ['qualification', *[c['id'] for c in cases]]:
        raise RuntimeError('COVERAGE_REQUEST_COMPLETION')
    if any(not x['score']['pass'] or x['response_error'] for x in rows) or any(x['metrics']['generated_tokens'] != 2048 for x in rows[1:]):
        raise RuntimeError('COVERAGE_FIXED_OUTPUT_OR_SCORE')
    startup = baseline.activation_receipt(type('Server', (), {'folder': folder})())
    total = json.loads((folder / 'profile.json').read_text())
    qualification = prior.read_profile(folder / 'qualification.profile.bin')
    formats = {}
    for dtype, data in total['formats'].items():
        bins = {}
        for nt, values in data['nt'].items():
            q = qualification['formats'].get(dtype, {}).get('nt', {}).get(nt, {})
            bins[nt] = {key: value - q.get(key, 0) for key, value in values.items()}
            if bins[nt]['entries'] != bins[nt]['jobs'] * int(nt) or bins[nt]['rows'] != bins[nt]['jobs'] * 640:
                raise RuntimeError('COVERAGE_ACCOUNTING')
        formats[dtype] = bins
    selected = formats.get('21', {}).get('1', {})
    if selected.get('jobs', 0) <= 0:
        raise RuntimeError('IQ3_S_NT1_NOT_OBSERVED')
    logs = (folder / 'engine.log').read_text()
    offsets = {int(x) for x in re.findall(r'LAB_GU_ORACLE type=21 nt=1 path=ggml dot_offset=(\d+)', logs)}
    symbols = subprocess.check_output(['nm', '-n', '--defined-only', str(TREE / 'build-lab/strata')], text=True)
    expected = {int(line.split()[0], 16) for line in symbols.splitlines()
                if line.split()[-1] == 'ggml_vec_dot_iq3_s_q8_K'}
    if not offsets or offsets != expected:
        raise RuntimeError('ACTUAL_ORACLE_SYMBOL_MISMATCH')
    denominator = sum(v.get('1', {}).get('worker_ns', 0) for v in formats.values())
    dump(TASK / 'COVERAGE.json', {'state': 'PASS', 'formats': formats,
        'IQ3_S_nt1_worker_fraction': selected['worker_ns'] / denominator,
        'oracle_offsets': sorted(offsets), 'oracle_symbol': 'ggml_vec_dot_iq3_s_q8_K',
        'activation': startup, 'candidate': 'off', 'raw_result': result,
        'scope': 'two full-config requests minus qualification; not strict decode-only or performance evidence'})
    return {'state': 'PASS', 'IQ3_S_nt1': selected, 'worker_fraction': selected['worker_ns'] / denominator}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
