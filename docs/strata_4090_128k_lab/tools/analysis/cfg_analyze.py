"""Summarize a CONFIG campaign (arms base / cfg): paired cfg/base ratios per group and per case, greedy output identity,
and engine decode timing per arm and per case."""
import json, re, statistics, sys, random
from collections import defaultdict
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(l) for l in (out / 'requests.jsonl').open()]
METRICS = ('decode_tps', 'prompt_tps', 'ttft_s', 'wall_s')
by = defaultdict(lambda: defaultdict(dict))
for r in rows:
    by[r['case_id']][r['arm']][r['round']] = r
group = {r['case_id']: r['group'] for r in rows}


def boot_ci(xs, n=4000, seed=7):
    if len(xs) < 3:
        return None
    rnd = random.Random(seed)
    ms = sorted(statistics.median(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return [round(ms[int(0.025 * n)], 4), round(ms[int(0.975 * n)], 4)]


def summ(v):
    return {'n': len(v), 'median': round(statistics.median(v), 4), 'ci95': boot_ci(v)} if v else None


by_group, by_case, identity = defaultdict(lambda: defaultdict(list)), {}, defaultdict(lambda: [0, 0])
for case, arms in by.items():
    rec = defaultdict(list)
    for rnd in set(arms.get('base', {})) & set(arms.get('cfg', {})):
        a, b = arms['base'][rnd], arms['cfg'][rnd]
        same_out = a['metrics'].get('generated_tokens') == b['metrics'].get('generated_tokens')
        for m in METRICS:
            if m in ('decode_tps', 'wall_s') and not same_out:
                continue
            x, y = a['metrics'].get(m), b['metrics'].get(m)
            if x and y:
                by_group[group[case]][m].append(y / x); rec[m].append(y / x)
        if not group[case].endswith('sampled'):
            identity[group[case]][0] += 1
            identity[group[case]][1] += a['response'].get('text') == b['response'].get('text')
    base_rs = list(arms.get('base', {}).values())
    by_case[case] = {'group': group[case], 'prompt_tokens': base_rs[0]['metrics'].get('prompt_tokens') if base_rs else None,
                     'decode_tps_base': statistics.median([x['metrics']['decode_tps'] for x in base_rs if x['metrics'].get('decode_tps')] or [0]),
                     **{m: summ(v) for m, v in rec.items()},
                     'pass': {arm: f"{sum(1 for x in rs.values() if x['score'].get('pass'))}/{len(rs)}" for arm, rs in arms.items()}}

dec = re.compile(r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+).*?CPU ([\d.]+).*?draft ([\d.]+)')
engine = {}
for arm in ('base', 'cfg'):
    acc = defaultdict(float)
    for log in sorted(out.glob(f'round-*-{arm}/engine.log')):
        for line in log.read_text(errors='replace').splitlines():
            m = dec.search(line)
            if m and int(m[1]) >= 20:
                n = int(m[1]); acc['windows'] += n
                for i, k in enumerate(('avg_T', 'tok_per_win', 'ms', 'verify', 'gpu_wait', 'host', 'cpu', 'draft'), 2):
                    acc[k] += n * float(m[i])
    w = acc.pop('windows', 0)
    engine[arm] = {'windows': int(w), **{k: round(v / w, 3) for k, v in acc.items()}} if w else None

json.dump({'paired_cfg_over_base': {g: {m: summ(v) for m, v in ms.items()} for g, ms in by_group.items()},
           'cases': by_case, 'greedy_text_identical': {g: f'{s}/{n}' for g, (n, s) in identity.items()},
           'engine': engine, 'failure': (out / 'FAILURE.json').read_text() if (out / 'FAILURE.json').exists() else None},
          sys.stdout, indent=1)
