"""Read-only .ninfer v2 inventory. Structural inspection is NOT loader compatibility."""
import json,os,struct,hashlib
from pathlib import Path

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(8<<20),b''): h.update(b)
    return h.hexdigest()

def inspect_artifact(path):
    path=Path(path); size=path.stat().st_size
    with path.open('rb') as f:
        pre=f.read(16)
        if len(pre)!=16 or pre[:8]!=b'NINFER\0\2': raise ValueError('not .ninfer v2')
        n=struct.unpack('<Q',pre[8:])[0]
        if not 1<=n<=64*(1<<20) or 16+n>size: raise ValueError('invalid directory size')
        def unique(pairs):
            d={}
            for k,v in pairs:
                if k in d: raise ValueError('duplicate JSON member')
                d[k]=v
            return d
        meta=json.loads(f.read(n),object_pairs_hook=unique)
    if set(meta)!={'identity','objects'} or not isinstance(meta['objects'],list) or not meta['objects']: raise ValueError('invalid root')
    start=(16+n+4095)//4096*4096; end=0; names=set(); totals={}; objects=[]
    for o in meta['objects']:
        name=o['name']; off=o['offset']; length=o['bytes']
        if not isinstance(name,str) or not name or name in names: raise ValueError('duplicate/empty name')
        if any(type(v) is not int or v<0 for v in [off,length]) or length==0: raise ValueError('invalid object range')
        if off<end or start+off+length>size: raise ValueError('overlap or object beyond file')
        if o['kind'] not in ['tensor','resource']: raise ValueError('unknown kind')
        names.add(name); end=off+length
        prefix=name.split('/')[0]; totals[prefix]=totals.get(prefix,0)+length
        objects.append({k:o[k] for k in ['name','kind','offset','bytes']}|({k:o[k] for k in ['shape','format','layout']} if o['kind']=='tensor' else {}))
    return dict(path=str(path),file_bytes=size,payload_offset=start,identity=meta['identity'],objects=objects,object_count=len(objects),component_bytes=totals,tensor_bytes=sum(o['bytes'] for o in objects if o['kind']=='tensor'),compatibility='NOT_ESTABLISHED')
