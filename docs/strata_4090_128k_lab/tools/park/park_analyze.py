"""Summarize #2253 park A/B: per arm and round, then per arm medians."""
import json, re, statistics as st, sys
from pathlib import Path

R = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / 'workspace/reports/p2253')
ARMS = ['a0', 'off', 'on', 'mmap']
out = {}
for arm in ARMS:
    per = []
    for d in sorted(R.glob(f'r*-{arm}')):
        p = d / 'park.json'
        if not p.exists(): continue
        j = json.loads(p.read_text())
        rows = j['rows']
        revisit = [r for r in rows if r['who'] != 'S' and r['cycle'] > 0]
        text = (d / 'engine.log').read_text(errors='replace')
        gate = [int(x) for x in re.findall(r'skip parking \(physical RAM admission.*?evicted (\d+), \d+ still parked', text)]
        per.append({
            'round': d.name.split('-')[0], **j['log'],
            'gate_evicted_dist': {str(k): gate.count(k) for k in sorted(set(gate))},
            'revisits': len(revisit),
            'revisit_reread': sum(1 for r in revisit if (r['reused_tokens'] or 0) == 0),
            'revisit_read_tokens': sum(r['read_tokens'] or 0 for r in revisit),
            'revisit_ttft_median': round(st.median(r['ttft_s'] for r in revisit), 2),
            'revisit_ttft_mean': round(st.mean(r['ttft_s'] for r in revisit), 2),
            'wall_total_s': round(sum(r['wall_s'] or 0 for r in rows), 1),
            'heap_max_mib': max(r.get('heap_rss_mib', 0) for r in rows),
            'heap_final_mib': rows[-1].get('heap_rss_mib'),
            'anon_max_mib': max(r.get('anonymous_mib', 0) for r in rows),
            'avail_min_mib': min(r.get('mem_available_mib', 1 << 30) for r in rows),
            'avail_loaded_mib': j['loaded'].get('mem_available_mib'),
            'park_ms': [float(x) for x in re.findall(r'conversation cache: parked \d+ tokens in ([0-9.]+) ms', text)],
            'errors': sum(1 for r in rows if r.get('error')),
            'abort': j.get('abort'),
        })
    for x in per:
        pm = x.pop('park_ms'); x['park_ms_median'] = round(st.median(pm), 1) if pm else None; x['park_ms_max'] = max(pm) if pm else None
    out[arm] = per

for arm in ARMS:
    print('==', arm)
    for x in out[arm]:
        print(' ', x['round'], 'refuse', x['gate_refusals'], 'evicted-dist', x['gate_evicted_dist'], 'parked', x['parked'],
              'restored', x['restored'], 'reread', f"{x['revisit_reread']}/{x['revisits']}", 'read_tok', x['revisit_read_tokens'],
              'ttft med/mean', x['revisit_ttft_median'], x['revisit_ttft_mean'], 'wall', x['wall_total_s'],
              'heap max/final', x['heap_max_mib'], x['heap_final_mib'], 'anon_max', x['anon_max_mib'],
              'avail loaded/min', x['avail_loaded_mib'], x['avail_min_mib'], 'trims', x['trims'], x['trim_ms_total'],
              x['trim_ms_max'], 'park_ms med/max', x['park_ms_median'], x['park_ms_max'], 'floor_after_capture',
              x['floor_after_capture'], 'err', x['errors'], 'abort', x['abort'])
(R / 'summary.json').write_text(json.dumps(out, indent=1))
