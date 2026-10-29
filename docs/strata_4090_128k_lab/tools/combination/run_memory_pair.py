"""Matched memory stages with explicit engine PIDs and all-thread child discovery."""
import argparse
import json
import os
from pathlib import Path
import time

import run_boundaries as boundary
from boundary_memory import MemorySampler, system_memory
from lab.assets import verify as verify_assets
from lab.core import dump, gpu_lock, hash_obj, load_config
from lab.tokenizer import StrataCounter


def owned_pids(server, proc_root=Path('/proc')):
    return boundary.descendants(server, proc_root)


def run(args):
    c=load_config(args.config);tree,out=Path(args.tree).resolve(),Path(args.out).resolve()
    combo=boundary.combo
    if int(c['port'])!=18089 or c['max_context']!=131072 or c['min_available_mib']<4096 or c.get('gpu_temp_abort_c',85)>85:
        raise ValueError('PROTECTION_MISMATCH')
    if Path(c['deployed_repo']).resolve()!=tree or c.get('request_overrides'):raise ValueError('CONFIG_MISMATCH')
    data=json.loads(Path(args.corpus).read_text())
    if hash_obj(data['cases'])!=data['corpus_sha256']:raise ValueError('CORPUS_IDENTITY_MISMATCH')
    indexed={x['id']:x for x in data['cases']}
    protected,build=combo.protected_hashes(c),combo.validate_tree(tree)
    prepared={a:combo.make_run_config(c,tree,a,combo.ready_spec(),out/a) for a in ('base','cfg')}
    combo.assert_same_except_kvres(prepared['base'],prepared['cfg'])
    plan={'mode':'MATCHED_MEMORY_PAIR','order':['base','cfg'],'source':build,
          'process_identity':'explicit GPU engine audit PIDs plus children from every service thread',
          'stages':['qualified idle10','68K/100K actual-history park/restore','prefill/decode cancel and continue',
                    '3 unique 100K cache-fill probes','idle30','unloaded15'],
          'scope':'memory attribution and peaks; no repeated sustained temperature phase; original failed attempts retained'}
    if not args.execute:return plan
    combo.assert_service_inactive();verify_assets(c)
    out.mkdir(parents=True,exist_ok=False);dump(out/'plan.json',plan)
    dump(out/'production-before.json',{'service':combo.assert_service_inactive(),'hashes':protected})
    os.environ.update(STRATA_PRESERVE_THINKING='0',STRATA_REPLY_REUSE='1')
    counter=StrataCounter(tree,c['gguf'],c['template']);results=[]
    with gpu_lock(c.get('gpu_lock_workspace',c['workspace'])):
        try:
            for arm in plan['order']:
                combo.assert_service_inactive();combo.assert_protected(c,protected)
                if combo.validate_tree(tree)!=build:raise RuntimeError('SOURCE_DRIFT')
                folder=out/arm;folder.mkdir();dump(folder/'cooldown.json',combo.wait_cool(c))
                dump(folder/'before-load.memory.json',system_memory())
                server=combo.OwnedServer(c,tree,arm,combo.ready_spec(),folder)
                a=None;error=None
                try:
                    with MemorySampler(folder,lambda:owned_pids(server)) as memory:
                        try:
                            server.__enter__();dump(folder/'activation.json',combo.validate_startup(server,arm))
                            sample=memory.checkpoint('loaded')
                            actual={x['pid'] for x in sample['processes'] if 'smaps_rollup' in x}
                            if not {int(x['pid']) for x in server.engine_audit}.issubset(actual):raise RuntimeError('ENGINE_MEMORY_NOT_OBSERVED')
                            a=boundary.Arm(c,server,counter,folder,memory)
                            probe={'model':'strata','messages':[{'role':'user','content':'Return only OK.'}],
                                   'max_tokens':32,'temperature':0,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
                            a.request('qualification',probe,'OK');time.sleep(10);memory.checkpoint('qualified-idle-10s')
                            a.lifecycle(indexed,'memory')
                            a.cancellations(indexed['park-prime-102400']['body'],'memory')
                            for cycle in range(3):
                                request=boundary.make_probe(indexed['park-prime-102400']['body'],'memory-cache-fill-'+str(cycle))
                                a.request('cache-fill-'+str(cycle),request,'BOUNDARY_OK')
                            memory.stage='idle-30s';time.sleep(30);memory.checkpoint('idle-30s')
                        finally:
                            server.__exit__(None,None,None);combo.wait_released(c);memory.checkpoint('unloaded')
                            time.sleep(15);memory.checkpoint('unloaded-15s')
                except BaseException as exception:
                    error=str(exception)
                    if not isinstance(exception,Exception):raise
                result={'arm':arm,'error':error,'abort_reason':server.abort_reason,'requests':a.rows if a else []}
                dump(folder/'result.json',result);results.append(result)
                if error and 'THERMAL_GUARD' not in error:raise RuntimeError(error)
        finally:
            dump(out/'production-after.json',{'service':combo.assert_service_inactive(),'hashes':combo.assert_protected(c,protected)})
            dump(out/'summary.json',{'arms':results,'deployment_approved':False})
    return {'state':'COMPLETE','arms':results,'deployment_approved':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','tree','corpus','out'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--execute',action='store_true')
    result=run(parser.parse_args());print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(int(any(x['error'] or any(not r['score']['pass'] for r in x['requests']) for x in result.get('arms',[]))))
