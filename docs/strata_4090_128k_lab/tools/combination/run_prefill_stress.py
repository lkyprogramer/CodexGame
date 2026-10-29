"""Short-output, full cold-prefill supplement; no active cooling inside either arm."""
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
from run_memory_pair import owned_pids


class StageOnlyMemory:
    """Keep periodic sampling; avoid full-smaps pauses between stress requests."""
    def __init__(self,sampler):self.sampler=sampler
    @property
    def stage(self):return self.sampler.stage
    @stage.setter
    def stage(self,value):self.sampler.stage=value
    def checkpoint(self,name):self.sampler.stage=name


def run(args):
    c=load_config(args.config)
    tree,out=Path(args.tree).resolve(),Path(args.out).resolve()
    if int(c['port'])!=18089 or c['max_context']!=131072 or c['min_available_mib']<4096 or c.get('gpu_temp_abort_c',85)>85:
        raise ValueError('PROTECTION_MISMATCH')
    if Path(c['deployed_repo']).resolve()!=tree or c.get('request_overrides'):
        raise ValueError('Use the frozen combination tree without request overrides')
    data=json.loads(Path(args.corpus).read_text())
    if hash_obj(data['cases'])!=data['corpus_sha256']:raise ValueError('CORPUS_IDENTITY_MISMATCH')
    source=next(x['body'] for x in data['cases'] if x['id']=='park-prime-102400')
    combo=boundary.combo
    protected,build=combo.protected_hashes(c),combo.validate_tree(tree)
    prepared={arm:combo.make_run_config(c,tree,arm,combo.ready_spec(),out/arm) for arm in ('base','cfg')}
    combo.assert_same_except_kvres(prepared['base'],prepared['cfg'])
    order=['base','cfg'] if args.arm=='both' else [args.arm]
    plan={'mode':'PURE_PREFILL_STRESS','order':order,'duration_s':600,'output_cap':8,
          'target_input':102400,'new_system_prefix_each_request':True,'mid_arm_cooling':False,
          'source':build,'protection':'85C and 4096MiB unchanged; thermal stop arm, cool then other arm; no retry',
          'memory':'1s periodic sampling; full smaps at loaded/end checkpoints, not between stress requests',
          'purpose':'Prefill duty-cycle boundary, separate from 2048-output mixed workload; no performance claim'}
    if not args.execute:return plan
    combo.assert_service_inactive();verify_assets(c)
    out.mkdir(parents=True,exist_ok=False);dump(out/'plan.json',plan)
    dump(out/'production-before.json',{'service':combo.assert_service_inactive(),'hashes':protected})
    os.environ.update(STRATA_PRESERVE_THINKING='0',STRATA_REPLY_REUSE='1')
    counter=StrataCounter(tree,c['gguf'],c['template'])
    results=[]
    with gpu_lock(c.get('gpu_lock_workspace',c['workspace'])):
        try:
            for arm in plan['order']:
                combo.assert_protected(c,protected);combo.assert_service_inactive()
                if combo.validate_tree(tree)!=build:raise RuntimeError('SOURCE_DRIFT')
                folder=out/arm;folder.mkdir();dump(folder/'cooldown.json',combo.wait_cool(c))
                dump(folder/'before-load.memory.json',system_memory())
                server=combo.OwnedServer(c,tree,arm,combo.ready_spec(),folder)
                error=None;a=None;started=None;elapsed=0
                try:
                    with MemorySampler(folder,lambda:owned_pids(server)) as memory:
                        try:
                            server.__enter__();dump(folder/'activation.json',combo.validate_startup(server,arm))
                            prefix=c['extra_frozen_env']['STRATA_BOUNDARY_PIN_TRACE']
                            if not all(Path(prefix+'.'+str(x['pid'])+'.jsonl').exists() for x in server.engine_audit):raise RuntimeError('PIN_TRACE_NOT_ACTIVE')
                            a=boundary.Arm(c,server,counter,folder,StageOnlyMemory(memory))
                            probe={'model':'strata','messages':[{'role':'user','content':'Return only OK.'}],
                                   'max_tokens':32,'temperature':0,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
                            a.request('qualification',probe,'OK');memory.checkpoint('qualified')
                            started=time.monotonic();cycle=0
                            while time.monotonic()-started<600:
                                request=boundary.make_probe(source,'pure-prefill-'+str(cycle))
                                request['max_tokens']=8
                                response=a.request('pure-prefill-'+str(cycle).zfill(3),request,'BOUNDARY_OK')
                                # A reused prefix would lower the load this supplement is intended to test.
                                if a.rows[-1]['metrics']['reused_tokens']!=0:raise RuntimeError('PREFILL_NOT_COLD')
                                cycle+=1
                            elapsed=time.monotonic()-started;memory.checkpoint('stress-complete')
                        finally:
                            if started and not elapsed:elapsed=time.monotonic()-started
                            server.__exit__(None,None,None);combo.wait_released(c);memory.checkpoint('unloaded')
                            time.sleep(15);memory.checkpoint('unloaded-15s')
                except BaseException as exception:
                    error=str(exception)
                    if not isinstance(exception,Exception):raise
                result={'arm':arm,'error':error,'abort_reason':server.abort_reason,'stress_elapsed_s':elapsed,'requests':a.rows if a else []}
                dump(folder/'result.json',result);results.append(result)
                if error and 'THERMAL_GUARD' not in error:raise RuntimeError(error)
        finally:
            dump(out/'production-after.json',{'service':combo.assert_service_inactive(),'hashes':combo.assert_protected(c,protected)})
            dump(out/'summary.json',{'arms':results,'deployment_approved':False})
    return {'state':'COMPLETE','arms':results,'deployment_approved':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('config','tree','corpus','out'):parser.add_argument('--'+key,required=True)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--arm',choices=['base','cfg','both'],default='both')
    result=run(parser.parse_args());print(json.dumps(result,indent=2),flush=True)
    raise SystemExit(int(any(x['error'] or any(not row['score']['pass'] for row in x['requests']) for x in result.get('arms',[]))))
