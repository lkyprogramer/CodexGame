"""Single long session, Pi-shaped: one conversation, follow-up turns only, no switching, no concurrency.

Each turn appends a deterministic ~3K-token Java source file plus an analysis question; the request carries Pi's
wire format (reasoning_effort xhigh, temperature 1.0 / top_p 0.95 / top_k 20, the previous turns' thinking sent back
as reasoning_content).  Thinking is capped with reasoning_budget_tokens so a run stays bounded.  Stops when the
prompt passes --stop-tokens.  Per turn: prompt / reused / read tokens, TTFT, decode tok/s, thinking and answer size.

  python session_bench.py --name base [--preserve-thinking false] [--env K=V] [--tree DIR] [--arg=--flag=V]
"""
import argparse, copy, json, random, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]   # lab package root
sys.path.insert(0, str(ROOT))
from lab import http
from lab.core import dump, load_config
from lab.runner import OwnedServer, wait_released
from lab.workspace import baseline_dir

OUT = ROOT / 'workspace/reports/session'
SYSTEM = ('You are a senior Java backend engineer helping one developer over a long working session on a payment '
          'service codebase. Answer precisely, cite class and method names, and keep answers focused.')
TYPES = ['Long', 'String', 'BigDecimal', 'Instant', 'UUID', 'Integer', 'Boolean', 'List<String>', 'Map<String, Long>']
NOUNS = ['Payment', 'Ledger', 'Refund', 'Settlement', 'Merchant', 'Invoice', 'Payout', 'Account', 'Transfer', 'Fee',
         'Dispute', 'Webhook', 'Batch', 'Quota', 'Audit', 'Tenant', 'Wallet', 'Rate', 'Order', 'Token']
QUESTIONS = [
    'Review {c} for thread-safety and transaction-boundary problems. List concrete defects with method names.',
    'How does {c} interact with the classes we discussed earlier? Point out inconsistent invariants.',
    'Find the riskiest null-handling and overflow paths in {c} and propose minimal fixes.',
    'Which methods of {c} would you cover first with JUnit 5 tests, and what edge cases?',
    'Propose a refactoring of {c} that removes duplication without changing behavior. Be specific.',
]


