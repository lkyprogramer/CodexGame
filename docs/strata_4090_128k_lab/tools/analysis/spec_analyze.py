"""Summarize a CFG-SPEC-S campaign (arms base / cfg) per group: paired cfg/base decode tok/s, total tokens over total
decode time, draft acceptance, and the engine's per-request decode timing (ms/window, tokens/window, avg T).

The server can split one request into several engine calls: with a reasoning effort it stops thinking at a budget
(3/4 of max_tokens, or reasoning_budget_tokens), closes it and calls the engine again for the answer.  Each engine call
logs a "decode timing" line followed by a "strata serve: prompt ..." line; calls are assigned to the requests of the
round in order, summing generated tokens until the request's count is reached (the inserted closing text counts as
output on the server side, so a slack of 32 tokens is allowed).  The first call of a split request is the think phase,
the rest the answer phase.  Counter probes (<= 4 generated tokens) are skipped.  A round whose calls do not add up is
left out of the engine table and listed under engine_unmatched.

  python tools/analysis/spec_analyze.py workspace/results/<campaign>
"""
import json, random, re, statistics, sys
from collections import defaultdict
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(l) for l in (out / 'requests.jsonl').open()]
DEC = re.compile(r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = '
                 r'verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+).*?CPU ([\d.]+).*?draft ([\d.]+)')
SERVE = re.compile(r'strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms.*?, (\d+) generated in (\d+) ms')
SLOTS = re.compile(r'expert cache (\d+) slots')
WIN = re.compile(r'verify: window up to (\d+) tokens')


def boot_ci(xs, n=4000, seed=7):
    if len(xs) < 3:
        return None
    rnd = random.Random(seed)
    ms = sorted(statistics.median(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return [round(ms[int(0.025 * n)], 4), round(ms[int(0.975 * n)], 4)]


def summ(v):
    return {'n': len(v), 'median': round(statistics.median(v), 4), 'ci95': boot_ci(v)} if v else None


# paired decode tok/s per group (same case, same round; both runs reached the fixed output)
by = defaultdict(dict)
for r in rows:
    by[(r['case_id'], r['round'])][r['arm']] = r
ratios, per_case = defaultdict(list), defaultdict(list)
for (case, rnd), arms in by.items():
    a, b = arms.get('base'), arms.get('cfg')
    if not (a and b and a['fixed_output_comparable'] and b['fixed_output_comparable']):
        continue
    x, y = a['metrics'].get('decode_tps'), b['metrics'].get('decode_tps')
    if x and y:
        ratios[a['group']].append(y / x); per_case[case].append(y / x)

# totals per arm and group
tot = defaultdict(lambda: defaultdict(float))
for r in rows:
    m, k = r['metrics'], (r['arm'], r['group'])
    if m.get('generated_tokens') and m.get('decode_ms'):
        tot[k]['tokens'] += m['generated_tokens']; tot[k]['decode_ms'] += m['decode_ms']
        tot[k]['offered'] += m.get('drafts_offered') or 0; tot[k]['accepted'] += m.get('drafts_accepted') or 0
        tot[k]['n'] += 1
totals = {f'{arm}/{g}': {'n': int(v['n']), 'tok_per_s': round(v['tokens'] / v['decode_ms'] * 1000, 2),
                         'draft_accept': round(v['accepted'] / v['offered'], 4) if v['offered'] else None}
          for (arm, g), v in sorted(tot.items())}

# engine timing by group and phase, engine calls assigned to requests in order
KEYS = ('avg_T', 'tok_per_win', 'ms', 'verify', 'gpu_wait', 'host', 'cpu', 'draft')


def engine_calls(text):
    calls, dec = [], None
    for m in re.finditer(DEC.pattern + '|' + SERVE.pattern, text):
        if m.group(0).startswith('strata decode timing'):
            dec = DEC.match(m.group(0))
        else:
            sv = SERVE.match(m.group(0))
            if dec and int(sv[5]) > 4:
                calls.append({'dec': dec, 'read': int(sv[3]), 'read_ms': int(sv[4]), 'gen': int(sv[5])})
            dec = None
    return calls


eng, unmatched, setup = defaultdict(lambda: defaultdict(float)), [], {}
reread = defaultdict(list)   # tokens read and ms by the answer call of a split request
for folder in sorted(out.glob('round-*-*')):
    rnd, arm = int(folder.name.split('-')[1]), folder.name.split('-')[2]
    text = (folder / 'engine.log').read_text(errors='replace') if (folder / 'engine.log').exists() else ''
    calls = engine_calls(text)
    reqs = sorted((r for r in rows if r['round'] == rnd and r['arm'] == arm), key=lambda r: r['started'])
    s, w = SLOTS.search(text), WIN.search(text)
    setup.setdefault(arm, set()).add((int(s[1]) if s else None, int(w[1]) if w else None))
    groups, i = [], 0
    for r in reqs:
        want, got, mine = r['metrics'].get('generated_tokens') or 0, 0, []
        while i < len(calls) and got < want - 32:
            mine.append(calls[i]); got += calls[i]['gen']; i += 1
        if not mine or abs(got - want) > 32:
            break
        groups.append((r, mine))
    if len(groups) != len(reqs) or i != len(calls):
        unmatched.append({'round': rnd, 'arm': arm, 'engine_calls': len(calls), 'requests': len(reqs), 'matched': len(groups)})
        continue
    for r, mine in groups:
        for j, c in enumerate(mine):
            phase = 'whole' if len(mine) == 1 else ('think' if j == 0 else 'answer')
            if phase == 'answer':
                reread[(arm, r['group'])].append((c['read'], c['read_ms']))
            for key in ((arm, r['group'], 'all'), (arm, r['group'], phase)):
                acc, m = eng[key], c['dec']
                n = int(m[1]); acc['windows'] += n
                for k, idx in zip(KEYS, range(2, 10)):
                    acc[k] += n * float(m[idx])
engine = {'/'.join(k): {'windows': int(v['windows']), **{x: round(y / v['windows'], 3) for x, y in v.items() if x != 'windows'}}
          for k, v in sorted(eng.items()) if not (k[2] == 'whole')}
answer_reread = {f'{a}/{g}': {'n': len(v), 'read_tokens_median': statistics.median(x for x, _ in v),
                              'read_ms_median': statistics.median(y for _, y in v)} for (a, g), v in sorted(reread.items())}

json.dump({'paired_decode_tps_cfg_over_base': {g: summ(v) for g, v in sorted(ratios.items())},
           'per_case': {c: summ(v) for c, v in sorted(per_case.items())},
           'totals': totals, 'engine': engine, 'answer_call_read': answer_reread, 'engine_unmatched': unmatched,
           'setup_slots_window': {a: sorted(v, key=str) for a, v in setup.items()},
           'not_comparable': sum(1 for r in rows if not r['fixed_output_comparable']),
           'failure': (out / 'FAILURE.json').read_text() if (out / 'FAILURE.json').exists() else None},
          sys.stdout, indent=1)
