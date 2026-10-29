"""Decode corpus for CFG-SPEC-S (--spec width under Pi sampling + thinking).

Pi-shaped cases come from a recorded single-session run (workspace/reports/session/<name>/session.json): the
conversation cut at a few turns, so the prompts are real follow-up histories with thinking sent back.  Each cut gets
two variants, both fixed to 2048 output tokens:
  spec-think   no reasoning budget: the whole output is thinking (about 2/3 of what Pi generates)
  spec-answer  reasoning_budget_tokens 128: thinking closes early and the output is the visible answer
Each variant is repeated (copies -a/-b) because sampled outputs differ.  The greedy decode cases of the CFG decode
corpus are appended as a control.

  python tools/analysis/mkspec.py --session r1536-off-1 --turns 0,2,3,5 --decode workspace/corpora/decode-<sha>.json
"""
import argparse, copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab.core import hash_obj, dump, load_config
from lab.tokenizer import StrataCounter
from lab.workspace import baseline_dir

ap = argparse.ArgumentParser()
ap.add_argument('--session', default='r1536-off-1')
ap.add_argument('--turns', default='0,2,3,5')
ap.add_argument('--decode', required=True, help='CFG decode corpus; its greedy groups are the control')
ap.add_argument('--max-tokens', type=int, default=2048)
ap.add_argument('--copies', type=int, default=2)
a = ap.parse_args()

c = load_config(str(ROOT / 'config/local.json'))
counter = StrataCounter(baseline_dir(c), c['gguf'], c['template'])
sess = json.loads((ROOT / 'workspace/reports/session' / a.session / 'session.json').read_text())
msgs, rows = sess['messages'], sess['rows']
dec = json.loads(Path(a.decode).read_text())

cases, drift = [], []
for t in (int(x) for x in a.turns.split(',')):
    # system + t (user, assistant) pairs + the user message of turn t
    hist = copy.deepcopy(msgs[:2 + 2 * t])
    assert hist[-1]['role'] == 'user'
    base = {'model': 'strata', 'messages': hist, 'max_tokens': a.max_tokens, 'temperature': 1.0, 'top_p': 0.95,
            'top_k': 20, 'reasoning_effort': 'xhigh'}
    n = counter(base)
    drift.append((t, n, rows[t]['prompt_tokens']))   # the server's count when this prompt was first sent
    for group, extra in (('spec-think', {}), ('spec-answer', {'reasoning_budget_tokens': 128})):
        for k in range(a.copies):
            body = {**copy.deepcopy(base), **extra}
            x = {'id': f'{group}-t{t}-{chr(97 + k)}', 'kind': 'performance', 'group': group,
                 'fixed_output': a.max_tokens, 'body': body}
            x['request_sha256'] = hash_obj(body); x['prompt_tokens_local'] = n
            cases.append(x)
cases += [x for x in dec['cases'] if x['group'] in ('decode', 'long-decode')]
out = {k: v for k, v in dec.items() if k not in ('cases', 'corpus_sha256', 'derived_from', 'purpose')}
out.update(cases=cases, corpus_sha256=hash_obj(cases), derived_from={'session': a.session, 'decode': dec['corpus_sha256']},
           purpose='CFG-SPEC-S: Pi sampled + thinking decode at real follow-up histories, plus the greedy decode control')
p = ROOT / ('workspace/corpora/spec-%s.json' % out['corpus_sha256'][:12])
dump(p, out)
print(p, len(cases))
print('local count vs recorded server prompt_tokens:', drift)
