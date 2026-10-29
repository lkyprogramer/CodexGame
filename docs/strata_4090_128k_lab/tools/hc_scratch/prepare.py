"""Freeze P13 inputs, endpoints and stop rules before any GPU measurement."""
from datetime import datetime, timezone
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/v027')]
import run_baseline as base
from lab.core import dump, hash_obj, load_config, sha256
from lab.tokenizer import StrataCounter

TASK = ROOT / 'workspace/combination/hc-scratch-20261028'
TREE = ROOT / 'workspace/trees/hc-scratch-20261028'
P6 = ROOT / 'workspace/combination/v027-20261028'


def prepare():
    c = load_config(P6 / 'config.json')
    old = Path(c['deployed_repo'])
    source = base.source_receipt(old, P6)
    protected = base.combo.protected_hashes(c)
    service = base.combo.assert_service_inactive()
    if TASK.exists() or TREE.exists():
        raise RuntimeError('P13_DESTINATION_EXISTS')
    TASK.mkdir()
    dump(TASK / 'production-before.json', {'file_sha256': protected, 'service': service})
    dump(TASK / 'P6_SOURCE.json', source)
    cases = json.loads((ROOT / 'workspace/combination/ada-delta-20261028/cases.json').read_text())
    for case in cases:
        assert hash_obj(case['body']) == case['request_sha256'] and case['fixed_output'] == 2048
    append = json.loads((ROOT / 'workspace/combination/dequant-side-20261028/cases.json').read_text())[:2]
    for case in append:
        assert hash_obj(case['request']) == case['body_sha256']
    dump(TASK / 'performance-cases.json', cases)
    dump(TASK / 'append-cases.json', append)
    # Qualification consumes the same exact token IDs; GEN 1 is diagnostic, not a performance sample.
    import os
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    counter = StrataCounter(c['deployed_repo'], c['gguf'], c['template'])
    token_records = []
    for case in cases:
        body = copy.deepcopy(case['body'])
        messages, tools, kwargs = counter.frontend.openai_to_messages(body)
        ids = counter.tokenizer.encode(counter.template.render(messages, tools=tools, **kwargs), parse_special=True)
        assert len(ids) == counter(case['body'])
        path = TASK / (case['id'] + '.ids')
        path.write_text(','.join(map(str, ids)) + '\n')
        token_records.append({'name': case['id'], 'count': len(ids), 'path': str(path), 'sha256': sha256(path)})
    dump(TASK / 'tokens.json', token_records)
    prior = {}
    for name in ('v027-20261028', 'retrieval-rootcause-20261028', 'reference-logits-20261028',
                 'higher-precision-20261028', 'dequant-side-20261028', 'ada-delta-20261028'):
        prior[name] = {str(p.relative_to(ROOT)): sha256(p) for p in sorted((ROOT / 'workspace/combination' / name).rglob('*'))
                       if p.is_file() and '__pycache__' not in p.parts and 'dependencies' not in p.parts and 'reference-build' not in p.parts}
    prior['gather-probe-20261028'] = {str(p.relative_to(ROOT)): sha256(p)
        for p in sorted((ROOT / 'workspace/gather-probe-20261028').rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts and 'build' not in p.parts}
    dump(TASK / 'prior-evidence-before.json', prior)
    registration = {
        'schema': 1, 'registered_utc': datetime.now(timezone.utc).isoformat(), 'source': source,
        'mechanism': 'HC-only alias xn16/lo/lo16/gated into existing GDN/QSA/MoE shared region at unchanged chunk16384',
        'unchanged': ['weights and tokenizer', 'EXACT6', 'KV int8 resident20480', 'spec4/minp0.5', '15 workers plus host',
                      'CPU_SHARE_MAX4096', 'AUTO_MAX16384', 'context131072 safety4096', '#1536/PT',
                      'DEFAULTS026', 'IL89=SIDE=IMMA=KVA=ROUTE_PRIOR=PLE_AUTO_RAM=0', 'kernels and stream/event ordering'],
        'arms': {'A': 'original layout and loan', 'B': 'HC alias, A loan/residency/dispatch; diagnostic only',
                 'C': 'HC alias and actual smaller loan; performance candidate only after its own numerical gate'},
        'qualification': ['actual Alloc counts, padding, maxima, carve/cap, slot granule and resident mappings',
                          'require real slot reduction and retained experts used by frozen requests',
                          'A/A same-token baseline; off vs original P6; B and C bitwise intermediate/logit/valid-state checks',
                          'first divergence retained; no tolerance relaxation or CPUshare disablement',
                          'HC consumers, fused next-half xn16, PLE, draft_kv, relayout, short-long-short, restore and cancellation',
                          'targeted existing parity and real region lifetime/sanitizer checks before timed campaign'],
        'baseline_instability': 'A/A bit differences block cross-engine bitwise attribution; locate earliest differing stage using identical input, do not label alias corruption or performance PASS',
        'mechanism_metrics': ['HC/GDN/QSA/MoE bytes', 'whole counted bytes and actual carve.used', 'borrowed slot count and granule',
                              'retained expert IDs and route hits', 'resident mask and CPU/GPU dispatch', 'PLE and MTP batch',
                              'actual expert H2D bytes and exposed wait'],
        'trace_budget': 'at most one A and C 100K trace beyond numerical qualification; trace timings excluded from formal statistics',
        'primary': {'case': 'think-102400', 'fixed_output': 2048, 'pairs': 6, 'metric': 'cold TTFT seconds',
                    'order': [['A','C'], ['C','A'], ['C','A'], ['A','C'], ['A','C'], ['C','A']],
                    'expansion_gate': 'paired improvement >=4% and paired-round 95% CI lower >0'},
        'noninferiority': {'metrics': ['full request wall seconds', 'full decode seconds'],
                          'gate': 'both paired C/A ratio 95% CI upper <=1.02', 'otherwise': 'INCONCLUSIVE or REGRESSION'},
        'support': [{'case': 'think-4096', 'fixed_output': 2048, 'pairs': 2, 'orders': [['A','C'], ['C','A']]},
                    {'case': '32K prime then frozen ~3K append', 'pairs': 2, 'orders': [['A','C'], ['C','A']],
                     'real_compaction': False}],
        'formal_budget': {'fresh_engines': 20, 'work_requests': 24, 'short_qualification_per_engine': 1},
        'statistics': 'entire fresh-engine paired round; exhaustive six-pair bootstrap (6^6), seed-free; support descriptive only',
        'measurement': ['same frozen profile and cache loading per fresh engine', 'cold reused_tokens=0',
                        'fixed output verified using generated_tokens, never SSE chunks', 'no profiler/sync/dump instrumentation in timed arms',
                        'GPU clock/temp/power, actual engine RSS/PSS/swap, faults, full decode and wall',
                        'retain failures/incomplete rows; no replacement or selective exclusion'],
        'stop': ['no slot savings: NO_CAPACITY_GAIN', 'no retained-expert cost signal: CAPACITY_ONLY/NO_SIGNAL',
                 'any B/C bit difference or lifecycle defect: stop before performance',
                 'A/A instability unresolved: BLOCKED_NUMERICAL_ORACLE', 'no automatic GROUP/newchunk/SELECT_LONG/IMMA follow-up'],
        'limits': {'gpu_abort_c': 85, 'min_available_mib': 4096, 'cooldown_c': 55,
                   'max_context': 131072, 'safety_tokens': 4096},
        'inputs': {'performance_sha256': sha256(TASK / 'performance-cases.json'), 'append_sha256': sha256(TASK / 'append-cases.json'),
                   'tokens': token_records},
        'adoption_gate': 'separate original P3 request performance and task quality; this probe cannot pass adoption',
        'original_six_status': 'FAIL_UNCHANGED', 'production_writes': False, 'deployment': False,
    }
    dump(TASK / 'PREREGISTRATION.json', registration)
    dump(TASK / 'REGISTRATION_RECEIPT.json', {'registered_utc': registration['registered_utc'],
         'sha256': sha256(TASK / 'PREREGISTRATION.json'), 'gpu_measurements_started': False,
         'driver_sha256': sha256(Path(__file__))})
    subprocess.run(['git', '-C', str(ROOT / 'workspace/repo'), 'worktree', 'add', '--detach', str(TREE), base.TAG], check=True)
    for name, digest in source['python_port']['files'].items():
        shutil.copy2(old / name, TREE / name)
        assert sha256(TREE / name) == digest
    c['deployed_repo'] = str(TREE)
    c['ggml_dir'] = next(x.split('=', 1)[1] for x in source['native']['flags'] if x.startswith('-DSTRATA_GGML_DIR='))
    c['request_timeout_s'] = 300
    c['gpu_monitor_interval_s'] = 1
    dump(TASK / 'config.json', c)
    return {'state': 'PREREGISTERED', 'task': str(TASK), 'receipt': json.loads((TASK / 'REGISTRATION_RECEIPT.json').read_text())}


if __name__ == '__main__':
    print(json.dumps(prepare()), flush=True)
