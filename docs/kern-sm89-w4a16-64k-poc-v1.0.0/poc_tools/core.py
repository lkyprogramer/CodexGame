"""CPU-only support tools. These do not implement a model or claim GPU validation."""
from __future__ import annotations
import codecs
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any, Iterable

GIB = 1 << 30
REQUIRED_GATES = ('environment','artifact','numeric','context64k','cache','java','lifecycle','performance')

def safe_relative(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('path must be nonempty and relative, with no ..')
    return p

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''): h.update(b)
    return h.hexdigest()

def memory_budget(weight_bytes: int, capacity: int, *, kv_bits: int = 16,
                  kv_meta_bytes_per_token: int = 0, slots: int = 4,
                  workspace_bytes: int = GIB, graph_bytes: int = 256 << 20,
                  headroom_bytes: int = GIB, total_bytes: int = 24 * GIB,
                  extra_bytes: int = 0) -> dict:
    values=(weight_bytes,capacity,kv_meta_bytes_per_token,slots,workspace_bytes,graph_bytes,headroom_bytes,total_bytes,extra_bytes)
    if any(type(x) is not int or x < 0 for x in values) or capacity < 1 or total_bytes < 1:
        raise ValueError('memory values must be nonnegative integers; capacity/total positive')
    if kv_bits not in (4,8,16): raise ValueError('only 4/8/16 bit planning is supported')
    # 16 full-attention layers, four KV heads, K+V, head dim 256.
    # Compression metadata is explicit: four-bit arithmetic alone is not an implementation.
    kv_bytes = capacity * (16 * 4 * 2 * 256 * kv_bits // 8 + kv_meta_bytes_per_token)
    # Conservative reference-provider stride; target must replace with the measured layout.
    slot_bytes=48 * 3211264
    parts={'weight_bytes':weight_bytes,'kv_bytes':kv_bytes,'state_bytes':slot_bytes*slots,
           'workspace_bytes':workspace_bytes,'graph_bytes':graph_bytes,'extra_bytes':extra_bytes}
    used=sum(parts.values())
    return {**parts,'capacity':capacity,'kv_bits':kv_bits,'slots':slots,'gdn_bytes_per_slot':slot_bytes,
            'total_bytes':total_bytes,'planned_bytes':used,'headroom_bytes':headroom_bytes,
            'spare_bytes':total_bytes-used,'fits':used+headroom_bytes <= total_bytes,
            'status':'ESTIMATE_NOT_GPU_MEASUREMENT'}

def _no_duplicates(pairs):
    out={}
    for key,value in pairs:
        if key in out: raise ValueError(f'duplicate JSON key: {key}')
        out[key]=value
    return out

DTYPE_BYTES={'BOOL':1,'U8':1,'I8':1,'I16':2,'U16':2,'I32':4,'U32':4,'I64':8,'U64':8,
             'F16':2,'BF16':2,'F32':4,'F64':8,'F8_E4M3':1,'F8_E5M2':1,'F8_E4M3FN':1}

def read_safetensors_header(path: Path, max_header: int = 64 << 20) -> dict:
    path=Path(path); size=path.stat().st_size
    with path.open('rb') as f:
        b=f.read(8)
        if len(b)!=8: raise ValueError('truncated length header')
        n=struct.unpack('<Q',b)[0]
        if n<2 or n>max_header or 8+n>size: raise ValueError('invalid or oversized header')
        d=json.loads(f.read(n),object_pairs_hook=_no_duplicates)
    out={}; intervals=[]
    for name,t in d.items():
        if name=='__metadata__':continue
        if not isinstance(t,dict):raise ValueError('tensor descriptor must be an object')
        dtype=t['dtype'];shape=t['shape'];start,end=t['data_offsets']
        if dtype not in DTYPE_BYTES: raise ValueError(f'unsupported dtype: {dtype}')
        if any(type(x) is not int or x<0 for x in shape): raise ValueError('invalid shape')
        if type(start) is not int or type(end) is not int or start<0 or end<start or end>size-8-n:
            raise ValueError('tensor data outside file')
        expected=math.prod(shape)*DTYPE_BYTES[dtype]
        if end-start != expected: raise ValueError('shape and stored bytes disagree')
        if end>start:intervals.append((start,end,name))
        out[name]={**t,'stored_bytes':end-start,'file':path.name}
    intervals.sort()
    if any(b[0]<a[1] for a,b in zip(intervals,intervals[1:])):raise ValueError('overlapping tensor data')
    return out

def audit_checkpoint(directory: Path) -> dict:
    directory=Path(directory); all_tensors={}; shards=[]
    for p in sorted(directory.glob('*.safetensors')):
        tensors=read_safetensors_header(p)
        for k,v in tensors.items():
            if k in all_tensors:raise ValueError(f'duplicate tensor across shards: {k}')
            all_tensors[k]=v
        shards.append({'name':p.name,'bytes':p.stat().st_size})
    if not shards:raise ValueError('no safetensors shards; model is not downloaded')
    groups={'text':0,'vision':0,'mtp':0,'other':0}
    for k,v in all_tensors.items():
        g='vision' if 'visual.' in k else 'mtp' if k.startswith('mtp.') or '.mtp.' in k else 'text' if 'language_model.' in k or k.startswith('lm_head.') else 'other'
        groups[g]+=v['stored_bytes'];v['group']=g
    cfg=json.loads((directory/'config.json').read_text())
    q=cfg.get('quantization_config',{})
    return {'status':'HEADER_AUDIT_ONLY','directory':str(directory),'shards':shards,
            'groups_bytes':groups,'tensors':all_tensors,'quantization_config':q,
            'text_config':cfg.get('text_config',cfg),
            'warning':'Marlin repack, runtime buffers, CUDA graph and KV are not included in checkpoint bytes.'}

def sse_events(chunks: Iterable[bytes]):
    decoder=codecs.getincrementaldecoder('utf-8')('strict'); buf=''; data=[]
    def event(lines):
        text='\n'.join(lines)
        if text=='[DONE]':return text
        return json.loads(text)
    for chunk in chunks:
        buf+=decoder.decode(chunk)
        while '\n' in buf:
            line,buf=buf.split('\n',1);line=line.removesuffix('\r')
            if line=='':
                if data:yield event(data);data=[]
            elif line.startswith('data:'):
                data.append(line[5:].removeprefix(' '))
    buf+=decoder.decode(b'',final=True)
    if buf or data:raise ValueError('truncated SSE frame at EOF')

def collect_stream(timed_events: Iterable[tuple[float,Any]], wall_s: float) -> dict:
    first=None;last=None;content=[];reasoning=[];usage=None;finish=None;done=False;error=None
    chunks=0;tool_calls=[]
    for t,e in timed_events:
        if e=='[DONE]':done=True;continue
        if not isinstance(e,dict):raise ValueError('SSE JSON event must be an object')
        if 'error' in e:error=e['error'];continue
        if isinstance(e.get('usage'),dict):usage=e['usage']
        for ch in e.get('choices',[]):
            delta=ch.get('delta',{})
            text=delta.get('content') or ch.get('text') or ''
            thought=delta.get('reasoning_content') or delta.get('reasoning') or ''
            tools=delta.get('tool_calls',[])
            emitted=bool(text or thought or any(x.get('function',{}).get('arguments') for x in tools))
            if emitted:
                if first is None:first=t
                last=t;chunks+=1
            if text:content.append(text)
            if thought:reasoning.append(thought)
            tool_calls.extend(tools)
            if ch.get('finish_reason') is not None:finish=ch['finish_reason']
    count=usage.get('completion_tokens') if usage else None
    prompt=usage.get('prompt_tokens') if usage else None
    estimated=count/(last-first) if isinstance(count,(int,float)) and first is not None and last is not None and last>first else None
    return {'status':'ERROR' if error else 'COMPLETE' if done else 'INCOMPLETE','error':error,
            'ttft_s':first,'wall_s':wall_s,'last_generated_s':last,'output_tokens':count,'prompt_tokens':prompt,
            'finish_reason':finish,'usage':usage,'content':''.join(content),'reasoning':''.join(reasoning),
            'tool_call_deltas':tool_calls,'generated_sse_events':chunks,
            'client_window_tps_estimate':estimated,'server_decode_tps':None,
            'rate_note':'SSE events are not tokens. Client-window rate is exploratory, never a performance gate.'}

def resolve_constants(m: dict) -> dict:
    const=m.get('constants',{})
    def walk(x,depth=0):
        if depth>32:raise ValueError('constant expansion cycle')
        if isinstance(x,str) and x in const:return walk(const[x],depth+1)
        if isinstance(x,list):return [walk(y,depth+1) for y in x]
        if isinstance(x,dict):return {k:walk(v,depth+1) for k,v in x.items() if k!='constants'}
        return x
    return walk(m)

def check_poc_manifest(m: dict) -> list[str]:
    """Conservative PoC lint, NOT a replacement for kern verify/ABI/SASS checks."""
    m=resolve_constants(m); errors=[]
    if m.get('schema_version')!=4:errors.append('schema_version must be 4')
    maxima={k:v.get('max',0) for k,v in m.get('vars',{}).items()}
    if maxima.get('tokens',0)>2048: errors.append('tokens.max above PoC workspace cap')
    def scalar(x):
        if type(x) is int:return x
        if isinstance(x,str) and x in maxima:return maxima[x]
        if isinstance(x,dict) and set(x)=={'mul'}:a,b=x['mul'];return scalar(a)*scalar(b)
        if isinstance(x,dict) and set(x)=={'ceil_div'}:
            a,b=x['ceil_div'];a=scalar(a);b=scalar(b)
            if b<=0:raise ValueError('bad divisor')
            return (a+b-1)//b
        raise ValueError('unknown expression')
    def walk(x,path):
        if isinstance(x,dict):
            if x.get('pdl'):errors.append(path+': PDL forbidden on SM89')
            if 'cluster' in x:errors.append(path+': cluster launch forbidden in this PoC')
            if 'tensormap' in x:errors.append(path+': TMA descriptor forbidden in this PoC')
            if 'shared_mem' in x:
                try:
                    if scalar(x['shared_mem'])>99*1024:errors.append(path+': dynamic shared memory exceeds SM89 limit')
                except (ValueError,TypeError,KeyError):errors.append(path+': unresolved shared-memory expression')
            for k,v in x.items():walk(v,path+'.'+k)
        elif isinstance(x,list):
            for i,v in enumerate(x):walk(v,f'{path}[{i}]')
    walk(m,'manifest')
    for name,module in m.get('modules',{}).items():
        if not re.fullmatch('[0-9a-f]{64}',module.get('sha256','')):errors.append(f'{name}: missing module hash')
        if re.search(r'sm[_-]?(?:100|103|120|121)',module.get('source','')):errors.append(f'{name}: Blackwell artifact label')
    return errors

def evaluate_evidence(data: dict, base: Path | None = None) -> dict:
    gates=data.get('gates',{}); missing=[]; failed=[]
    for k in REQUIRED_GATES:
        g=gates.get(k,{})
        if g.get('status')=='FAIL':failed.append(k)
        elif g.get('status')!='PASS':missing.append(k)
        else:
            refs=g.get('evidence',[])
            if not refs or base is None: missing.append(k+':evidence')
            else:
                for ref in refs:
                    try:
                        p=(base/safe_relative(ref['path'])).resolve()
                        p.relative_to(base.resolve())
                        if not p.is_file() or sha256_file(p)!=ref['sha256']:raise ValueError('bad evidence digest')
                    except (ValueError,KeyError,TypeError):missing.append(k+':evidence')
    if data.get('hardware_verified') is not True or data.get('device_cc')!='8.9':missing.append('actual_sm89_device')
    for k,pattern in [('model_sha256','[0-9a-f]{64}'),('kern_commit','[0-9a-f]{40}'),('profile_sha256','[0-9a-f]{64}')]:
        if not re.fullmatch(pattern,str(data.get(k,''))):missing.append(k)
    if not data.get('run_id'):missing.append('run_id')
    for key,expected in [('profile','p0-bf16-kv'),('speculation','none'),('activation_dtype','bf16'),('gdn_dtype','fp32'),('kv_dtype','bf16')]:
        if data.get(key)!=expected:missing.append(key+'_contract')
    samples=gates.get('performance',{}).get('samples',[])
    if gates.get('performance',{}).get('status')=='PASS':
        longs=[s for s in samples if 65536<=s.get('prompt_tokens',0)<73728]
        shorts=[s for s in samples if 4096<=s.get('prompt_tokens',0)<=8192]
        for group,name,floor in [(longs,'long',20),(shorts,'short',50)]:
            if len(group)<3:missing.append(name+'_perf_samples')
            for s in group:
                if type(s.get('output_tokens')) is not int or s.get('output_tokens',0)<2048 or s.get('count_basis')!='accepted_target_tokens' or s.get('speculation')!='none' or s.get('time_basis')!='engine_decode_wall':missing.append(name+'_perf_contract')
                elif not isinstance(s.get('decode_ms'),(int,float)) or not math.isfinite(s['decode_ms']) or s['decode_ms']<=0:missing.append(name+'_decode_ms')
                elif 1000*s['output_tokens']/s['decode_ms']<floor:failed.append(name+'_perf_floor')
    if gates.get('context64k',{}).get('status')=='PASS':
        g=gates['context64k']
        if g.get('actual_prompt_tokens')!=65536 or g.get('generated_tokens',0)<2048 or g.get('truncated') is not False:failed.append('context64k_contract')
        if type(g.get('minimum_free_bytes')) is not int:missing.append('context64k_headroom')
        elif g['minimum_free_bytes'] < (512<<20):failed.append('context64k_headroom')
    if gates.get('java',{}).get('status')=='PASS':
        if gates['java'].get('passed')!=3 or gates['java'].get('protected_files_unchanged') is not True:failed.append('java_contract')
    decision='NO_GO' if failed else 'BLOCKED' if missing else 'POC_GO'
    return {'decision':decision,'failed':sorted(set(failed)),'missing':sorted(set(missing)),
            'production_promoted':False,'scope':'64K no-spec PoC only; not 200K or production certification'}