def java_file(i, rng):
    noun = NOUNS[i % len(NOUNS)] + ('V%d' % (i // len(NOUNS)) if i >= len(NOUNS) else '')
    cls = noun + 'Service'
    lines = [f'package com.example.pay.{noun.lower()};', '', 'import java.math.BigDecimal;', 'import java.time.Instant;',
             'import java.util.*;', 'import java.util.concurrent.*;', '', f'/** Handles {noun.lower()} lifecycle. */',
             f'public class {cls} {{']
    fields = []
    for f in range(rng.randint(8, 12)):
        t = rng.choice(TYPES); n = f'{rng.choice(["pending", "settled", "retry", "limit", "owner", "region", "cursor"])}{f}'
        fields.append((t, n)); lines.append(f'    private {"volatile " if rng.random() < .2 else ""}{t} {n};')
    lines.append(f'    private final Map<String, {noun}Record> cache = new {"ConcurrentHashMap" if rng.random() < .5 else "HashMap"}<>();')
    while sum(len(x) for x in lines) < 11000:
        m = f'{rng.choice(["apply", "settle", "reconcile", "validate", "load", "retry", "merge", "split"])}{noun}{len(lines)}'
        t, n = rng.choice(fields)
        lines += ['', f'    /** {m}: updates {n} and the cache entry for the given key. */',
                  f'    public synchronized {noun}Record {m}(String key, {t} value, int attempts) {{' if rng.random() < .4 else
                  f'    public {noun}Record {m}(String key, {t} value, int attempts) {{',
                  f'        if (key == null || attempts > {rng.randint(3, 9)}) {{',
                  f'            throw new IllegalArgumentException("bad key or attempts: " + key);', '        }',
                  f'        {noun}Record current = cache.get(key);',
                  '        if (current == null) {',
                  f'            current = new {noun}Record(key, Instant.now(), {rng.randint(1, 500)});',
                  '            cache.put(key, current);', '        }',
                  f'        long total = current.amount() * {rng.randint(100, 100000)}L + attempts;',
                  f'        this.{n} = value;',
                  f'        return current.withAmount(total).withNote("{m} #" + attempts);', '    }']
    lines += ['', f'    public record {noun}Record(String key, Instant at, long amount) {{',
              f'        {noun}Record withAmount(long a) {{ return new {noun}Record(key, at, a); }}',
              f'        {noun}Record withNote(String n) {{ return this; }}', '    }', '}']
    return cls, '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--config', default=str(ROOT / 'config/local.json'))
    ap.add_argument('--preserve-thinking', default='default', choices=['default', 'false'])
    ap.add_argument('--budget', type=int, default=2048)
    ap.add_argument('--max-tokens', type=int, default=32768)   # Pi's maxTokens for this model
    ap.add_argument('--stop-tokens', type=int, default=110000)
    ap.add_argument('--max-turns', type=int, default=40)
    ap.add_argument('--seed', type=int, default=20261025)
    ap.add_argument('--env', action='append', default=[])
    ap.add_argument('--arg', action='append', default=[])
    ap.add_argument('--tree', default='')
    a = ap.parse_args()
    c = load_config(a.config)
    tree = Path(a.tree) if a.tree else baseline_dir(c)
    ready = {'cfg': {'env': dict(x.split('=', 1) for x in a.env), 'args': dict(x.split('=', 1) for x in a.arg)}}
    arm = 'cfg' if (a.env or a.arg) else 'base'
    folder = OUT / a.name
    rng = random.Random(a.seed)
    msgs = [{'role': 'system', 'content': SYSTEM}]
    rows = []
    est = 0   # Pi's view of the context: the last prompt + its reply + the new message (chars / 3)
    wait_released(c)
    with OwnedServer(c, tree, arm, ready, folder) as srv:
        for turn in range(a.max_turns):
            cls, src = java_file(turn, rng)
            q = QUESTIONS[turn % len(QUESTIONS)].format(c=cls)
            msgs.append({'role': 'user', 'content': f'Here is {cls}.java:\n```java\n{src}\n```\n{q}'})
            est += len(msgs[-1]['content']) // 3
            # pi-ai clampMaxTokensToContext: min(maxTokens, contextWindow - estimate - 4096)
            max_new = min(a.max_tokens, c['max_context'] - est - 4096)
            if max_new < 1024: break
            body = {'model': 'strata', 'messages': msgs, 'max_tokens': max_new, 'temperature': 1.0, 'top_p': 0.95,
                    'top_k': 20, 'reasoning_effort': 'xhigh'}
            if a.budget > 0: body['reasoning_budget_tokens'] = a.budget   # 0: no budget, as Pi sends it
            if a.preserve_thinking == 'false': body['chat_template_kwargs'] = {'preserve_thinking': False}
            r = http.chat(srv.base, body, srv.key, timeout=1800)
            m = http.measurements(r)
            row = dict(turn=turn, max_tokens=max_new, error=r.get('error'), finish=r.get('finish_reason'),
                       reasoning_chars=len(r.get('reasoning') or ''), answer_chars=len(r.get('text') or ''), **m,
                       reasoning=r.get('reasoning') or '', text=r.get('text') or '')
            rows.append(row)
            print(a.name, turn, 'prompt', m['prompt_tokens'], 'reused', m['reused_tokens'], 'read', m['read_tokens'],
                  'ttft', round(m['ttft_s'] or -1, 2), 'gen', m['generated_tokens'], 'dec_tps',
                  round(m['decode_tps'] or -1, 1), 'think_ch', row['reasoning_chars'], 'ans_ch', row['answer_chars'],
                  r.get('error') or '', flush=True)
            if r.get('error'): break
            am = {'role': 'assistant', 'content': r.get('text') or ''}
            if r.get('reasoning'): am['reasoning_content'] = r['reasoning']   # Pi sends thinking back this way
            msgs.append(am)
            est = (m['prompt_tokens'] or 0) + (m['generated_tokens'] or 0)
            if est > a.stop_tokens: break
    dump(folder / 'session.json', {'name': a.name, 'args': vars(a), 'rows': rows, 'abort': srv.abort_reason,
                                   'messages': msgs})


if __name__ == '__main__':
    main()
