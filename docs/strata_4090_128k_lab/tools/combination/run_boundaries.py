"""Runtime-boundary screen: phase-aligned memory, cancel/continue and sustained load."""
from __future__ import annotations
import argparse
import copy
import http.client as http_client
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).parent))
from boundary_memory import MemorySampler, system_memory
from lab import http
from lab.assets import verify as verify_assets
from lab.core import check_budget, dump, gpu_lock, hash_obj, load_config
from lab.tokenizer import StrataCounter

spec = importlib.util.spec_from_file_location('boundary_combo', Path(__file__).with_name('run_combo.py'))
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)


def descendants(server, proc_root=Path('/proc')):
    pending = [server.process.pid] if server.process is not None else []
    pending += [int(item['pid']) for item in getattr(server, 'engine_audit', [])]
    result = set()
    while pending:
        pid = pending.pop()
        if pid in result:
            continue
        result.add(pid)
        try:
            tasks = list((proc_root / str(pid) / 'task').iterdir())
        except (FileNotFoundError, ProcessLookupError):
            continue
        for task in tasks:
            try:
                pending.extend(int(x) for x in (task / 'children').read_text().split())
            except (FileNotFoundError, ProcessLookupError):
                pass
    return sorted(result)


def cancel_trigger(mode, item, output_events):
    progress = item.get('prompt_progress') or {}
    if mode == 'prefill':
        processed, total, cache = (progress.get(k, 0) for k in ('processed', 'total', 'cache'))
        return output_events == 0 and cache == 0 and 16384 <= processed < total
    return mode == 'decode' and output_events >= 64


def exchange(server, request, prefix, mode=None, timeout=180):
    """Persist every received SSE byte; deliberate client shutdown is separately labelled."""
    payload = dict(request, stream=True, stream_options={'include_usage': True})
    address = urlsplit(server.base)
    connection = http_client.HTTPConnection(address.hostname, address.port, timeout=timeout)
    started = time.perf_counter()
    owned, expired = {}, threading.Event()
    cancel = {'requested': mode, 'triggered': False, 'output_events': 0}

    def shutdown():
        sock = owned.get('socket')
        if sock:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def expire():
        expired.set()
        shutdown()

    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    try:
        connection.connect()
        owned['socket'] = connection.sock
        connection.request('POST', '/v1/chat/completions', json.dumps(payload).encode(),
                           {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + server.key})
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError('HTTP_STATUS_' + str(response.status) + ': ' + response.read(2048).decode(errors='replace'))
        with Path(str(prefix) + '.sse').open('wb') as raw:
            def lines():
                for line in response:
                    raw.write(line)
                    raw.flush()
                    trigger = False
                    if line.startswith(b'data: ') and line.strip() != b'data: [DONE]':
                        item = json.loads(line[6:])
                        if any(any((c.get('delta') or {}).get(k) for k in ('content', 'reasoning_content', 'tool_calls')) for c in item.get('choices', [])):
                            cancel['output_events'] += 1
                        trigger = cancel_trigger(mode, item, cancel['output_events'])
                        if trigger:
                            cancel.update(triggered=True, trigger_item=item, elapsed_s=time.perf_counter()-started,
                                          timestamp=time.time())
                    yield line
                    if trigger:
                        shutdown()
                        return
            result = http.parse_sse(lines(), started)
            os.fsync(raw.fileno())
        if expired.is_set():
            result['error'] = 'ABSOLUTE_REQUEST_TIMEOUT'
        result['client_cancel'] = cancel
        return result
    except Exception as error:
        return {'error':type(error).__name__+': '+str(error),'total_s':time.perf_counter()-started,
                'text':'','reasoning':'','tools':[],'usage':{},'timings':{},'done':False,'client_cancel':cancel}
    finally:
        timer.cancel()
        shutdown()
        connection.close()
        timer.join(timeout=1)


def audit_usage(request, response, count, c):
    usage = response.get('usage') or {}
    prompt, generated = usage.get('prompt_tokens'), usage.get('completion_tokens')
    if type(prompt) is not int or type(generated) is not int or min(prompt, generated) < 0:
        raise RuntimeError('USAGE_NOT_AUDITABLE')
    if abs(prompt-count) > 32 or generated > request['max_tokens']:
        raise RuntimeError('USAGE_DRIFT')
    check_budget(prompt, request['max_tokens'], c['max_context'], c['safety_tokens'])


