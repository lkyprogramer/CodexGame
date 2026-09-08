#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import http_bench as hb
ROOT=Path(__file__).resolve().parents[1]; RES=ROOT/'results'
E=hb.E

def main():
    target=int(E.get('CACHE_PROMPT_TOKENS',100000)); corpus,meta=hb.prompt_for(target)
    base='This is a Java repository snapshot. Remember the release marker and analyze reconnect invariants.\n'+corpus
    m1=[{'role':'user','content':base}]
    print('[cache] cold turn',flush=True); r1=hb.stream_chat(m1,96,'cache-cold')
    print('[cache] exact repeat',flush=True); r2=hb.stream_chat(m1,96,'cache-exact')
    # Growing Agent loop: include prior assistant output, then a small new user/tool-like tail.
    tail='\n'.join(f'TOOL_RESULT line={i} reconnectAttempt={i%3} status=OK' for i in range(300))
    m3=m1+[{'role':'assistant','content':r1['text']},{'role':'user','content':'A tool just returned the following new tail. Re-evaluate only what changed and state the original RELEASE_NEEDLE exactly.\n'+tail}]
    print('[cache] growing append turn',flush=True); r3=hb.stream_chat(m3,128,'cache-append')
    for r in (r1,r2,r3): print(f"[cache] {r['tag']} prompt={r['prompt_tokens']} cached={r['cached_tokens']} ttft={r['ttft_s']} wall={r['wall_s']}",flush=True)
    (RES/'cache_bench.json').write_text(json.dumps([r1,r2,r3],indent=2))
if __name__=='__main__': main()
