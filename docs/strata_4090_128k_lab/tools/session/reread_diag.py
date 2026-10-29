"""Why a follow-up turn re-reads the previous reply: text divergence (template trim / re-render) or BPE (the model's
generated ids are not the canonical encoding of the same text).

For turn t: live = render(prompt_t) + raw_t (the engine's decoded generated ids, from STRATA_DEBUG's '[strata] raw:'
line); next = render(prompt_{t+1}).  Reports where `next` first leaves `live` (relative to the reply start) and, for
the reply text, len(encode(raw_t)) vs the generated token count.

  python reread_diag.py workspace/reports/session/nobudget-debug
"""
import ast, copy, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab.core import load_config
from lab.tokenizer import StrataCounter
from lab.workspace import baseline_dir

folder = Path(sys.argv[1])
c = load_config(ROOT / 'config/local.json')
sc = StrataCounter(baseline_dir(c), c['gguf'], c['template'])
f, tok = sc.frontend, sc.tokenizer
s = json.loads((folder / 'session.json').read_text())
msgs, rows = s['messages'], s['rows']
log = '\n'.join(p.read_text(errors='replace') for p in sorted(folder.glob('*.log')))
raws = [ast.literal_eval(x) for x in re.findall(r"\[strata\] raw: ('.*'|\".*\")$", log, re.M)]
engine = re.findall(r'prompt (\d+) tokens = (\d+) reused \+ (\d+) read', log)
print('turns', len(rows), 'raw lines', len(raws))


def render(body):
    m, tools, kw = f.openai_to_messages(copy.deepcopy(body))
    m, tools, changed = f.mark_think_literals(m, tools, sc.tags)
    text = sc.template.render(m, tools=tools, **kw)
    plain = ()
    if changed: text, plain = f.unmark_think_literals(text, sc.tags)
    return text, plain


def body(t):
    b = {'model': 'strata', 'messages': msgs[:2 + 2 * t], 'temperature': 1.0, 'top_p': 0.95, 'top_k': 20,
         'reasoning_effort': 'xhigh'}
    pt = s['args'].get('preserve_thinking')
    if pt == 'false': b['chat_template_kwargs'] = {'preserve_thinking': False}
    return b


out = []
for t in range(min(len(rows) - 1, len(raws))):
    cur, _ = render(body(t))
    nxt, plain = render(body(t + 1))
    raw = raws[t]
    live = cur + raw
    i = 0
    n = min(len(live), len(nxt))
    while i < n and live[i] == nxt[i]: i += 1
    rel = i - len(cur)
    gen = rows[t]['generated_tokens']
    canon = len(tok.encode(raw, parse_special=True))
    r = rows[t + 1]
    rec = {'turn': t, 'next_reused': r['reused_tokens'], 'next_read': r['read_tokens'], 'prompt_t': rows[t]['prompt_tokens'],
           'reply_chars': len(raw), 'text_agrees_through_reply': rel >= len(raw) or live[len(cur):].rstrip() == nxt[len(cur):len(cur) + len(raw)].rstrip(),
           'first_text_diff_in_reply': rel if rel < len(raw) else None,
           'live_ctx': raw[max(0, rel - 30):rel + 30] if rel < len(raw) else '',
           'next_ctx': nxt[len(cur) + max(0, rel - 30):len(cur) + rel + 30] if rel < len(raw) else '',
           'generated': gen, 'canonical_tokens_of_raw': canon, 'bpe_differs': gen is not None and canon != gen}
    out.append(rec)
    print(json.dumps(rec, ensure_ascii=False))
(folder / 'reread_diag.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