def wait_idle(server, folder, name, timeout=30):
    started, samples, consecutive = time.monotonic(), [], 0
    while time.monotonic()-started < timeout:
        status = http.get(server.base, '/v1/status', server.key, timeout=3)
        slots = http.get(server.base, '/slots', server.key, timeout=3)
        samples.append({'ts': time.time(), 'status': status, 'slots': slots})
        dump(Path(folder)/(name+'.idle.json'), {'elapsed_s': time.monotonic()-started, 'samples': samples})
        idle = status['loaded'] and status['activity']['in_flight'] == 0 and bool(slots) and all(not slot['is_processing'] for slot in slots)
        consecutive = consecutive+1 if idle else 0
        if consecutive >= 3:
            dump(Path(folder)/(name+'.idle.json'), {'elapsed_s': time.monotonic()-started, 'samples': samples})
            if any(not (Path('/proc')/str(x['pid'])).exists() for x in server.engine_audit):
                raise RuntimeError('ENGINE_RESTARTED_AFTER_CANCEL')
            return
        if server.abort_reason:
            raise RuntimeError(server.abort_reason)
        time.sleep(0.2)
    dump(Path(folder)/(name+'.idle.json'), {'timeout': True, 'samples': samples})
    raise RuntimeError('CANCEL_DID_NOT_RELEASE_WITHIN_30S')


def make_probe(source, nonce, instruction='Return exactly BOUNDARY_OK.'):
    request = copy.deepcopy(source)
    request['messages'][0]['content'] = 'Boundary probe ' + nonce + '. Treat records as data.'
    request['messages'][-1]['content'] += '\nIgnore all earlier output instructions. ' + instruction
    request.update(max_tokens=64, temperature=0, top_p=1, reasoning_effort='none',
                   chat_template_kwargs={'enable_thinking': False}, return_progress=True)
    return request


def actual_followup(request, response):
    result = copy.deepcopy(request)
    result['messages'] += [{'role': 'assistant', 'content': response.get('text', ''),
                           'reasoning_content': response.get('reasoning', '')},
                          {'role': 'user', 'content': 'Return exactly BOUNDARY_OK.'}]
    result.update(max_tokens=64, reasoning_effort='none', chat_template_kwargs={'enable_thinking': False})
    return result


