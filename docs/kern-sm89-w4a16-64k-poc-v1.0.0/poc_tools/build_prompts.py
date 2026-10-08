"""Build deterministic real-token workloads from a LOCAL tokenizer, never estimate by characters."""
import argparse, hashlib, json, random
from pathlib import Path

def build_tokens(encode, target, seed):
    if type(target) is not int or target<=0:raise ValueError('target must be positive')
    rng=random.Random(seed);ids=[];i=0
    # Different record ids, values and Java-like/log content avoid a repeated-one-token speed toy.
    while len(ids)<target+4096:
        row=(f'// File module_{i%53}/Service_{i}.java\n'
             f'final int timeout_{i} = {rng.randrange(100,60000)};\n'
             f'// Audit {rng.getrandbits(64):016x}: preserve milliseconds and generation order.\n'
             f'2026-09-08 INFO session={i} attempt={rng.randrange(1,8)} revision={rng.randrange(1000000)}\n')
        part=encode(row)
        if not part or not all(type(x) is int and x>=0 for x in part):raise ValueError('encoder must produce nonempty nonnegative token ids')
        ids.extend(part);i+=1
    return ids[:target]

def main():
    p=argparse.ArgumentParser();p.add_argument('--tokenizer',required=True);p.add_argument('--out-dir',required=True);p.add_argument('--model',default='qwen3.8-27b-kern-sm89-p0');p.add_argument('--lengths',default='4096,32768,65536');a=p.parse_args()
    try:from tokenizers import Tokenizer
    except ImportError:raise SystemExit('BLOCKED: install the pinned tokenizer dependency in the isolated tools environment')
    tok=Tokenizer.from_file(a.tokenizer);encode=lambda s:tok.encode(s,add_special_tokens=False).ids
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    manifest=[]
    for n in map(int,a.lengths.split(',')):
        if n<1024 or n>65536:raise ValueError('PoC performance length must be in [1024,65536]')
        for seed in (17,31,47):
            ids=build_tokens(encode,n,seed)
            instruction=encode('\nContinue with a detailed Java design review and many concrete code examples.\n')
            if len(instruction)>=n:raise ValueError('instruction is longer than requested prompt')
            ids[-len(instruction):]=instruction
            payload={'model':a.model,'prompt':ids,'max_tokens':2048,'temperature':0.0,'ignore_eos':True}
            name=f'perf-{n}-{seed}.json';(out/name).write_text(json.dumps(payload))
            manifest.append({'path':name,'kind':'PERFORMANCE_ONLY_IGNORE_EOS','input_tokens':len(ids),'seed':seed})
    # Retrieval uses meaningful insertions and does NOT ignore EOS.
    n=65536;ids=build_tokens(encode,n,59);facts={}
    for pct,name in [(10,'alpha'),(50,'beta'),(90,'gamma')]:
        value=f'V{random.Random(pct+59).getrandbits(48):012x}';facts[name]=value
        ins=encode(f'\nAUDIT_FACT {name}={value}; this value is authoritative.\n')
        at=n*pct//100;ids[at:at+len(ins)]=ins
    q=encode('\nReturn only JSON containing the three AUDIT_FACT values for alpha, beta, gamma.\n');ids[-len(q):]=q
    (out/'retrieval-65536.json').write_text(json.dumps({'model':a.model,'prompt':ids,'max_tokens':128,'temperature':0.0}))
    (out/'retrieval-answers.json').write_text(json.dumps(facts))
    manifest.append({'path':'retrieval-65536.json','kind':'RETRIEVAL','input_tokens':65536})
    (out/'manifest.json').write_text(json.dumps({'tokenizer_sha256':hashlib.sha256(Path(a.tokenizer).read_bytes()).hexdigest(),'cases':manifest},indent=2))
    print(f'Generated {len(manifest)} cases. Token counts are exact input id counts; server usage must independently agree.')
if __name__=='__main__':main()
