#!/usr/bin/env python3
"""Offline summary of a Strata serve engine log (L0, no content): one record per request from the engine's own lines.

    python3 -B tools/prodlog.py ENGINE_LOG [ENGINE_LOG ...] [--json OUT] [--since 'YYYY-MM-DD HH:MM:SS']

Each request ends with `strata serve: prompt N tokens = R reused + X read ...`.  Lines are attached by where the engine
prints them: `decode timing` and `conversation cache: restored` come before that summary (same request); the
checkpoint pool, expert cache hit rate, KV streaming, suffix drafts and every other `conversation cache:` line come
after it (the request just summarised).  An `engine started:` line opens a new epoch (it carries the only wall time).
Format source: Strata v0.2.17 engine/src/program/generate.cpp.  The log carries no prompt or answer text.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

START = re.compile(r'^\[strata\] (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) engine started: (\S+)')
PROMPT = re.compile(r'strata serve: prompt (\d+) tokens = (\d+) reused \+ (\d+)(?: of (\d+))? read in (\d+) ms \([\d.]+ tok/s\), '
                    r'(\d+) generated in (\d+) ms \([\d.]+ tok/s\), drafts accepted (\d+) of (\d+), (\d+) checkpoints( \(cancelled\))?')
TIMING = re.compile(r'decode timing: (\d+) windows, avg T ([\d.]+), ([\d.]+) tokens/window, ([\d.]+) ms/window = .*?GPU-reach wait ([\d.]+) '
                    r'\+ per-layer host ([\d.]+) \[.*?CPU ([\d.]+)\].*?CPU experts ([\d.]+) \(([\d.]+) entries\)')
HIT = re.compile(r'decode expert cache hit rate: ([\d.]+)%')
RESTORED = re.compile(r'conversation cache: restored (\d+) tokens \((\w+)\) in ([\d.]+) ms')
BORROWED = re.compile(r'conversation cache: borrowed (\d+) tokens from a parked conversation.*? in ([\d.]+) ms')
PARKED = re.compile(r'conversation cache: (parked|skipped) (\d+) tokens.*? in ([\d.]+) ms; parked=(\d+) bytes=(\d+) evictions=(\d+)')
EVICTED = re.compile(r'conversation cache: evicted (\d+) parked conversation')
CONV = re.compile(r'strata serve: conversation cache: (.*)')
BEFORE = ('decode timing', 'conversation cache: restored', 'conversation cache: borrowed', 'conversation cache: read ', 'conversation cache: took ',
          'conversation cache: the state at')
BUCKETS = ((0, 4096, '<4K'), (4096, 32768, '4K-32K'), (32768, 65536, '32K-64K'), (65536, 1 << 30, '>=64K'))


def bucket(n: int) -> str:
    return next(name for lo, hi, name in BUCKETS if lo <= n < hi)


def parse(lines, since: str | None = None) -> list[dict]:
    reqs, pending, last, epoch = [], [], None, None
    for raw in lines:
        line = raw.rstrip('\n')
        m = START.search(line)
        if m:
            epoch = {'started': m.group(1), 'exe': m.group(2)}
            pending, last = [], None
            continue
        if since and (epoch is None or epoch['started'] < since):
            continue
        m = PROMPT.search(line)
        if m:
            n, reused, fresh, of, pms, gen, dms, acc, off, ck, canc = m.groups()
            r = dict(epoch=epoch['started'] if epoch else None, prompt=int(n), reused=int(reused), read=int(fresh),
                     read_planned=int(of) if of else int(fresh), prompt_ms=int(pms), generated=int(gen), decode_ms=int(dms),
                     drafts_accepted=int(acc), drafts_offered=int(off), checkpoints=int(ck), cancelled=bool(canc),
                     timing=[], restored=None, hit_rate=None, park=None, evicted=0, conv_notes=[])
            for p in pending:
                attach(r, p)
            pending = []
            reqs.append(r)
            last = r
            continue
        if 'decode timing' in line or 'conversation cache' in line or 'decode expert cache hit rate' in line:
            if any(k in line for k in BEFORE):
                pending.append(line)
            elif last is not None:
                attach(last, line)
    return reqs


def attach(r: dict, line: str) -> None:
    m = TIMING.search(line)
    if m:
        w, t, tw, ms, reach, host, cpu, ce, ent = (float(x) for x in m.groups())
        r['timing'].append(dict(windows=int(w), avg_t=t, tok_win=tw, ms_win=ms, reach=reach, host=host, cpu=cpu, cpu_experts=ce, cpu_entries=ent))
        return
    m = HIT.search(line)
    if m:
        r['hit_rate'] = float(m.group(1))
        return
    m = RESTORED.search(line)
    if m:
        r['restored'] = dict(tokens=int(m.group(1)), source=m.group(2), ms=float(m.group(3)))
        return
    m = BORROWED.search(line)
    if m:
        r['restored'] = dict(tokens=int(m.group(1)), source='borrowed', ms=float(m.group(2)))
        return
    m = PARKED.search(line)
    if m:
        r['park'] = dict(stored=m.group(1) == 'parked', tokens=int(m.group(2)), ms=float(m.group(3)), parked=int(m.group(4)),
                         bytes=int(m.group(5)), evictions_total=int(m.group(6)))
        return
    m = EVICTED.search(line)
    if m:
        r['evicted'] += int(m.group(1))
        return
    m = CONV.search(line)
    if m:
        r['conv_notes'].append(m.group(1)[:160])


def _med(x):
    x = [v for v in x if v is not None]
    return round(statistics.median(x), 3) if x else None


def summarize(reqs: list[dict]) -> dict:
    s = dict(requests=len(reqs), cancelled=sum(r['cancelled'] for r in reqs))
    tot = sum(r['prompt'] for r in reqs)
    s['prompt_tokens'] = tot
    s['reused_tokens'] = sum(r['reused'] for r in reqs)
    s['read_tokens'] = sum(r['read'] for r in reqs)
    s['reuse_ratio'] = round(s['reused_tokens'] / tot, 4) if tot else None
    s['read_seconds'] = round(sum(r['prompt_ms'] for r in reqs) / 1000, 1)
    s['decode_seconds'] = round(sum(r['decode_ms'] for r in reqs) / 1000, 1)
    s['generated_tokens'] = sum(r['generated'] for r in reqs)
    cold = [r for r in reqs if r['reused'] == 0 and r['prompt'] >= 8192]
    s['cold_reads_ge_8k'] = dict(count=len(cold), tokens=sum(r['read'] for r in cold), seconds=round(sum(r['prompt_ms'] for r in cold) / 1000, 1))
    big_read = [r for r in reqs if r['reused'] > 0 and r['read'] >= 8192]
    s['partial_reuse_reads_ge_8k'] = dict(count=len(big_read), tokens=sum(r['read'] for r in big_read),
                                          seconds=round(sum(r['prompt_ms'] for r in big_read) / 1000, 1))
    s['restores'] = dict(count=sum(r['restored'] is not None for r in reqs),
                         live=sum(1 for r in reqs if r['restored'] and r['restored']['source'] == 'live'),
                         checkpoint=sum(1 for r in reqs if r['restored'] and r['restored']['source'] == 'checkpoint'),
                         borrowed=sum(1 for r in reqs if r['restored'] and r['restored']['source'] == 'borrowed'))
    s['parks'] = sum(1 for r in reqs if r['park'] and r['park']['stored'])
    s['park_skips'] = sum(1 for r in reqs if (r['park'] and not r['park']['stored']) or any(n.startswith('skip parking') for n in r['conv_notes']))
    s['evictions'] = sum(r['evicted'] for r in reqs)
    s['park_evictions_counter_max'] = max((r['park']['evictions_total'] for r in reqs if r['park']), default=0)   # engine's running count
    s['by_prompt_bucket'] = {}
    for _, _, name in BUCKETS:
        rs = [r for r in reqs if bucket(r['prompt']) == name]
        if not rs:
            continue
        tw = [t for r in rs for t in r['timing']]
        s['by_prompt_bucket'][name] = dict(
            requests=len(rs), reuse_ratio=round(sum(r['reused'] for r in rs) / max(1, sum(r['prompt'] for r in rs)), 4),
            read_tok_s=_med([1000 * r['read'] / r['prompt_ms'] for r in rs if r['prompt_ms'] > 0 and r['read'] >= 512]),
            decode_tok_s=_med([1000 * r['generated'] / r['decode_ms'] for r in rs if r['decode_ms'] > 0 and r['generated'] >= 64]),
            accept=_med([r['drafts_accepted'] / r['drafts_offered'] for r in rs if r['drafts_offered']]),
            ms_win=_med([t['ms_win'] for t in tw]), tok_win=_med([t['tok_win'] for t in tw]), reach=_med([t['reach'] for t in tw]),
            cpu_entries=_med([t['cpu_entries'] for t in tw]), hit_rate=_med([r['hit_rate'] for r in rs]))
    s['epochs'] = sorted({r['epoch'] for r in reqs if r['epoch']})
    return s


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('logs', nargs='+')
    ap.add_argument('--json')
    ap.add_argument('--since', help="only epochs started at or after this wall time ('YYYY-MM-DD HH:MM:SS')")
    a = ap.parse_args(argv)
    reqs = []
    for p in a.logs:
        with open(p, errors='replace') as f:
            reqs += parse(f, a.since)
    s = summarize(reqs)
    if a.json:
        Path(a.json).write_text(json.dumps(dict(summary=s, requests=reqs), indent=1) + '\n')
    json.dump(s, sys.stdout, indent=1)
    print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
