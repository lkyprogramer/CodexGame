"""Write one corpus case's prompt as the token IDs the server would send the engine, for `strata generate --tokens-file`.

Same rendering as lab.tokenizer.StrataCounter (the pinned Strata frontend, template and tokenizer), so a generate run
reads the exact prompt of the Pi-shaped serve request.  The engine's `generate` summary splits the CPU pool's time
into gate/up, quantize and down, which the serve path does not print.

  python tools/analysis/np3_tokens.py workspace/corpora/spec-<sha>.json spec-think-t0-a workspace/np3/t0.tokens
"""
import copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab.core import load_config
from lab.tokenizer import StrataCounter
from lab.workspace import baseline_dir

corpus, case_id, out = sys.argv[1:4]
c = load_config(str(ROOT / 'config/local.json'))
sc = StrataCounter(baseline_dir(c), c['gguf'], c['template'])
case = next(x for x in json.loads(Path(corpus).read_text())['cases'] if x['id'] == case_id)
f, body = sc.frontend, case['body']
messages, tools, kw = f.openai_to_messages(copy.deepcopy(body))
if body.get('tool_choice') == 'none':
    tools = None
messages, tools, changed = f.mark_think_literals(messages, tools, sc.tags)
rendered = sc.template.render(messages, tools=tools, **kw)
plain = ()
if changed:
    rendered, plain = f.unmark_think_literals(rendered, sc.tags)
ids = sc.tokenizer.encode(rendered, parse_special=True, plain=plain)
assert len(ids) == sc(body)
Path(out).write_text(','.join(str(i) for i in ids) + '\n')
print(out, len(ids))
