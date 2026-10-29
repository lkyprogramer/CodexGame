"""Summarize a CFG-CPUSHARE-S campaign (arms base / cfg) per group: paired cfg/base prompt time of the same follow-up
read, read tok/s over the group, first-event time, and the engine's prefill timing (wall, wait copy and host grouping
shares, host staging, and the server's prompt time beyond the engine's prefill wall).

A pair counts only when both arms read the same number of tokens (same cache reuse); pairs that do not are counted
under read_mismatch.  Engine "prefill timing" lines of >= 500 tokens are matched to the requests that read >= 500
tokens (a read of a few tokens prints no line), by order inside each
round's engine.log; a round whose counts differ is listed under engine_unmatched.  The decode control is compared on
decode tok/s, and the expert cache slots of each arm are listed (the limit also sizes prefill buffers).

  python tools/analysis/cpushare_analyze.py workspace/results/<campaign>
"""
import json, random, re, statistics, sys
from collections import defaultdict
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(l) for l in (out / 'requests.jsonl').open()]
PRE = re.compile(r'strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms, wall (\d+) ms, host staging (\d+) ms:.*?'
                 r'host grouping \d+ \(([\d.]+)%\).*?wait copy \d+ \(([\d.]+)%\)')
SLOTS = re.compile(r'expert cache (\d+) slots')


def boot_ci(xs, n=4000, seed=7):
    if len(xs) < 3:
        return None
    rnd = random.Random(seed)
    ms = sorted(statistics.median(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return [round(ms[int(0.025 * n)], 4), round(ms[int(0.975 * n)], 4)]


def summ(v):
    return {'n': len(v), 'median': round(statistics.median(v), 4), 'ci95': boot_ci(v)} if v else None


by = defaultdict(dict)
for r in rows:
    by[(r['case_id'], r['round'])][r['arm']] = r
ratios, first, decode, mismatch = defaultdict(list), defaultdict(list), [], 0
for (case, rnd), arms in by.items():
    a, b = arms.get('base'), arms.get('cfg')
    if not (a and b):
        continue
    ma, mb = a['metrics'], b['metrics']
    if a['group'] == 'decode':
        if a['fixed_output_comparable'] and b['fixed_output_comparable'] and ma.get('decode_tps') and mb.get('decode_tps'):
            decode.append(mb['decode_tps'] / ma['decode_tps'])
        continue
    if ma.get('read_tokens') != mb.get('read_tokens'):
        mismatch += 1; continue
    if ma.get('prompt_ms') and mb.get('prompt_ms'):
        ratios[a['group']].append(mb['prompt_ms'] / ma['prompt_ms'])
    if ma.get('ttft_s') and mb.get('ttft_s'):
        first[a['group']].append(mb['ttft_s'] / ma['ttft_s'])

tot = defaultdict(lambda: defaultdict(list))
for r in rows:
    m, k = r['metrics'], (r['arm'], r['group'])
    for f in ('read_tokens', 'prompt_ms', 'ttft_s'):
        if m.get(f) is not None:
            tot[k][f].append(m[f])
totals = {f'{arm}/{g}': {'n': len(v['prompt_ms']),
                         'read_tokens_median': statistics.median(v['read_tokens']) if v['read_tokens'] else None,
                         'read_tok_per_s': round(sum(v['read_tokens']) / sum(v['prompt_ms']) * 1000, 1) if v['prompt_ms'] else None,
                         'prompt_ms_median': statistics.median(v['prompt_ms']) if v['prompt_ms'] else None,
                         'ttft_s_median': round(statistics.median(v['ttft_s']), 3) if v['ttft_s'] else None}
          for (arm, g), v in sorted(tot.items())}

eng, unmatched, slots = defaultdict(lambda: defaultdict(float)), [], defaultdict(set)
for folder in sorted(out.glob('round-*-*')):
    rnd, arm = int(folder.name.split('-')[1]), folder.name.split('-')[2]
    text = (folder / 'engine.log').read_text(errors='replace') if (folder / 'engine.log').exists() else ''
    lines, prev = [], 0
    for m in PRE.finditer(text):   # host staging is a running total in the engine log: keep each read's own part
        if int(m[1]) >= 500:
            lines.append((m, int(m[4]) - prev))
        prev = int(m[4])
    s = SLOTS.search(text); slots[arm].add(int(s[1]) if s else None)
    reqs = sorted((r for r in rows if r['round'] == rnd and r['arm'] == arm and r['group'] != 'decode'
                   and (r['metrics'].get('read_tokens') or 0) >= 500), key=lambda r: r['started'])
    if len(lines) != len(reqs):
        unmatched.append({'round': rnd, 'arm': arm, 'prefill_lines': len(lines), 'requests': len(reqs)}); continue
    for (m, staging), r in zip(lines, reqs):
        acc = eng[(arm, r['group'])]
        acc['n'] += 1; acc['tokens'] += int(m[1]); acc['wall_ms'] += int(m[3]); acc['staging_ms'] += staging
        acc['grouping_pct'] += float(m[5]); acc['wait_copy_pct'] += float(m[6])
        acc['outside_ms'] += (r['metrics'].get('prompt_ms') or 0) - int(m[3])   # server prompt time beyond the engine's prefill wall
engine = {f'{arm}/{g}': {'n': int(v['n']), 'tok_per_s': round(v['tokens'] / v['wall_ms'] * 1000, 1),
                         'staging_ms_mean': round(v['staging_ms'] / v['n'], 1),
                         'outside_prefill_ms_mean': round(v['outside_ms'] / v['n'], 1),
                         'grouping_pct_mean': round(v['grouping_pct'] / v['n'], 2),
                         'wait_copy_pct_mean': round(v['wait_copy_pct'] / v['n'], 2)}
          for (arm, g), v in sorted(eng.items())}

json.dump({'paired_prompt_ms_cfg_over_base': {g: summ(v) for g, v in sorted(ratios.items())},
           'paired_ttft_cfg_over_base': {g: summ(v) for g, v in sorted(first.items())},
           'paired_decode_tps_cfg_over_base': summ(decode), 'expert_cache_slots': {a: sorted(v, key=str) for a, v in slots.items()},
           'read_mismatch': mismatch, 'totals': totals, 'engine_prefill': engine, 'engine_unmatched': unmatched,
           'failure': (out / 'FAILURE.json').read_text() if (out / 'FAILURE.json').exists() else None},
          sys.stdout, indent=1)
