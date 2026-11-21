"""C01 offline counterfactual (2026-11-20): does an 8-gram secondary index recover suffix matches that Strata v0.2.17's
trigram 4-way buckets lost, on the Pi-like agent sessions (public Exercism tasks; no user content)?
ORACLE_UPPER_BOUND only: proposals use only the visible prefix; acceptance is scored against the recorded output.
Strata semantics (engine/src/spec/suffix_drafter.cpp, v0.2.17): every trigram of history -> its 4 most recent end
positions; propose from the candidate with the longest backward match (<= 64, >= min_match 3; newest on ties)."""
import json, sys, collections
import functools, pathlib
sys.path.insert(0, '/home/hhtele/strata-0.2.17/terminal/tools'); import strata_tokenizer as ST   # the engine's own tokenizer (pure Python)
_tp = pathlib.Path('/data/strata-data/packs/iq3_xxs/tokenizer'); _v = json.loads((_tp / 'vocab.json').read_text()); _t = [None] * len(_v)
for _k, _i in _v.items(): _t[_i] = _k
TOK = ST.Tokenizer(_t, (_tp / 'merges.txt').read_text().split('\n'), json.loads((_tp / 'token_type.json').read_text()))
WAYS, MAXM, MINM, KMAX = 4, 64, 3, 8
@functools.lru_cache(maxsize=None)
def _enc(s): return tuple(TOK.encode(s, parse_special=True))
def enc(s): return list(_enc(s)) if s else []
def tc_text(m):
    return ''.join('<tool_call>\n{"name": "%s", "arguments": %s}\n</tool_call>' % (t['function']['name'], t['function']['arguments']) for t in m.get('tool_calls') or [])
def render(msgs, j):
    """prompt tokens for request j (PT0: assistant thinking kept only after the last user message)"""
    last_user = max(i for i in range(j) if msgs[i]['role'] == 'user')
    out = []
    for i, m in enumerate(msgs[:j]):
        r = m['role']; body = m.get('content') or ''
        if r == 'assistant':
            th = m.get('reasoning_content') if i > last_user else None
            body = ('<think>\n%s\n</think>\n\n' % th if th else '') + body + tc_text(m)
        elif r == 'tool':
            r = 'user'; body = '<tool_response>\n%s\n</tool_response>' % body
        out += enc('<|im_start|>%s\n' % r) + enc(body) + enc('<|im_end|>\n')
    return out + enc('<|im_start|>assistant\n')
class Drafter:
    def __init__(self, eight):
        self.h = []; self.tri = collections.defaultdict(list); self.eight = {} if eight else None
    def append(self, toks):
        for t in toks:
            self.h.append(t); e = len(self.h) - 1
            if e >= 2:
                b = self.tri[tuple(self.h[e-2:e+1])]; b.insert(0, e); del b[WAYS:]
            if self.eight is not None and e >= 7:
                b8 = self.eight.setdefault(tuple(self.h[e-7:e+1]), []); b8.insert(0, e); del b8[2:]   # 2 ways: way 0 is usually the current suffix itself
    def match_len(self, p, cur):
        n = 0
        while n < MAXM and n <= p and self.h[p-n] == self.h[cur-n]: n += 1
        return n
    def propose(self):
        h = self.h; cur = len(h) - 1
        if cur < 3: return None, 0, False
        cands = list(self.tri.get(tuple(h[cur-2:cur+1]), ()))
        from8 = None
        if self.eight is not None and cur >= 7:
            from8 = next((q for q in self.eight.get(tuple(h[cur-7:cur+1]), ()) if q < cur and q not in cands), None)
            if from8 is not None: cands.append(from8)
        best, bl = None, 0
        for p in cands:
            if p >= cur: continue
            l = self.match_len(p, cur)
            if l > bl: best, bl = p, l
        if bl < MINM: return None, bl, False
        return best, bl, best == from8
def walk(prompt, gen, eight, mtp):
    d = Drafter(eight); d.append(prompt); i = 0; windows = 0.0; sfx_w = 0; acc = 0; via8 = 0; via8_extra = 0
    while i < len(gen):
        p, l, is8 = d.propose()
        if p is not None:
            k = 0
            while k < KMAX and p + 1 + k < len(d.h) and i + k < len(gen) and d.h[p+1+k] == gen[i+k]: k += 1
            if k > 0:
                c = min(k + 1, len(gen) - i); windows += 1; sfx_w += 1; acc += k
                if is8: via8 += 1; via8_extra += k
                d.append(gen[i:i+c]); i += c; continue
        c = 1; windows += 1.0 / mtp; d.append(gen[i:i+c]); i += c   # MTP window: mtp tokens per window on average
    return dict(windows=windows, suffix_windows=sfx_w, suffix_accepted=acc, via8_windows=via8, via8_accepted=via8_extra, gen=len(gen))
def main(files, mtp):
    tot = {'A': collections.Counter(), 'B': collections.Counter()}; by_kind = collections.defaultdict(lambda: {'A': collections.Counter(), 'B': collections.Counter()})
    reqs = 0
    for f in files:
        msgs = json.load(open(f))
        for j, m in enumerate(msgs):
            if m['role'] != 'assistant': continue
            prompt = render(msgs, j)
            th = m.get('reasoning_content')
            gen = enc(('<think>\n%s\n</think>\n\n' % th if th else '') + (m.get('content') or '') + tc_text(m))
            kind = 'write_edit' if any(t['function']['name'] in ('write', 'edit') for t in m.get('tool_calls') or []) else 'other'
            for arm, eight in (('A', False), ('B', True)):
                r = walk(prompt, gen, eight, mtp)
                tot[arm].update(r); by_kind[kind][arm].update(r)
            reqs += 1
    def summ(t):
        a, b = t['A'], t['B']
        return dict(gen_tokens=a['gen'], windows_A=round(a['windows'], 1), windows_B=round(b['windows'], 1),
                    window_saving_upper=round(1 - b['windows'] / a['windows'], 4) if a['windows'] else None,
                    suffix_window_share_A=round(a['suffix_windows'] / a['windows'], 4) if a['windows'] else None,
                    suffix_accepted_share_A=round(a['suffix_accepted'] / a['gen'], 4) if a['gen'] else None,
                    recovered_by_8gram_windows=b['via8_windows'], recovered_by_8gram_accepted=b['via8_accepted'])
    res = dict(requests=reqs, mtp_tokens_per_window=mtp, kmax=KMAX, all=summ(tot), by_kind={k: summ(v) for k, v in by_kind.items()},
               label='ORACLE_UPPER_BOUND')
    print(json.dumps(res, indent=1))
if __name__ == '__main__':
    main(sys.argv[2:], float(sys.argv[1]))
