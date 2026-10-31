"""Read-only P00 identity collection. Run on the target host; never starts an engine."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess

LAB = Path(__file__).resolve().parents[2]

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def object_hash(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def source_changes(tree):
    return command(['git','diff','--name-only','HEAD'],tree).splitlines(), subprocess.check_output(['git','diff','--binary','HEAD'],cwd=tree)

def prepared_env(cfg_env):
    result={k:v for k,v in cfg_env.items() if k.startswith('STRATA_')}
    for key,value in {'STRATA_REPLY_REUSE':'1','STRATA_PRESERVE_THINKING':'0'}.items():
        if key in result and result[key]!=value:raise ValueError('SERVICE_EXPORT_CONFLICT: '+key)
        result.setdefault(key,value)
    return result

def read(path):return json.loads(Path(path).read_text())
def command(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()

def validate_identity(data,lock):
    """Validate measured identities, not runtime activation or GPU authorization."""
    b=lock['research_baseline']; source=data['source']
    checks={
        'source_head':source['head']==b['sha'],
        'six_file_port':source['port_files_match'] is True and len(source['dirty_files'])==6,
        'native_clean':source['native_clean'] is True and source['patch_match'] is True,
        'binary':data['binary']['sha256']==b['binary_sha256_reported'],
        'dependencies':data['dependencies']['mismatches']==[] and data['dependencies']['files']>0,
        'assets':data['assets']['mismatches']==[] and data['assets']['full_hash_verified'] is True and data['assets']['files']>0,
        'protection':data['protection']['count']==13 and data['protection']['changed']==[],
        'production_stopped':data['service']['ActiveState']=='inactive' and data['service']['SubState']=='dead',
        'env':all(data['config']['env'].get(k)==v for k,v in b['mandatory_env'].items()),
        'profile_absent':all(k not in data['config']['env'] for k in b['required_absent_env']),
        'forbidden_env_absent':not any(k in data['config']['env'] for k in ('STRATA_STAGE_PIN','STRATA_ROUTE_RESIDENT')),
        'build':all(data['build']['values'].get(k)==v for k,v in b['mandatory_build'].items()),
        'kv_resident':data['config']['kv_resident']==20480,
        'isolation_budget':data['config']['max_context']==131072 and data['config']['port']==18089 and data['config']['safety_tokens']==4096 and data['config']['request_overrides_present'] is False,
    }
    failed=[k for k,v in checks.items() if not v]
    if failed:raise ValueError('IDENTITY_REJECTED: '+','.join(failed))
    return {'status':'IDENTITY_LOCKED','checks':checks,'runtime_activation':'NOT_RUN','gpu_authorization':'NOT_GRANTED_BY_IDENTITY','deployment_approved':False}

def collect_identity(config_path:Path)->dict:
    """Collect P6 receipts and full file hashes; do not return secrets from config."""
    config_path=Path(config_path).resolve();task=config_path.parent;c=read(config_path)
    tree=Path(c['deployed_repo']);root=tree.parents[2]; build=read(task/'BUILD_COMPLETE.json');port=read(task/'reply-pt-port.json')
    protected=read(root/'workspace/combination/hc-perf-20261029/HAND_BACK.json')['protected']
    changed=[p for p,h in protected.items() if not Path(p).is_file() or digest(p)!=h]
    dirty,patch_bytes=source_changes(tree)
    files={name:digest(tree/name) for name in port['files']}
    tracked=command(['git','ls-files'],tree).splitlines()
    tracked_hashes={name:digest(tree/name) for name in tracked if (tree/name).is_file()}
    dependencies=read(task/'dependencies-sha256.json');dep_root=task/'dependencies/llama.cpp-3cf0325'
    dep_bad=[name for name,h in dependencies['files'].items() if not (dep_root/name).is_file() or digest(dep_root/name)!=h]
    assets=read(task/'assets.json');asset_rows=[];asset_bad=[]
    for record in assets['records']:
        p=Path(record['path']);before=p.stat();actual=digest(p);after=p.stat()
        match=(actual==record['sha256'] and before.st_size==record['bytes'] and (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns))
        if not match:asset_bad.append(str(p))
        asset_rows.append({'path':str(p),'bytes':after.st_size,'sha256':actual,'matches_original':match})
    cache={}
    for line in (tree/'build-lab/CMakeCache.txt').read_text().splitlines():
        if '=' in line and ':' in line.split('=',1)[0] and not line.startswith(('#','//')):
            k,v=line.split('=',1);cache[k.split(':',1)[0]]=v
    values={'STRATA_MMQ_KQUANTS':cache.get('STRATA_MMQ_KQUANTS'),'STRATA_Q6K_EXPERTS':cache.get('STRATA_Q6K_EXPERTS'),'CUDA_ARCHITECTURES':cache.get('CMAKE_CUDA_ARCHITECTURES'),'CMAKE_BUILD_TYPE':cache.get('CMAKE_BUILD_TYPE')}
    # Use the existing pure config constructor; no OwnedServer or command execution.
    import sys
    sys.path.insert(0,str(root));from lab.runner import make_run_config
    cfg=make_run_config(c,tree,'cfg',{},task/'p00-not-created')
    env=prepared_env(cfg['env'])
    def flag(name):
        args=cfg['args'];return args[args.index(name)+1] if name in args else None
    rawservice=command(['systemctl','show','openclaw-qwen38-next.service','--property=ActiveState,SubState,UnitFileState'])
    with socket.socket() as sock:
        sock.settimeout(1);listening=sock.connect_ex(('127.0.0.1',18089))==0
    return {'schema_version':1,'observed_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'P00 read-only full identity; no engine launch',
      'source':{'head':command(['git','rev-parse','HEAD'],tree),'dirty_files':dirty,'port_files':files,'port_files_match':files==port['files'],'native_clean':set(dirty)==set(port['files']),'patch_match':patch_bytes==(task/'reply-pt-v027.patch').read_bytes(),'tracked_files':len(tracked_hashes),'tracked_manifest_sha256':object_hash(tracked_hashes),'python_patch_manifest_sha256':digest(task/'reply-pt-port.json')},
      'binary':{'path':build['exe'],'sha256':digest(build['exe']),'build_receipt_sha256':digest(task/'BUILD_COMPLETE.json')},
      'dependencies':{'files':len(dependencies['files']),'manifest_sha256':digest(task/'dependencies-sha256.json'),'mismatches':dep_bad},
      'assets':{'files':len(asset_rows),'hashed_bytes':sum(r['bytes'] for r in asset_rows),'manifest_sha256':digest(task/'assets.json'),'full_hash_verified':True,'mismatches':asset_bad,'records':asset_rows},
      'build':{'values':values,'cmake_cache_sha256':digest(tree/'build-lab/CMakeCache.txt'),'original_flags':build['flags']},
      'config':{'source_path':str(config_path),'source_sha256':digest(config_path),'engine_config_sha256':digest(c['deployed_config']),'env':env,'expected_service_exports':{'STRATA_REPLY_REUSE':'1','STRATA_PRESERVE_THINKING':'0'},'env_scope':'prepared configuration, not actual PID; explicit conflicts rejected, missing reply/PT inherited per P6 runner; verify at P01','kv_resident':int(flag('--kv-resident')),'max_context':c['max_context'],'port':c['port'],'safety_tokens':c['safety_tokens'],'request_overrides_present':bool(c.get('request_overrides'))},
      'service':dict(line.split('=',1) for line in rawservice.splitlines()),'protection':{'count':len(protected),'changed':changed,'hashes':protected},
      'gpu':{'csv':command(['nvidia-smi','--query-gpu=name,memory.total,memory.used,driver_version,temperature.gpu','--format=csv,noheader,nounits']),'compute_processes_csv':command(['nvidia-smi','--query-compute-apps=pid,process_name','--format=csv,noheader,nounits'])},
      'port_18089_accepting_tcp':listening,'runtime':{'native_pid':None,'actual_env':None,'actual_argv':None,'actual_expert_slots':None,'reason':'P00 does not launch engine; historical 10272 slots must be rechecked at P01'},'production_state_changed':False,'deployment_approved':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',required=True,type=Path)
    a=parser.parse_args();print(json.dumps(collect_identity(a.config),ensure_ascii=False,indent=2))
