from __future__ import annotations
import json,re
from pathlib import Path
from .core import dump,flag_value,sha256


def collect(c):
    paths={Path(c['gguf']).resolve(),Path(c['template']).resolve()}
    g=Path(c['gguf']);m=re.match(r'(.*-)(\d{5})-of-(\d{5})(\.gguf)$',g.name)
    if m:
        for i in range(1,int(m[3])+1):paths.add(g.with_name(f'{m[1]}{i:05d}-of-{m[3]}{m[4]}').resolve())
    cfg=json.loads(Path(c['deployed_config']).read_text(encoding='utf-8-sig'));root=Path(c['deployed_repo'])
    for flag in ('--pack','--native','--ple-gguf','--expert-profile','--mtp','--control-vector'):
        value=flag_value(cfg.get('user_args',[]),flag) or flag_value(cfg.get('args',[]),flag)
        if value:
            p=Path(value).expanduser();p=p if p.is_absolute() else root/p
            if p.is_dir():paths.update(x.resolve() for x in p.rglob('*') if x.is_file())
            else:paths.add(p.resolve())
    for key in ('pack','native','expert_profile','mtp_path'):
        if isinstance(cfg.get(key),str) and cfg[key]:
            p=Path(cfg[key]);p=p if p.is_absolute() else root/p
            paths.update(x.resolve() for x in p.rglob('*') if x.is_file()) if p.is_dir() else paths.add(p.resolve())
    for x in c.get('asset_files',[]):paths.add(Path(x).expanduser().resolve())
    if len(paths)>5000:raise RuntimeError('Asset scan is too broad; check the pack path')
    return sorted(paths)


def snapshot(c):
    records=[];seen={}
    for p in collect(c):
        st=p.stat();key=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
        digest=seen.get(key) or sha256(p);seen[key]=digest
        after=p.stat()
        if (st.st_size,st.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise RuntimeError(f'Asset changed during hashing: {p}')
        records.append({'path':str(p),'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'sha256':digest})
    out={'scope':'Known GGUF shards, template and model/pack/profile/MTP paths in the deployed config; add custom resources to asset_files',
         'records':records,'deployed_config_sha256':sha256(Path(c['deployed_config']))}
    dump(Path(c['workspace'])/'assets.json',out);return {'assets':len(records),'hashed_bytes':sum(x['bytes'] for x in records)}


def verify(c):
    p=Path(c['workspace'])/'assets.json'
    if not p.exists():raise RuntimeError('ASSETS_NOT_FROZEN: run assets before GPU tests')
    data=json.loads(p.read_text())
    if data['deployed_config_sha256']!=sha256(Path(c['deployed_config'])):raise RuntimeError('Production config changed since assets snapshot; inspect and re-freeze explicitly')
    for x in data['records']:
        s=Path(x['path']).stat()
        if s.st_size!=x['bytes'] or s.st_mtime_ns!=x['mtime_ns']:raise RuntimeError('Asset changed after snapshot: '+x['path'])
    current={str(x) for x in collect(c)}
    if current!={x['path'] for x in data['records']}:raise RuntimeError('Asset set changed')
    return data
