"""Break a request's engine prompt time into its parts, from a campaign run with STRATA_TRACE=1 (single arm).

The engine's prompt_ms starts before the request is matched against the session (generate.cpp r0), so it holds more
than the prefill: parking the outgoing conversation when the request does not continue the live one, the batched
read (the prefill wall), the checkpoint saves, the refill of the expert cache slots the prompt path borrowed, and the
last few tokens read as verify windows.  Each request's block runs from the previous "strata serve: prompt" line to
its own; counter probes (<= 4 generated tokens) are skipped and the rest are matched to the round's requests in
order.  "rest" is prompt_ms minus the parts named here (matching, restoring a checkpoint, the head swap, ...).

  python tools/analysis/ttft_trace.py workspace/results/<campaign>
"""
import json, re, statistics, sys
from collections import defaultdict
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(l) for l in (out / 'requests.jsonl').open()]
SERVE = re.compile(r'strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+) read in (\d+) ms.*?, (\d+) generated')
PARTS = {'park_ms': re.compile(r'conversation cache: parked \d+ tokens in ([\d.]+) ms'),
         'batched_ms': re.compile(r'strata trace: read \d+ tokens \(batched\) in ([\d.]+) ms'),
         'windows_ms': re.compile(r'strata trace: read \d+ tokens \(windows\) in ([\d.]+) ms'),
         'ckpt_ms': re.compile(r'strata trace: checkpoint at \d+: sync ([\d.]+) ms, save ([\d.]+) ms'),
         'refill_ms': re.compile(r'strata trace: refilled \d+ slots on \d+ stage\(s\) in ([\d.]+) ms')}
LENT = re.compile(r'strata trace: lent (\d+) slots')


def blocks(text):
    got, start = [], 0
    for m in SERVE.finditer(text):
        b = text[start:m.end()]; start = m.end()
        if int(m[5]) <= 4:
            continue
        x = {'context': int(m[1]), 'reused': int(m[2]), 'read': int(m[3]), 'prompt_ms': int(m[4]),
             'lent_slots': sum(int(v) for v in LENT.findall(b))}
        for k, rx in PARTS.items():
            x[k] = round(sum(sum(float(g) for g in (f if isinstance(f, tuple) else (f,))) for f in rx.findall(b)), 1)
        x['rest_ms'] = round(x['prompt_ms'] - sum(x[k] for k in PARTS), 1)
        got.append(x)
    return got


per_req, unmatched = [], []
for folder in sorted(out.glob('round-*-*')):
    rnd, arm = int(folder.name.split('-')[1]), folder.name.split('-')[2]
    text = (folder / 'engine.log').read_text(errors='replace') if (folder / 'engine.log').exists() else ''
    bs = blocks(text)
    reqs = sorted((r for r in rows if r['round'] == rnd and r['arm'] == arm), key=lambda r: r['started'])
    if len(bs) != len(reqs) or any(b['context'] != (r['metrics'].get('prompt_tokens') or b['context']) for b, r in zip(bs, reqs)):
        unmatched.append({'round': rnd, 'arm': arm, 'blocks': len(bs), 'requests': len(reqs)}); continue
    per_req += [dict(b, round=rnd, case=r['case_id'], group=r['group']) for b, r in zip(bs, reqs)]

KEYS = ('prompt_ms', 'park_ms', 'batched_ms', 'ckpt_ms', 'refill_ms', 'windows_ms', 'rest_ms', 'lent_slots')
by_group, by_case = defaultdict(list), defaultdict(list)
for x in per_req:
    by_group[x['group']].append(x); by_case[x['case']].append(x)
json.dump({'mean_by_group': {g: {'n': len(v), **{k: round(statistics.mean(x[k] for x in v), 1) for k in KEYS}}
                             for g, v in sorted(by_group.items())},
           'median_by_case': {c: {'context': v[0]['context'], 'read': v[0]['read'],
                                  **{k: statistics.median(x[k] for x in v) for k in KEYS}} for c, v in sorted(by_case.items())},
           'unmatched': unmatched},
          sys.stdout, indent=1)
