"""Exactly six preregistered pairs. A statistical gate alone never approves deployment."""
import itertools
import math
import re
from common import input_cli, number, require

ORDER = ['AC', 'CA', 'CA', 'AC', 'AC', 'CA']
METRICS = ('ttft_ms', 'wall_ms', 'decode_ms')


def paired(baseline, candidate):
    logs = [math.log(c) - math.log(a) for a, c in zip(baseline, candidate)]
    draws = sorted(sum(logs[i] for i in ids) / 6 for ids in itertools.product(range(6), repeat=6))
    def quantile(q):
        rank = (len(draws) - 1) * q; low = int(rank); high = min(low + 1, len(draws) - 1)
        return math.exp(draws[low] + (draws[high] - draws[low]) * (rank - low))
    ratio = math.exp(sum(logs) / 6)
    return {'ratio': ratio, 'ratio_ci95': [quantile(0.025), quantile(0.975)], 'time_improvement': 1 - ratio}


def evaluate(data):
    require(isinstance(data, dict) and type(data.get('schema_version')) is int and data['schema_version'] == 1 and type(data.get('synthetic')) is bool, 'integer schema_version=1 and boolean synthetic required')
    plan = data['preregistration']; ids = plan['pair_ids']; pairs = data['pairs']
    require(isinstance(ids, list) and len(ids) == 6 and all(isinstance(x, str) and x for x in ids) and len(set(ids)) == 6, 'Exactly six unique preregistered pair IDs required')
    require(plan['order'] == ORDER, 'Preregistered AC/CA/CA/AC/AC/CA order required')
    require(re.fullmatch(r'[0-9a-fA-F]{64}', plan['request_sha256']) is not None, 'Frozen request SHA256 required')
    tokens = plan['fixed_output_tokens']
    require(type(tokens) is int and tokens > 0, 'fixed_output_tokens must be positive integer')
    noise = number(plan['aa_noise'], 'preregistered aa_noise'); require(noise < 0.5, 'aa_noise must be < 0.5')
    require(plan['primary_metric'] in METRICS, 'Unknown primary time metric')
    require(isinstance(pairs, list) and len(pairs) == 6, 'Missing or extra pairs: reject whole experiment')
    require([row['pair_id'] for row in pairs] == ids, 'Missing, duplicate or reordered pairs')
    engines = set(); values = {name: {'baseline': [], 'candidate': []} for name in METRICS}
    for position, row in enumerate(pairs):
        require(row['order'] == ORDER[position], 'Pair order differs from preregistration')
        for arm in ('baseline', 'candidate'):
            run = row[arm]; require(isinstance(run, dict), 'Run must be an object'); engine = run['engine_id']
            require(isinstance(engine, str) and engine and engine not in engines, 'Missing or reused engine identity')
            engines.add(engine)
            require(run.get('fresh_engine') is True and run.get('run_valid') is True, 'Invalid or non-fresh run: no inference')
            require(run.get('failure_kind') == 'none', 'Failed run: no survivor-only inference')
            require(run['request_sha256'] == plan['request_sha256'], 'Request hash differs from plan')
            require(type(run['output_tokens']) is int and run['output_tokens'] == tokens, 'Fixed output tokens differ')
            for name in METRICS: values[name][arm].append(number(run['metrics'][name], name, positive=True))
    results = {name: paired(v['baseline'], v['candidate']) for name, v in values.items()}
    minimum = max(0.04, 2 * noise)
    gates = {'primary': results[plan['primary_metric']]['ratio_ci95'][1] <= 1 - minimum}
    gates.update({name: results[name]['ratio_ci95'][1] <= 1.02
                  for name in METRICS if name != plan['primary_metric']})
    return {'status': 'PERFORMANCE_GATE_ONLY' if all(gates.values()) else 'PERFORMANCE_GATE_NOT_MET',
            'synthetic': data['synthetic'], 'pairs': 6, 'engine_count': len(engines), 'bootstrap_draws': 46656,
            'method': 'exact paired log-ratio bootstrap; linear quantile at (N-1)*q',
            'metrics': results, 'gates': gates, 'primary_metric': plan['primary_metric'], 'minimum_improvement': minimum,
            'quality': 'NOT_EVALUATED', 'deployment_approved': False,
            'limitations': ['Declared preregistration and fresh engine identities require independent evidence review.',
                            'Synthetic fixtures and rounded-report sanity checks are not hardware measurements.']}


if __name__ == '__main__':
    raise SystemExit(input_cli(evaluate, __doc__))
