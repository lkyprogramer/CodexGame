#!/usr/bin/env python3
"""survey-20261125 verdict (plans/SURVEY_20261125.prereg.json 'rules'); run on the 4090 beside upgrade_gate.py.
  survey_eval.py next    -> the next runs the schedule wants (one name per line), from what exists so far
  survey_eval.py verdict -> VERDICT-SURVEY.json under the label"""
import json, sys
import upgrade_gate as ug

LB = 'survey-20261125'
PHASE1 = ['C1', 'S1', 'KL2', 'S3', 'KFW', 'C2', 'S2', 'KQI', 'KQF', 'KDP', 'KGP', 'C3', 'MD8', 'MPF', 'MLP', 'MLH', 'C4']
ARMS = ['S1', 'S2', 'S3', 'KL2', 'KFW', 'KQI', 'KQF', 'KDP', 'KGP']
CTRL = ['C1', 'C2', 'C3', 'C4', 'C5']
BRACKET = {'S1': ('C1', 'C2'), 'KL2': ('C1', 'C2'), 'S3': ('C1', 'C2'), 'KFW': ('C1', 'C2'), 'S2': ('C2', 'C3'), 'KQI': ('C2', 'C3'),
           'KQF': ('C2', 'C3'), 'KDP': ('C2', 'C3'), 'KGP': ('C2', 'C3')}


def bitwise():
    k = ug.load(LB, 'KL.json') or {}
    pre = ug.load(LB, 'PREREG.json'); out = {}
    for c in pre['candidates']:
        r = (k.get('runs') or {}).get(c['kl_run'])
        out[c['run']] = None if r is None else (r['kl_vs_b2'] == 0 and r['top1_vs_b2'] == 1)
    return out


def fig(n):
    d = ug.load(LB, 'RUN-%s.json' % n)
    return ug.run_figures(LB, n) if d else None


def valid(f): return bool(f) and f['valid'] and (f['cotenant_cpu'] is None or f['cotenant_cpu'] <= 4.5)


def nxt():
    bw = bitwise(); todo = []
    for n in PHASE1:
        if n.startswith('K') and bw.get(n) is not True: continue
        if not ug.load(LB, 'RUN-%s.json' % n): todo.append(n)
    if todo: return todo
    for a in ARMS:
        if a.startswith('K') and bw.get(a) is not True: continue
        f = fig(a); b = BRACKET[a]; cs = [fig(x) for x in b]
        if not (valid(f) and all(valid(c) for c in cs)): continue
        g = f['decode_tok_s'] / (sum(c['decode_tok_s'] for c in cs) / 2) - 1
        if g > 0 and not ug.load(LB, 'RUN-%sb.json' % a): todo.append(a + 'b')
    if not ug.load(LB, 'RUN-C5.json'): todo.append('C5')
    return todo


def verdict():
    bw = bitwise(); ctl = {n: fig(n) for n in CTRL}; ctl = {n: f for n, f in ctl.items() if valid(f)}
    d = [f['decode_tok_s'] for f in ctl.values()]; cm = sum(d) / len(d); aa = (max(d) - min(d)) / cm; bar = max(0.022, 2 * aa)
    lim = {k: max(f[k] for f in ctl.values()) + 1 for k in ('finish_length', 'repeat_notices')}
    out = dict(controls={n: dict(decode_tok_s=f['decode_tok_s'], ms_win=f['ms_win'], tok_win=f['tok_win'], cotenant_cpu=f['cotenant_cpu']) for n, f in ctl.items()},
               control_decode_tok_s=round(cm, 2), aa=round(aa, 4), bar=round(bar, 4), bitwise=bw, arms={}, m={})
    for a in ARMS:
        f, fb = fig(a), fig(a + 'b')
        if a.startswith('K') and bw.get(a) is not True: out['arms'][a] = dict(verdict='NOT_BITWISE' if bw.get(a) is False else 'NO_KL'); continue
        if not valid(f): out['arms'][a] = dict(verdict='INVALID_OR_MISSING'); continue
        cs = [fig(x) for x in BRACKET[a]]
        g1 = f['decode_tok_s'] / (sum(c['decode_tok_s'] for c in cs) / 2) - 1
        r = dict(screen_gain=round(g1, 4), run=dict(decode_tok_s=f['decode_tok_s'], ms_win=f['ms_win'], tok_win=f['tok_win'], cotenant_cpu=f['cotenant_cpu'],
                                                     finish_length=f['finish_length'], repeat_notices=f['repeat_notices']))
        if g1 <= 0: r['verdict'] = 'NO_GAIN_SCREEN'; out['arms'][a] = r; continue
        if not valid(fb): r['verdict'] = 'UNCONFIRMED'; out['arms'][a] = r; continue
        g = (f['decode_tok_s'] + fb['decode_tok_s']) / 2 / cm - 1
        loops_ok = all(x[k] <= lim[k] for x in (f, fb) for k in lim) if a.startswith('S') else True
        r.update(run_b=dict(decode_tok_s=fb['decode_tok_s'], ms_win=fb['ms_win'], tok_win=fb['tok_win'], cotenant_cpu=fb['cotenant_cpu'],
                            finish_length=fb['finish_length'], repeat_notices=fb['repeat_notices']), gain=round(g, 4),
                 checks=dict(gain_ge_bar=g >= bar, both_above_control_mean=min(f['decode_tok_s'], fb['decode_tok_s']) > cm, loop_signs_ok=loops_ok))
        r['verdict'] = 'PASS' if all(r['checks'].values()) else 'NO_PASS'; out['arms'][a] = r
    c34 = [fig(x) for x in ('C3', 'C4')]
    if all(valid(c) for c in c34):
        base = sum(c['ms_win'] for c in c34) / 2
        for n, div, what in (('MD8', 8 * 48, 'ms per empty node'), ('MLP', 0.020 * 48, 'slope of a delay before the doorbell'),
                             ('MLH', 0.020 * 48, 'slope of a delay after the resident experts')):
            f = fig(n)
            if valid(f): out['m'][n] = dict(ms_win=f['ms_win'], base_ms_win=round(base, 3), value=round((f['ms_win'] - base) / div, 5), what=what, cotenant_cpu=f['cotenant_cpu'])
    return ug.save(LB, 'VERDICT-SURVEY.json', out)


if __name__ == '__main__':
    if sys.argv[1:] == ['next']: print('\n'.join(nxt()))
    elif sys.argv[1:] == ['verdict']: print(json.dumps(verdict(), indent=1))
    else: raise SystemExit(__doc__)
