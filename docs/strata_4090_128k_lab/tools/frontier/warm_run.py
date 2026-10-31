"""P01 live adapter: one P6 engine, at most three real-history requests, no retry.

Run only with --execute on the authorized Linux host. Native source is unchanged.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'tools/combination'),str(ROOT/'tools/v027')]
from lab import http
from lab.assets import verify as verify_assets
from lab.core import check_budget,dump,gpu_inventory,gpu_lock,hash_obj,load_config,sha256
from lab.runner import OwnedServer,make_run_config,wait_released
from lab.tokenizer import StrataCounter
import run_combo as combo
import run_boundaries as boundary
import run_restore as restore
import run_baseline as baseline
from boundary_memory import MemorySampler
from tools.frontier.warm_plan import validate_warm_plan
from tools.frontier.identity import source_changes,prepared_env
from tools.frontier.critical_path import summarize_windows


def load(path):return json.loads(Path(path).read_text())
def utc():return datetime.now(timezone.utc).isoformat()

class WorkDeadline(BaseException):
    pass

class Budget:
    def __init__(self,seconds=3600,reserve=120,clock=time.monotonic):
        if seconds!=3600 or reserve!=120:raise ValueError('FROZEN_TOTAL_BUDGET')
        self.clock=clock;self.started=clock();self.end=self.started+seconds;self.reserve=reserve
        self.engine_starts=0;self.requests=0
    def remaining_work(self):return self.end-self.reserve-self.clock()
    def start_engine(self):
        if self.engine_starts or self.remaining_work()<=0:raise RuntimeError('ENGINE_OR_WALL_BUDGET')
        self.engine_starts+=1
    def before_request(self,deadline):
        if type(deadline) is not int or not 0<deadline<=600:raise ValueError('REQUEST_DEADLINE')
        if self.requests>=3 or self.remaining_work()<deadline:raise RuntimeError('REQUEST_OR_WALL_BUDGET')
        self.requests+=1
    def begin_cleanup(self):
        self.cleanup_end=min(self.end,self.clock()+self.reserve)
        return self.cleanup_end
    def cleanup_remaining(self):
        return max(.1,self.cleanup_end-self.clock())
    def checkpoint(self):
        if self.remaining_work()<=0:raise RuntimeError('WORK_DEADLINE_REACHED')


def request_outcome(response,count,c,index):
    if response.get('error') or response.get('done') is not True:raise RuntimeError('INCOMPLETE_RESPONSE')
    if response.get('tools'):raise RuntimeError('UNAUTHORIZED_TOOL_OUTPUT')
    boundary.audit_usage({'max_tokens':2048},response,count,c)
    m=http.measurements(response)
    if m['generated_tokens']!=2048:return 'INSUFFICIENT_SHORT_OUTPUT'
    if type(m['read_tokens']) is not int or type(m['reused_tokens']) is not int:raise RuntimeError('MISSING_READ_REUSE')
    if m['read_tokens']+m['reused_tokens']!=m['prompt_tokens']:raise RuntimeError('READ_REUSE_ACCOUNTING')
    if index==0 and m['reused_tokens']!=0:raise RuntimeError('PRIME_NOT_COLD')
    if index and m['reused_tokens']<=0:return 'INSUFFICIENT_NO_WARM_REUSE'
    return 'REQUEST_COMPLETE'


def append_request(previous,response,recipe):
    if response.get('tools'):raise RuntimeError('TOOL_HISTORY_UNSUPPORTED')
    if hash_obj(recipe['append_user_message'])!=recipe['append_user_message_sha256']:raise RuntimeError('FOLLOWUP_DRIFT')
    if recipe['padding_allowed'] is not False:raise RuntimeError('PADDING_FORBIDDEN')
    result=copy.deepcopy(previous)
    result['messages']=restore.actual_history(previous,response)+[copy.deepcopy(recipe['append_user_message'])]
    return result


def rendered(counter,body):
    f=counter.frontend;m,t,kw=f.openai_to_messages(copy.deepcopy(body))
    if body.get('tool_choice')=='none':t=None
    m,t,changed=f.mark_think_literals(m,t,counter.tags)
    text=counter.template.render(m,tools=t,**kw)
    text,plain=f.unmark_think_literals(text,counter.tags) if changed else (text,())
    ids=counter.tokenizer.encode(text,parse_special=True,plain=plain)
    return len(ids),hash_obj(ids)


def activation(server,identity,lock):
    receipt=baseline.activation_receipt(server)
    if receipt['expert_cache_slots']!=lock['research_baseline']['reported_expert_slots']:raise RuntimeError('ACTUAL_SLOT_DRIFT')
    pid=server.engine_audit[0]['pid']
    env=dict(x.decode().split('=',1) for x in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if x.startswith(b'STRATA_'))
    expected=identity['config']['env']
    if env!=expected:raise RuntimeError('ACTUAL_ENV_DRIFT')
    if any(k in env for k in ('STRATA_VERIFY_PROFILE','STRATA_STAGE_PIN','STRATA_ROUTE_RESIDENT')):raise RuntimeError('FORBIDDEN_ACTUAL_ENV')
    receipt.update(native_pid=pid,native_identity=server.engine_audit[0],actual_strata_env=env,
                   binary_sha256=sha256(server.cfg['exe']),clock_domain='host CLOCK_MONOTONIC/perf_counter; native aggregate log has no window clock')
    return receipt


def assert_control_config(path,identity):
    if sha256(Path(path))!=identity['config']['source_sha256']:raise RuntimeError('P00_CONTROL_CONFIG_DRIFT')

def preflight(config,identity,plan,inputs,policy):
    assert_control_config(plan['runtime_config_path'],identity)
    if config['port']!=18089 or config['max_context']!=131072 or config['safety_tokens']!=4096:raise RuntimeError('ISOLATION_DRIFT')
    if config['min_available_mib']<4096 or config['gpu_temp_abort_c']>85:raise RuntimeError('RESOURCE_GUARD_WEAKENED')
    tree=Path(config['deployed_repo']);task=Path(config['workspace'])
    build=load(task/'BUILD_COMPLETE.json')
    import subprocess
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()!=identity['source']['head'] or build['source_sha']!=identity['source']['head']:raise RuntimeError('SOURCE_HEAD_DRIFT')
    if any(sha256(tree/name)!=digest for name,digest in identity['source']['port_files'].items()):raise RuntimeError('PORT_DRIFT')
    dirty,patch=source_changes(tree)
    if set(dirty)!=set(identity['source']['port_files']) or patch!=(task/'reply-pt-v027.patch').read_bytes():raise RuntimeError('HEAD_SOURCE_DRIFT')
    if sha256(tree/'build-lab/strata')!=identity['binary']['sha256']:raise RuntimeError('P00_BINARY_DRIFT')
    verify_assets(config)  # original full-content SHA was reverified at P00; this is metadata+set reuse.
    if sha256(task/'assets.json')!=identity['assets']['manifest_sha256']:raise RuntimeError('ASSET_MANIFEST_DRIFT')
    for field in ('execution_instruction_reference','baseline_identity_path','gpu_handoff_reference'):
        ref=plan[field]
        if sha256(inputs/ref)!=plan['reference_evidence'][ref]['sha256']:raise RuntimeError('REFERENCE_HASH_DRIFT')
    validate_warm_plan(plan,policy)
    if plan['planning_only'] is not False:raise RuntimeError('EXECUTION_SCOPE_NOT_BOUND')
    for req in plan['matrix'][0]['requests']:
        if hash_obj(load(inputs/req['input_reference']))!=req['body_or_recipe_sha256']:raise RuntimeError('INPUT_DRIFT')
    return tree


def run_diagnostic(plan_path,identity_path,output_dir,*,adapter=None):
    plan_path=Path(plan_path).resolve();inputs=plan_path.parent;out=Path(output_dir).resolve()
    if out.exists():raise RuntimeError('RUN_ALREADY_EXISTS_NO_REPLAY')
    out.mkdir(parents=True);budget=Budget();rows=[];reason=None;server=None;protected=None
    c=load_config(Path(load(plan_path)['runtime_config_path']));plan=load(plan_path);identity=load(identity_path)
    policy=load(ROOT/'frontier/config/policy.json');lock=load(ROOT/'frontier/sources/LOCK.json')
    def expired(*_):raise WorkDeadline('WORK_DEADLINE_REACHED')
    old_handler=signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,budget.remaining_work())
    dump(out/'START.json',{'started_at_utc':utc(),'pid':os.getpid(),'wall_budget_s':3600,'cleanup_reserve_s':120,'engine_limit':1,'request_limit':3})
    try:
        if adapter is not None:adapter.preflight(c,identity,plan,inputs,policy)
        with gpu_lock(c['gpu_lock_workspace']):
            dump(out/'LEASE.json',{'acquired_at_utc':utc(),'pid':os.getpid(),'workspace':c['gpu_lock_workspace'],'exclusive':True,'expires_with_context_exit':True})
            protected=combo.protected_hashes(c)
            if protected!=identity['protection']['hashes']:raise RuntimeError('P00_PROTECTION_DRIFT')
            dump(out/'PROTECTION_BEFORE.json',{'service':combo.assert_service_inactive(),'protected':protected,'gpu':gpu_inventory(c['gpu'])})
            tree=(preflight if adapter is None else adapter.preflight)(c,identity,plan,inputs,policy)
            budget.checkpoint();dump(out/'COOLDOWN.json',combo.wait_cool(dict(c,cooldown_timeout_s=min(300,budget.remaining_work()))))
            c=dict(c,extra_frozen_env=prepared_env(c.get('extra_frozen_env',{})))
            if adapter is not None:c=adapter.configure(c,identity,out)
            counter=StrataCounter(tree,c['gguf'],c['template'])
            c=dict(c,maintenance_confirmed=True,startup_timeout_s=min(300,int(budget.remaining_work()-15)))
            # One OwnedServer only. No qualification probes, retries, or generic campaigns.
            server=OwnedServer(c,tree,'cfg',{},out/'engine');entered=False
            try:
                budget.start_engine();server.__enter__();entered=True
                live=(activation if adapter is None else adapter.activation)(server,identity,lock);dump(out/'ACTIVATION.json',live)
                with MemorySampler(out/'engine',lambda:boundary.descendants(server),interval=1.0) as memory:
                    body=None;response=None
                    for index,request_plan in enumerate(plan['matrix'][0]['requests']):
                        budget.checkpoint();name=request_plan['request_label'];item=load(inputs/request_plan['input_reference'])
                        body=item if index==0 else append_request(body,response,item)
                        if body.get('max_tokens')!=2048 or body.get('tool_choice')!='none':raise RuntimeError('REQUEST_POLICY_DRIFT')
                        count,ids_hash=rendered(counter,body)
                        check_budget(count,2048,131072,4096)
                        if count>request_plan['prompt_tokens_upper_bound']:raise RuntimeError('PLANNED_INPUT_BOUND_EXCEEDED')
                        if index==0 and (count!=request_plan['expected_prompt_tokens_cpu'] or ids_hash!=request_plan['expected_rendered_token_ids_sha256_cpu']):raise RuntimeError('PRIME_RENDER_DRIFT')
                        prefix=out/name;dump(Path(str(prefix)+'.request.json'),body)
                        memory.checkpoint(name+'-before');offset=(out/'engine/engine.log').stat().st_size
                        budget.before_request(request_plan['request_deadline_seconds'])
                        pending={'request_id':name,'engine_id':'D1','execution_status':'STARTED','request_body_sha256':hash_obj(body),'local_prompt_tokens':count}
                        with (out/'ATTEMPTS.jsonl').open('a') as dest:dest.write(json.dumps(pending)+'\n')
                        start=time.monotonic();response=boundary.exchange(server,body,prefix,timeout=request_plan['request_deadline_seconds']);end=time.monotonic()
                        dump(Path(str(prefix)+'.response.json'),response)
                        if response.get('error'):reason=reason or ('RESPONSE_ERROR: '+str(response['error']))
                        if response.get('done') is True and not response.get('error'):
                            try:boundary.wait_idle(server,out,name,timeout=min(30,max(1,budget.remaining_work())))
                            except Exception as error:
                                dump(out/(name+'.idle-error.json'),{'response_error':response.get('error'),'idle_error':str(error)})
                                reason=reason or ('IDLE_ERROR: '+str(error))
                        memory.checkpoint(name+'-after')
                        with (out/'engine/engine.log').open('rb') as stream:stream.seek(offset);delta=stream.read().decode(errors='replace')
                        Path(str(prefix)+'.engine.log').write_text(delta)
                        m=http.measurements(response)
                        row={'campaign_id':plan['campaign_id'],'engine_id':'D1','request_id':name,'phase':'frontier/P01' if adapter is None else adapter.phase,'prime_or_append':name,'planned_order':index,'start_monotonic_ns':int(start*1e9),'end_monotonic_ns':int(end*1e9),'clock_domain':'host CLOCK_MONOTONIC','request_body_sha256':hash_obj(body),'rendered_token_ids_sha256':ids_hash,'rendered_history_sha256':hash_obj(body['messages']),'local_prompt_tokens':count,**m,'completion_tokens':m['generated_tokens'],'metrics':m,'execution_status':'COMPLETED','failure_kind':None,'generated_token_ids':None,'generated_token_ids_reason':'SSE does not expose original sampled token IDs; decoded text is retained, not mislabelled as native IDs','actual_response_text_sha256':hash_obj({'text':response.get('text'),'reasoning':response.get('reasoning')}),'response_error':response.get('error')}
                        try:outcome=(request_outcome if adapter is None else adapter.request_outcome)(response,count,c,index)
                        except Exception as e:outcome='FAILED';row.update(execution_status='FAILED',failure_kind=str(e))
                        row['request_acceptance']=outcome;rows.append(row)
                        with (out/'REQUESTS.jsonl').open('a') as dest:dest.write(json.dumps(row)+'\n')
                        print(json.dumps({'request_id':name,'prompt_tokens':m['prompt_tokens'],'read_tokens':m['read_tokens'],'reused_tokens':m['reused_tokens'],'completion_tokens':m['generated_tokens'],'ttft_s':m['ttft_s'],'wall_s':m['wall_s'],'status':outcome}),flush=True)
                        if outcome!='REQUEST_COMPLETE':reason=reason or outcome;break
                        if reason is not None:break
                        if server.abort_reason:raise RuntimeError('SERVER_GUARD: '+server.abort_reason)
            finally:
                # __enter__ already performs teardown on startup exceptions. Never restart it.
                active_error=sys.exc_info()[1]
                if active_error is not None:reason=reason or f'{type(active_error).__name__}: {active_error}'
                budget.begin_cleanup()
                signal.setitimer(signal.ITIMER_REAL,budget.cleanup_remaining())
                try:
                    if entered:server.__exit__(None,None,None)
                    elif server.process is not None and server.process.poll() is None:server.__exit__(None,None,None)
                    wait_released(c,timeout_s=budget.cleanup_remaining())
                except BaseException as error:
                    dump(out/'CLEANUP_ERROR.json',{'original_reason':reason,'cleanup_error':str(error)})
                    reason=reason or ('CLEANUP_ERROR: '+str(error))
                    raise
                finally:
                    private=out/'engine/runtime.private.json'
                    if private.exists():
                        red=load(private);red['api_key']='<ephemeral key removed>';dump(private,red)
            signal.setitimer(signal.ITIMER_REAL,max(.1,budget.end-time.monotonic()))
            verify_assets(c)
            if protected!=combo.protected_hashes(c):raise RuntimeError('FINAL_PROTECTION_DRIFT')
            dump(out/'HAND_BACK.json',{'observed_at_utc':utc(),'service':combo.assert_service_inactive(),'protected':combo.protected_hashes(c),'protected_unchanged':True,'gpu':gpu_inventory(c['gpu']),'port_18089_free':True,'observed_while_lock_held':True})
    except BaseException as e:
        reason=reason or f'{type(e).__name__}: {e}'
        dump(out/'FAILURE.json',{'reason':reason,'requests_consumed':budget.requests,'engines_consumed':budget.engine_starts,'no_replacement':True})
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
        attempts=[json.loads(x) for x in (out/'ATTEMPTS.jsonl').read_text().splitlines()] if (out/'ATTEMPTS.jsonl').exists() else []
        for attempt in attempts:
            if attempt['request_id'] not in {x['request_id'] for x in rows}:rows.append(dict(attempt,execution_status='FAILED',failure_kind=reason or 'NO_COMPLETE_RESPONSE_RECORD'))
        missing=[r['request_label'] for r in plan['matrix'][0]['requests'] if r['request_label'] not in {x['request_id'] for x in rows}]
        with (out/'REQUESTS.jsonl').open('w') as dest:
            for row in rows:dest.write(json.dumps(row)+'\n')
            for name in missing:dest.write(json.dumps({'request_id':name,'engine_id':'D1','execution_status':'NOT_RUN','failure_kind':'prior stop or budget','prompt_tokens':None,'completion_tokens':None})+'\n')
        dump(out/'COMPLETION.json',{'status':'COMPLETE' if reason is None else 'STOPPED','reason':reason,'engine_starts':budget.engine_starts,'work_requests_sent':budget.requests,'recorded_requests':len(rows),'not_run':missing,'wall_s':time.monotonic()-budget.started,'wall_budget_exceeded':time.monotonic()>budget.end,'request_count_scope':'HTTP attempts including failures','no_retry_or_replacement':True,'production_changed':False,'original_six':'FAIL_UNCHANGED','p05':'BLOCKED_EVIDENCE'})
        try:
            if time.monotonic()>=budget.end:raise RuntimeError('NO_AUDIT_TIME_REMAINING')
            signal.signal(signal.SIGALRM,expired);signal.setitimer(signal.ITIMER_REAL,max(.1,budget.end-time.monotonic()))
            verify_assets(c)
            hand={'observed_at_utc':utc(),'service':combo.assert_service_inactive(),'protected':combo.protected_hashes(c),'protected_unchanged':protected is not None and combo.protected_hashes(c)==protected,'gpu':gpu_inventory(c['gpu']),'scope':'all owned startup/request processes have exited; no production start'}
            if not (out/'HAND_BACK.json').exists():dump(out/'HAND_BACK.json',hand)
        except BaseException as e:dump(out/'HAND_BACK_ERROR.json',{'error':str(e)})
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
        trace=[out/'REQUESTS.jsonl'] if (out/'REQUESTS.jsonl').exists() else []
        trace += list(out.glob('*.engine.log'))
        if adapter is None:
            analysis=summarize_windows(trace,{'engine_id':'D1'})
            qualification={'status':'INSUFFICIENT','reason':reason or 'Existing aggregate logs lack closed per-window CPU/GPU dependencies and original sampled token IDs','new_candidate_qualified':False,'causal_speedup_claim':False,'performance':'NOT_EVALUATED','quality':'NOT_EVALUATED'}
        else:
            result=adapter.finalize(out,identity,rows,reason)
            analysis=result['ANALYSIS'];qualification=result['QUALIFICATION']
            analysis.update(DEPENDENCIES=result['DEPENDENCIES'],WINDOWS=result['WINDOWS'])
        dump(out/'ANALYSIS.json',analysis)
        dump(out/'DEPENDENCIES.json',analysis.get('DEPENDENCIES',{'status':'UNKNOWN','reason':'No native dependency trace'}))
        (out/'WINDOWS.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in analysis.get('WINDOWS',[])))
        dump(out/'QUALIFICATION.json',qualification)
        completed=load(out/'COMPLETION.json');completed.update(wall_s=time.monotonic()-budget.started,wall_budget_exceeded=time.monotonic()>budget.end)
        if (out/'HAND_BACK_ERROR.json').exists():completed.update(status='BLOCKED_RESOURCE',hand_back_error=load(out/'HAND_BACK_ERROR.json'))
        if completed['wall_budget_exceeded']:completed['status']='BLOCKED_RESOURCE'
        dump(out/'COMPLETION.json',completed)
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True,type=Path);p.add_argument('--identity',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:p.error('--execute required; this starts an authorized GPU engine')
    result=run_diagnostic(a.plan,a.identity,a.out);print(str(result))
