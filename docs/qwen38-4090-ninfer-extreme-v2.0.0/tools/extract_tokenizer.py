"""Extract only the embedded tokenizer JSON; never exports executable code."""
import argparse,hashlib
from pathlib import Path
from .artifact import inspect_artifact
p=argparse.ArgumentParser();p.add_argument('artifact');p.add_argument('--out',required=True);a=p.parse_args()
d=inspect_artifact(a.artifact);o=[x for x in d['objects'] if x['name']=='frontend/tokenizer.json' and x['kind']=='resource']
if len(o)!=1:raise SystemExit('exact tokenizer resource missing')
x=o[0]
if x['bytes']>64*(1<<20):raise SystemExit('unexpected tokenizer size')
dest=Path(a.out)
if dest.exists():raise SystemExit('refusing overwrite')
with open(a.artifact,'rb') as f:f.seek(d['payload_offset']+x['offset']);data=f.read(x['bytes'])
if len(data)!=x['bytes']:raise SystemExit('truncated resource')
dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
print('tokenizer_bytes=',len(data),'sha256=',hashlib.sha256(data).hexdigest())