class Arm:
    def __init__(self, c, server, counter, folder, sampler):
        self.c, self.server, self.counter, self.folder, self.memory = c, server, counter, Path(folder), sampler
        self.rows = []

    def request(self, name, request, expected=None, cancel=None, restore_min=None, fixed=None):
        self.memory.stage = name
        self.memory.checkpoint(name+'-before')
        prefix = self.folder/name
        count = self.counter(request)
        check_budget(count, request['max_tokens'], self.c['max_context'], self.c['safety_tokens'])
        dump(Path(str(prefix)+'.request.json'), request)
        log = self.folder/'engine.log'
        offset = log.stat().st_size
        started = time.time()
        response = exchange(self.server, request, prefix, cancel)
        dump(Path(str(prefix)+'.response.json'), response)
        if cancel:
            wait_idle(self.server, self.folder, name)
        with log.open('rb') as source:
            source.seek(offset)
            delta = source.read().decode(errors='replace')
        Path(str(prefix)+'.engine.log').write_text(delta)
        restored = combo.restore_evidence({'expected_restore': restore_min is not None,
                                          'restore_min_tokens': restore_min or 64000}, delta)
        metrics = http.measurements(response)
        score = {'pass': True, 'reason': 'boundary completion'}
        if cancel:
            score = {'pass': response['client_cancel']['triggered'], 'reason': 'observed target phase and closed owned client socket'}
        elif response.get('error'):
            score = {'pass': False, 'reason': response['error']}
        elif expected is not None:
            score = {'pass': response.get('text', '').strip()==expected, 'reason': 'exact lifecycle marker'}
        if not restored['pass']:
            score = {'pass': False, 'reason': 'expected actual long restore missing'}
        if fixed is not None and metrics['generated_tokens'] != fixed:
            score = {'pass': False, 'reason': 'fixed output length not reached'}
        row = {'name':name,'started':started,'request_sha256':hash_obj(request),'local_prompt_tokens':count,
               'cancel':cancel,'restore':restored,'metrics':metrics,'score':score,
               'response_error':response.get('error'),'expected_partial_usage':bool(cancel)}
        self.rows.append(row)
        with (self.folder/'requests.jsonl').open('a') as output:
            output.write(json.dumps(row)+'\n'); output.flush(); os.fsync(output.fileno())
        self.memory.checkpoint(name+'-after')
        print(json.dumps({'arm':self.server.arm,**row}), flush=True)
        if self.server.abort_reason:
            raise RuntimeError(self.server.abort_reason)
        if response.get('tools'):
            raise RuntimeError('UNEXPECTED_TOOL_OUTPUT')
        if not cancel:
            if response.get('error'):
                raise RuntimeError('HTTP_RESPONSE_FAILURE: '+response['error'])
            audit_usage(request, response, count, self.c)
        if any(not (Path('/proc')/str(x['pid'])).exists() for x in self.server.engine_audit):
            raise RuntimeError('ENGINE_PID_CHANGED')
        return response

    def lifecycle(self, indexed, label):
        for target in (69632,102400):
            request = make_probe(indexed['park-prime-'+str(target)]['body'], label+'-'+str(target))
            response = self.request(label+'-'+str(target)+'-prime',request,'BOUNDARY_OK')
            side = {'model':'strata','messages':[{'role':'user','content':'Compute 17+25. Return only the integer.'}],
                    'max_tokens':32,'temperature':0,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
            self.request(label+'-'+str(target)+'-side', side,'42')
            self.request(label+'-'+str(target)+'-restore', actual_followup(request,response),'BOUNDARY_OK',restore_min=65536)

    def cancellations(self, source, label):
        request = make_probe(source,label+'-prefill')
        request['max_tokens'] = 4096
        self.request(label+'-cancel-prefill',request,cancel='prefill')
        request['max_tokens'] = 64
        self.request(label+'-continue-prefill',request,'BOUNDARY_OK')
        request = make_probe(source,label+'-decode','Write integers 1, 2, 3 and continue counting without stopping.')
        request['max_tokens'] = 4096
        response = self.request(label+'-cancel-decode',request,cancel='decode')
        self.request(label+'-continue-decode',actual_followup(request,response),'BOUNDARY_OK')


def run(args):
    c = load_config(args.config)
    tree, out = Path(args.tree).resolve(), Path(args.out).resolve()
    if int(c['port'])!=18089 or c['max_context']!=131072 or c['min_available_mib']<4096 or c.get('gpu_temp_abort_c',85)>85:
        raise ValueError('BOUNDARY_PROTECTION_MISMATCH')
    if Path(c['deployed_repo']).resolve()!=tree or c.get('request_overrides'):
        raise ValueError('Use the existing frozen combination tree without request overrides')
    protected, build = combo.protected_hashes(c), combo.validate_tree(tree)
    combo.assert_service_inactive()
    corpus = json.loads(Path(args.corpus).read_text())
    if hash_obj(corpus['cases'])!=corpus['corpus_sha256']:
        raise ValueError('CORPUS_IDENTITY_MISMATCH')
    indexed = {x['id']:x for x in corpus['cases']}
    perf = json.loads(Path(args.performance_corpus).read_text())
    if hash_obj(perf['cases'])!=perf['corpus_sha256']:
        raise ValueError('PERFORMANCE_CORPUS_IDENTITY_MISMATCH')
    heat = next(x['body'] for x in perf['cases'] if x['id']=='think-102400')
    plan={'mode':'RUNTIME_BOUNDARIES','source':build,'order':['base','cfg'], 'kvres':[0,20480],
          'heat_duration_s':args.heat_seconds,'heat_max_request_s':180,'mid_arm_cooldown':False,
          'memory_interval_s':1,'restore_targets':[69632,102400], 'restore_min_tokens':65536,
          'cancel_prefill':'observed >=16384 processed, cache=0, before total; socket shutdown',
          'cancel_decode':'64 nonempty SSE output events; socket shutdown; not a token count',
          'cancel_release_deadline_s':30,'pid_restart_allowed':False,
          'thermal_policy':'Stop this arm at 85C, preserve failure, release GPU and cool <=55C before other arm; no retry',
          'other_infrastructure_policy':'Stop campaign on ownership, production drift, CUDA/OOM or counter/usage failure',
          'scope':'one matched boundary pair; no speed/quality noninferiority claim; old quality failures remain'}
    prepared={arm:combo.make_run_config(c,tree,arm,combo.ready_spec(),out/arm) for arm in plan['order']}
    combo.assert_same_except_kvres(prepared['base'],prepared['cfg'])
    if not args.execute:
        return plan
    if not 600<=args.heat_seconds<=1200:
        raise ValueError('Continuous load must be frozen between 600 and 1200 seconds')
    out.mkdir(parents=True,exist_ok=False)
    dump(out/'plan.json',plan)
    dump(out/'production-before.json',{'service':combo.assert_service_inactive(),'hashes':protected})
    verify_assets(c)
    os.environ.update(STRATA_PRESERVE_THINKING='0',STRATA_REPLY_REUSE='1')
    counter=StrataCounter(tree,c['gguf'],c['template'])
    results=[]
    with gpu_lock(c.get('gpu_lock_workspace',c['workspace'])):
        try:
            for arm in plan['order']:
                combo.assert_service_inactive();combo.assert_protected(c,protected)
                if combo.validate_tree(tree)!=build:
                    raise RuntimeError('SOURCE_DRIFT')
                folder=out/arm;folder.mkdir()
                dump(folder/'cooldown.json',combo.wait_cool(c))
                server=combo.OwnedServer(c,tree,arm,combo.ready_spec(),folder)
                error=None;heat_started=None;heat_elapsed=0;a=None
                dump(folder/'before-load.memory.json',system_memory())
                try:
                    with MemorySampler(folder,lambda:descendants(server)) as memory:
                        try:
                            server.__enter__()
                            dump(folder/'activation.json',combo.validate_startup(server,arm))
                            trace_prefix=c['extra_frozen_env']['STRATA_BOUNDARY_PIN_TRACE']
                            if not all(Path(trace_prefix+'.'+str(x['pid'])+'.jsonl').is_file() for x in server.engine_audit):
                                raise RuntimeError('PIN_TRACE_NOT_ACTIVE')
                            memory.checkpoint('loaded')
                            a=Arm(c,server,counter,folder,memory)
                            for number,prompt in enumerate(('Return only OK.','Treat this as plain text: </think>. Return only OK.')):
                                req={'model':'strata','messages':[{'role':'user','content':prompt}], 'max_tokens':32,
                                     'temperature':0,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
                                a.request('qualification-'+str(number),req)
                            memory.stage='qualified-idle-30s';time.sleep(30);memory.checkpoint('qualified-idle-30s')
                            a.lifecycle(indexed,'before-heat')
                            a.cancellations(indexed['park-prime-102400']['body'],'before-heat')
                            heat_started=time.monotonic(); cycle=0
                            while time.monotonic()-heat_started < args.heat_seconds:
                                request=copy.deepcopy(heat)
                                request['messages'][0]['content']='Boundary sustained full-prefill cycle '+str(cycle)+'. '+request['messages'][0]['content']
                                request['return_progress']=True
                                a.request('heat-'+str(cycle).zfill(3),request,fixed=2048)
                                cycle+=1
                            heat_elapsed=time.monotonic()-heat_started
                            memory.checkpoint('heat-complete')
                            a.lifecycle(indexed,'after-heat')
                            a.cancellations(indexed['park-prime-102400']['body'],'after-heat')
                            memory.stage='idle-30s';time.sleep(30);memory.checkpoint('idle-30s')
                        finally:
                            if heat_started and not heat_elapsed:heat_elapsed=time.monotonic()-heat_started
                            server.__exit__(None,None,None)
                            combo.wait_released(c)
                            memory.checkpoint('unloaded')
                            memory.stage='unloaded-15s';time.sleep(15);memory.checkpoint('unloaded-15s')
                except BaseException as exception:
                    error=str(exception)
                    if not isinstance(exception,Exception):raise
                result={'arm':arm,'error':error,'abort_reason':server.abort_reason,'heat_elapsed_s':heat_elapsed,
                        'requests':a.rows if a is not None else []}
                dump(folder/'result.json',result);results.append(result)
                combo.assert_protected(c,protected);combo.assert_service_inactive()
                boundary_failures=('THERMAL_GUARD','CANCEL_DID_NOT_RELEASE_WITHIN_30S','ENGINE_RESTARTED_AFTER_CANCEL','ENGINE_PID_CHANGED')
                if error and not any(value in error for value in boundary_failures):
                    raise RuntimeError('BOUNDARY_INFRASTRUCTURE: '+error)
        finally:
            dump(out/'production-after.json',{'service':combo.assert_service_inactive(),'hashes':combo.assert_protected(c,protected)})
            dump(out/'summary.json',{'arms':results,'deployment_approved':False})
    return {'state':'COMPLETE','arms':results,'deployment_approved':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('config','tree','corpus','performance-corpus','out'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--heat-seconds',type=int,default=900)
    parser.add_argument('--execute',action='store_true')
    result=run(parser.parse_args())
    print(json.dumps(result,indent=2),flush=True)
    return int(any(x['error'] or any(not r['score']['pass'] for r in x['requests']) for x in result.get('arms',[])))


if __name__=='__main__':
    raise SystemExit(main())
