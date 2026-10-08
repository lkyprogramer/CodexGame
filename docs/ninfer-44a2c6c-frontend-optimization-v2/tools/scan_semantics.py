#!/usr/bin/env python3
"""Finite added-token scanner model. NOT a Qwen tokenizer or product qualification."""
from __future__ import annotations
import argparse, json, random
from pathlib import Path

def vocabulary(tokens: list[tuple[int,bytes]]) -> list[tuple[int,bytes]]:
    out=sorted(tokens)
    if len({i for i,_ in out})!=len(out):raise ValueError('duplicate token ID')
    if any(not isinstance(i,int) or not isinstance(s,bytes) or not s for i,s in out):raise ValueError('nonempty byte tokens and integer IDs required')
    return out

def legacy(data: bytes,tokens: list[tuple[int,bytes]]) -> list[tuple[int,int,int]]:
    ts=vocabulary(tokens);out=[];pos=0
    while pos<len(data):
        best=None
        for i,t in ts:
            k=data.find(t,pos)
            if k>=0 and (best is None or k<best[0]):best=(k,k+len(t),i)
        if best is None:break
        out.append(best);pos=best[1]
    return out

def forward(data: bytes,tokens: list[tuple[int,bytes]]) -> tuple[list[tuple[int,int,int]],dict]:
    buckets={}
    for i,t in vocabulary(tokens):buckets.setdefault(t[0],[]).append((i,t))
    out=[];pos=0;visited=checks=0
    while pos<len(data):
        visited+=1;best=None
        for i,t in buckets.get(data[pos],[]):
            checks+=1
            if data.startswith(t,pos):best=(pos,pos+len(t),i);break
        if best is None:pos+=1
        else:out.append(best);pos=best[1]
    return out,{'positions_visited':visited,'candidate_checks':checks,'selected_added_tokens':len(out)}

def check_prefix_decomposition(data: bytes,tokens: list[tuple[int,bytes]]) -> bool:
    """Compare scanner choices for ALL cuts of this finite sample, not BPE/NFC output."""
    full=legacy(data,tokens)
    for cut in range(len(data)+1):
        prefix=[m for m in full if m[1]<=cut]
        restart=prefix[-1][1] if prefix else 0
        local=[(a+restart,b+restart,i) for a,b,i in legacy(data[restart:cut],tokens)]
        if prefix+local!=legacy(data[:cut],tokens):return False
    return True

def random_check(seed: int,iterations: int) -> dict:
    if iterations<1:raise ValueError('iterations must be positive')
    rng=random.Random(seed);ts=[(300,b'<a>'),(301,b'<a>x'),(302,b'ab'),(303,b'aba'),(304,b'\xff'),(305,b'</a>')]
    parts=[b'a',b'b',b'<',b'>',b'x',b'\0',b'\xff',b'<a>',b'</a>',b'<a',b'e\xcc\x81']
    cuts=0;positions=0
    for _ in range(iterations):
        data=b''.join(rng.choice(parts) for _ in range(rng.randrange(0,22)))
        one,w=forward(data,ts)
        if one!=legacy(data,ts) or not check_prefix_decomposition(data,ts):raise AssertionError('scanner/prefix model mismatch')
        if w['positions_visited']>len(data):raise AssertionError('nonmonotone scan')
        cuts+=len(data)+1;positions+=w['positions_visited']
    return {'status':'PASS','scope':'FINITE_LEXICAL_REFERENCE_MODEL_ONLY','seed':seed,'samples':iterations,'byte_cuts_checked':cuts,'positions_visited':positions,'ninfer_product_tested':False}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seed',type=int,default=20260925);p.add_argument('--iterations',type=int,default=20000);p.add_argument('--output',type=Path);a=p.parse_args()
    text=json.dumps(random_check(a.seed,a.iterations),indent=2)+'\n'
    if a.output:a.output.write_text(text)
    else:print(text,end='')
    return 0
if __name__=='__main__':raise SystemExit(main())
