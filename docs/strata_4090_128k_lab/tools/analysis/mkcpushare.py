"""Follow-up read corpus for CFG-CPUSHARE-S (STRATA_PREFILL_CPU_SHARE_MAX vs the size of a follow-up read).

Two chains replayed in order inside one engine, each step generating 16 tokens with Pi's request shape:
  read-long   a recorded PT=0 session (history without thinking): each step reads the previous answer plus the new
              file, about 7-13K tokens, the way every PT=0 follow-up does
  read-short  the same files with each earlier answer cut to its first 600 characters: about 3K per step, the size
              of a normal PT=1 follow-up
The first step of each chain is a cold prefill (group read-prime) and is not part of the comparison.  The greedy
decode cases of the --like corpus follow as a control: a larger limit also sizes prefill buffers that borrow expert
cache slots, so decode is checked, not assumed.

  python tools/analysis/mkcpushare.py --session pt0-java --steps 10 --short-steps 8
"""
import argparse, copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab.core import hash_obj, dump, load_config
from lab.tokenizer import StrataCounter
from lab.workspace import baseline_dir

ap = argparse.ArgumentParser()
ap.add_argument('--session', default='pt0-java')
ap.add_argument('--steps', type=int, default=10)
ap.add_argument('--short-steps', type=int, default=8)
ap.add_argument('--like', default='workspace/corpora/decode-1c99c03c6c9e.json', help='corpus whose header fields to reuse')
a = ap.parse_args()

c = load_config(str(ROOT / 'config/local.json'))
counter = StrataCounter(baseline_dir(c), c['gguf'], c['template'])
msgs = json.loads((ROOT / 'workspace/reports/session' / a.session / 'session.json').read_text())['messages']
like = json.loads((ROOT / a.like).read_text())
plain = [{'role': m['role'], 'content': m['content']} for m in msgs]   # no reasoning_content: PT=0 history

cases, sizes = [], []
for name, steps, cut in (('read-long', a.steps, None), ('read-short', a.short_steps, 600)):
    hist = copy.deepcopy(plain)
    if cut:
        hist = [dict(m, content=m['content'][:cut]) if m['role'] == 'assistant' else m for m in hist]
    prev = None
    for t in range(steps):
        body = {'model': 'strata', 'messages': hist[:2 + 2 * t], 'max_tokens': 16, 'temperature': 1.0, 'top_p': 0.95,
                'top_k': 20, 'reasoning_effort': 'xhigh'}
        n = counter(body)
        x = {'id': f'{name}-{t:02d}', 'kind': 'performance', 'group': 'read-prime' if t == 0 else name,
             'fixed_output': 16, 'cache_state': 'sequence_controlled', 'body': body,
             'request_sha256': hash_obj(body), 'prompt_tokens_local': n, 'counted_prompt_tokens': n}
        cases.append(x); sizes.append((x['id'], n, None if prev is None else n - prev)); prev = n
cases += [x for x in like['cases'] if x['group'] == 'decode']
out = {k: v for k, v in like.items() if k not in ('cases', 'corpus_sha256', 'derived_from', 'purpose')}
out.update(cases=cases, corpus_sha256=hash_obj(cases), derived_from={'session': a.session},
           purpose='CFG-CPUSHARE-S: follow-up reads of about 3K and 7-13K tokens replayed in order, plus the greedy decode control')
p = ROOT / ('workspace/corpora/cpushare-%s.json' % out['corpus_sha256'][:12])
dump(p, out)
print(p, len(cases))
print('prompt tokens and growth per step:', sizes)
