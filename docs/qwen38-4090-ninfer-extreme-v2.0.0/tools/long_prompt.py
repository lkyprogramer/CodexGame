"""Capacity-only synthetic corpus, not a decode-speed or intelligence benchmark.
Requires optional tokenizers in an isolated controller venv. Chat template overhead
is NOT counted here: enforce actual server prompt_tokens + output <= capacity.
"""
import argparse,hashlib,json,random
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',required=True);p.add_argument('--tokens',type=int,default=258000);p.add_argument('--model',default='qwen3.8-27b-lab');p.add_argument('--out',required=True);p.add_argument('--seed',type=int,default=4090);a=p.parse_args()
    if not 4096<=a.tokens<=258000:raise SystemExit('supported capacity-probe raw-content range is 4096..258000')
    try:from tokenizers import Tokenizer
    except ImportError:raise SystemExit('Install optional tokenizers in the isolated controller venv; do not modify system Python')
    tok=Tokenizer.from_file(a.tokenizer);rng=random.Random(a.seed);pieces=[];ids=[]
    while len(ids)<a.tokens:
        off=len(pieces)
        for i in range(off,off+2048):
            nonce=hashlib.sha256(f'{a.seed}:{i}'.encode()).hexdigest()[:16]
            pieces.append(f'// shard={i} revision={nonce}\nfinal class Entry{i} {{ long tick = {rng.randrange(10,999999)}L; String key = "{nonce}"; }}\n')
        ids=tok.encode(''.join(pieces),add_special_tokens=False).ids
    base=ids[:a.tokens-512];prev=0;chunks=[];answers={}
    for n,frac in enumerate([.05,.25,.50,.75,.95]):
        cut=int(len(base)*frac);chunks.append(tok.decode(base[prev:cut]));key=f'NEEDLE_{n+1}';value=hashlib.sha256(f'needle:{a.seed}:{n}'.encode()).hexdigest()[:16];answers[key]=value
        chunks.append(f'\n// {key} = {value}\n');prev=cut
    chunks.append(tok.decode(base[prev:]));text='Find the five NEEDLE values in this repository snapshot. Reply as one JSON object mapping NEEDLE_1 through NEEDLE_5 to their exact values.\n'+''.join(chunks)
    encoded=tok.encode(text,add_special_tokens=False).ids
    while len(encoded)<a.tokens:
        text+='\n// capacity padding '+hashlib.sha256(str(len(encoded)).encode()).hexdigest()+'\n';encoded=tok.encode(text,add_special_tokens=False).ids
    text=tok.decode(encoded[:a.tokens]);count=len(tok.encode(text,add_special_tokens=False).ids)
    if count!=a.tokens or any(v not in text for v in answers.values()):raise SystemExit('tokenizer round-trip or needle preservation failed; do not guess count')
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    body={'model':a.model,'messages':[{'role':'user','content':text}],'temperature':1.,'top_p':.95,'top_k':20,'reasoning_effort':'medium','max_tokens':2048,'seed':a.seed}
    (out/'request.json').write_text(json.dumps(body,ensure_ascii=False)+'\n')
    (out/'private-oracle.json').write_text(json.dumps({'values':answers,'raw_content_tokens':count,'tokenizer_sha256':hashlib.sha256(Path(a.tokenizer).read_bytes()).hexdigest(),'note':'Not chat token count. Require server usage confirmation. Needle answer likely ends early; run separate sustained output request for speed.'},indent=2)+'\n')
    print(f'RAW_CONTENT={count}; final chat count must come from server. Capacity corpus only.')
if __name__=='__main__':main()
