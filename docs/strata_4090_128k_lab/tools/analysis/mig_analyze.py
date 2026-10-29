"""Summarize a MIG campaign (arms p / base): per-case medians, paired A0/P ratios, engine timing lines."""
import json, re, statistics, sys, random
from collections import defaultdict
from pathlib import Path

out = Path(sys.argv[1])
rows = [json.loads(l) for l in (out / 'requests.jsonl').open()]
METRICS = ('decode_tps', 'prompt_tps', 'ttft_s', 'wall_s')
by = defaultdict(lambda: defaultdict(dict))          # case -> arm -> round -> row
for r in rows:
    by[r['case_id']][r['arm']][r['round']] = r
group = {r['case_id']: r['group'] for r in rows}


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def boot_ci(xs, n=4000, seed=7):
    if len(xs) < 3:
        return None
    rnd = random.Random(seed)
    ms = sorted(statistics.median(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return ms[int(0.025 * n)], ms[int(0.975 * n)]


case_rows, ratios = [], defaultdict(lambda: defaultdict(list))
for case, arms in by.items():
    rec = {'case': case, 'group': group[case]}
    for arm in ('p', 'base'):
        rs = list(arms.get(arm, {}).values())
        rec[arm] = {m: med([x['metrics'].get(m) for x in rs]) for m in METRICS}
        rec[arm]['read_tokens'] = med([x['metrics'].get('read_tokens') for x in rs])
        rec[arm]['generated'] = med([x['metrics'].get('generated_tokens') for x in rs])
        rec[arm]['pass'] = f"{sum(1 for x in rs if x['score'].get('pass'))}/{len(rs)}"
        off = sum(x['metrics'].get('drafts_offered') or 0 for x in rs)
        acc = sum(x['metrics'].get('drafts_accepted') or 0 for x in rs)
        rec[arm]['accept'] = acc / off if off else None
        rec[arm]['fixed_ok'] = sum(1 for x in rs if x.get('fixed_output_comparable'))
    for rnd in set(arms.get('p', {})) & set(arms.get('base', {})):
        a, b = arms['p'][rnd], arms['base'][rnd]
        # Prompt-side metrics do not depend on the output; decode/wall only compare when both arms generated the same count.
        same_out = a['metrics'].get('generated_tokens') == b['metrics'].get('generated_tokens')
        for m in METRICS:
            if m in ('decode_tps', 'wall_s') and not same_out:
                continue
            x, y = a['metrics'].get(m), b['metrics'].get(m)
            if x and y:
                ratios[group[case]][m].append(y / x)
    case_rows.append(rec)

# Engine-side timing lines, aggregated per arm (windows-weighted).
dec = re.compile(r'strata decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = verify ([\d.]+) \(GPU-reach wait ([\d.]+) \+ per-layer host ([\d.]+).*?CPU ([\d.]+).*?draft ([\d.]+)')
pre = re.compile(r'strata prefill timing: (\d+) tokens, GPU timeline (\d+) ms')
engine = {}
for arm in ('p', 'base'):
    w = tok = ms = ver = gpu = host = cpu = dr = 0.0
    pf = []
    for log in sorted(out.glob(f'round-*-{arm}/engine.log')):
        for line in log.read_text(errors='replace').splitlines():
            m = dec.search(line)
            if m:
                n = int(m[1])
                if n < 20:          # skip tiny requests; the long fixed-output cases dominate
                    continue
                w += n; tok += n * float(m[3]); ms += n * float(m[4]); ver += n * float(m[5])
                gpu += n * float(m[6]); host += n * float(m[7]); cpu += n * float(m[8]); dr += n * float(m[9])
            m = pre.search(line)
            if m and int(m[1]) >= 3000:
                pf.append((int(m[1]), int(m[2])))
    engine[arm] = {'windows': int(w), 'tokens_per_window': tok / w if w else None, 'ms_per_window': ms / w if w else None,
                   'verify_ms': ver / w if w else None, 'gpu_wait_ms': gpu / w if w else None, 'host_ms': host / w if w else None,
                   'cpu_ms': cpu / w if w else None, 'draft_ms': dr / w if w else None,
                   'prefill': sorted(pf)}

summary = {g: {m: {'n': len(v), 'median_ratio_base_over_p': statistics.median(v), 'ci95': boot_ci(v)}
               for m, v in ms.items()} for g, ms in ratios.items()}
json.dump({'cases': case_rows, 'paired_ratios': summary, 'engine': engine}, sys.stdout, indent=1, default=str)
