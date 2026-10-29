"""Long-context decode corpus for CFG-IL0 / CFG-EXACT: a ledger at 4K/32K/64K/120K plus a code-writing task that keeps
generating past 512 tokens, greedy and with Pi sampling; plus the short fixed-512 decode cases of the MIG corpus."""
import copy, json, sys
sys.path.insert(0, '.')
from lab.core import hash_obj, dump, load_config
from lab.corpus import SYSTEM, fit_ledger
from lab.tokenizer import StrataCounter
from lab.workspace import baseline_dir

c = load_config('config/local.json')
counter = StrataCounter(baseline_dir(c), c['gguf'], c['template'])
mig = json.load(open('workspace/corpora/mig-523966959432.json'))
TASK = ('\nNow ignore the earlier answer format. Write a complete Java 21 implementation of a ConfigLedgerService for the '
        'ledger above: a record type per entry, a parser for these lines, validation of every field, indexes by module and '
        'by owner, an immutable snapshot API, and JUnit 5 tests for each method. Output only code, no explanation. '
        'Do not stop early.')
cases = [x for x in mig['cases'] if x['group'] in ('decode', 'decode-sampled')]
for k, target in enumerate([4096, 32768, 65536, 122880]):
    # Leave room for the task text and 512 output tokens under the target.
    b, _ = fit_ledger(counter, target - 160, 20261025 + k, SYSTEM + f' Long decode scenario D{k}.')
    b['messages'][-1]['content'] = b['messages'][-1]['content'].rsplit('\nReturn only', 1)[0] + TASK
    b['max_tokens'] = 512
    g = {'id': f'ldec-{target}', 'kind': 'performance', 'group': 'long-decode', 'fixed_output': 512, 'body': b}
    s = copy.deepcopy(g); s['id'] += '-sampled'; s['group'] = 'long-decode-sampled'
    s['body'].update({'temperature': 1.0, 'top_p': 0.95, 'top_k': 20})
    for x in (g, s):
        x['request_sha256'] = hash_obj(x['body']); x['prompt_tokens_local'] = counter(x['body'])
    cases += [g, s]
out = {k: v for k, v in mig.items() if k not in ('cases', 'corpus_sha256')}
out.update(cases=cases, corpus_sha256=hash_obj(cases), derived_from=mig['corpus_sha256'],
           purpose='CFG decode: short fixed-512 decode + long-context code decode at 4K/32K/64K/120K, greedy and Pi sampling')
p = 'workspace/corpora/decode-%s.json' % out['corpus_sha256'][:12]
dump(p, out)
print(p, len(cases), [(x['id'], x['prompt_tokens_local']) for x in cases if x['group'].startswith('long')])
