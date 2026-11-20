"""Build the frozen request fixtures for the v0.2.16 baseline campaign: real source files, exact token counts from the pack tokenizer."""
import json, sys, hashlib
from pathlib import Path
BD = Path(sys.argv[1]); TERM = BD / 'src/terminal'; TDIR = Path('/data/strata-data/packs/iq3_xxs/tokenizer')
sys.path[:0] = [str(TERM), str(TERM / 'tools')]
import strata_tokenizer as ST
from serve.frontend import ChatTemplate, openai_to_messages
from serve.server import MockEngine, Service
vocab = json.loads((TDIR / 'vocab.json').read_text(encoding='utf-8'))
tokens = [None] * len(vocab)
for t, i in vocab.items():
    tokens[i] = t
tcfg = json.loads((TDIR / 'tokenizer.json').read_text(encoding='utf-8'))
tok = ST.Tokenizer(tokens, (TDIR / 'merges.txt').read_text(encoding='utf-8').split('\n'),
                   json.loads((TDIR / 'token_type.json').read_text()), tcfg.get('pre') or 'qwen35', tcfg.get('special_ids') or None)
svc = Service(MockEngine(tok, 'ok'), tok, ChatTemplate(TDIR / 'chat_template.jinja'))

def count(body):
    m, tl, kw = openai_to_messages(body)
    return len(svc.encode_prompt(m, tl, kw))

# real code, one pool per request so no two requests share a prefix beyond the system line
src = BD / 'src'
pool = sorted([p for p in (src / 'engine/src').rglob('*.cpp')] + [p for p in (src / 'engine/src').rglob('*.cu')], key=lambda p: str(p))
pool = [p for p in pool if 2000 < p.stat().st_size < 120000]
py = sorted((src / 'terminal').rglob('*.py'), key=lambda p: str(p))
py = [p for p in py if 2000 < p.stat().st_size < 120000 and 'test' not in p.name]
used = set()
def take(files, target, question, sysline, prior=None, budget=None):
    parts = []
    for p in files:
        if p in used:
            continue
        txt = p.read_text(encoding='utf-8', errors='replace')
        trial = parts + ['// FILE: %s\n%s' % (p.relative_to(src), txt)]
        msgs = (prior or []) + [{'role': 'user', 'content': '\n\n'.join(trial) + '\n\n' + question}]
        n = count({'messages': [{'role': 'system', 'content': sysline}] + msgs})
        if n > target:
            continue
        parts = trial
        used.add(p)
        if n > target * 0.97:
            break
    msgs = (prior or []) + [{'role': 'user', 'content': '\n\n'.join(parts) + '\n\n' + question}]
    return [{'role': 'system', 'content': sysline}] + msgs
SYS = 'You are a senior backend engineer reviewing a large C++/CUDA and Python inference codebase with one developer over a long session. Request id: %s.'
Q = 'Review the code above. Think it through, then list concrete defects (file, function, why it is wrong, minimal fix), most severe first.'
out = {}
def fixture(name, messages, max_tokens):
    body = {'messages': messages, 'max_tokens': max_tokens, 'temperature': 0, 'stream': True,
            'stream_options': {'include_usage': True}}
    out[name] = {'body': body, 'prompt_tokens': count(body)}
fixture('d3k', take(py, 3000, Q, SYS % 'd3k'), 1536)
c32 = take(pool, 32000, Q, SYS % 'c32k')
fixture('c32k', c32, 256)
ANSWER = ('Findings, most severe first:\n' + '\n'.join('%d. In the reviewed file the error path at this point does not release the buffer it took; release it before returning.' % i for i in range(1, 41)))
follow = c32 + [{'role': 'assistant', 'content': ANSWER}]
fixture('f10k', take(pool, 32000 + 10000 + count({'messages': [{'role': 'assistant', 'content': ANSWER}]}), 'Here are more files that call into the ones above. ' + Q, SYS % 'c32k', prior=follow[1:]), 512)
fixture('c100k', take(pool, 100000, Q, SYS % 'c100k'), 1024)
for k, v in out.items():
    assert v['prompt_tokens'] + v['body']['max_tokens'] + 4096 <= 131072, k
    print(k, v['prompt_tokens'], v['body']['max_tokens'], len(json.dumps(v['body'])))
f = BD / 'fixtures.json'
f.write_text(json.dumps(out, ensure_ascii=False))
print('sha256', hashlib.sha256(f.read_bytes()).hexdigest())
