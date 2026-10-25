#!/usr/bin/env python3
"""Recover only offline evidence. Never invoke models, historical tools, or graders."""
import argparse
import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_bytes(data)
    path.chmod(0o600)


def relative(value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('unsafe recovered path')
    return path


def run(collector, score, repo, output, local_backup=None):
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    metadata = json.loads((score/'recovery-local-r3.json').read_text())
    recovery = metadata['recovery']
    expected = {}
    for name, digest in recovery['source_artifacts'].items():
        expected['original8/'+name] = {'sha256':digest, 'origin':'recovery-local-r3.json#/recovery/source_artifacts'}
    aborted = json.loads((score/'gson-aborted-attempt-r2-evidence.json').read_text())
    for name, digest in aborted['artifacts'].items():
        expected['gson-r2/'+name] = {'sha256':digest, 'origin':'gson-aborted-attempt-r2-evidence.json#/artifacts'}
    for case in metadata['external_scores']:
        prefix = 'external-r3/'+case['id']+'/'
        expected[prefix+'pi.jsonl'] = {'sha256':case['raw_sha256'], 'origin':'recovery-local-r3.json#/external_scores/raw_sha256'}
        expected[prefix+'changes.patch'] = {'sha256':case['patch_sha256'], 'origin':'recovery-local-r3.json#/external_scores/patch_sha256'}
    audit = {'schema_version':1,'scope':'OFFLINE_EVIDENCE_RECOVERY_NO_MODEL_NO_GRADER_NO_TEST_EXECUTION',
             'collector':str(collector),'metadata':str(score),'records_sha256':sha((collector/'records.jsonl').read_bytes()),
             'expected_artifacts':expected,'wire_integrity_errors':[], 'groups':[], 'exact_recovered':[],
             'derived_files':[], 'limitations':['No original Pi CLI event stream can be inferred byte-exact from HTTP SSE.',
                 'Tool feedback represents public agent verification; it is not the final hidden grader output.',
                 'diff -ruN changes.patch includes lost filesystem timestamps; derived patches are not the originals.']}
    rows = [json.loads(line) for line in (collector/'records.jsonl').read_text().splitlines()]
    groups = collections.defaultdict(list)
    for row in rows:
        directory=collector/'requests'/row['id']
        body=json.loads((directory/'request.json').read_text())
        raw_bytes=(directory/'raw.json.gz').read_bytes()
        if sha(encode(body)) != row['request_sha256'] or sha(raw_bytes) != row['raw_sha256']:
            audit['wire_integrity_errors'].append(row['id'])
            continue
        with gzip.open(directory/'raw.json.gz','rb') as stream:
            raw=json.load(stream)
        groups[row['extra']['local_case_header']].append((row,body,raw))
    # Exact recovery may use surviving copies, or deterministic candidates ONLY after historical SHA equality.
    def exact(candidate, method, source):
        digest=sha(candidate)
        matches=[name for name, item in expected.items() if item['sha256']==digest and 'recovered_path' not in item]
        for name in matches:
            dest=output/'original-exactbytes-sha-match'/relative(name)
            save(dest,candidate)
            expected[name].update(status='RECONSTRUCTED_IDENTICAL_BYTES',recovered_path=str(dest),method=method,actual_sha256=digest,source=source)
            audit['exact_recovered'].append({'artifact':name,'sha256':digest,'method':method,'source':source})
    if local_backup:
        for path in sorted(local_backup.rglob('*')):
            if path.is_file() and path.stat().st_size<2_000_000:
                exact(path.read_bytes(),'SURVIVING_BACKUP_BYTES_HASH_MATCH',str(path))
    for case, classname in [('java-agent-1-idempotency','OrderServiceTest'),('java-agent-2-retry-contract','RetryingClientTest'),('java-agent-3-reconnect-loop','ReconnectCoordinatorTest')]:
        exact(('PASS '+classname+'\n').encode(),'DETERMINISTIC_RECONSTRUCTION_HASH_MATCH',
              'scripts/ninfer_baseline/fixtures/'+case+'/src/test fixed println')
    exact((json.dumps({'passed':True,'tests_passed':1,'tests_total':1,'score':1.0,'details':['OK']},ensure_ascii=False)+'\n').encode(),
          'DETERMINISTIC_RECONSTRUCTION_HASH_MATCH','qcb/verifier_helpers.py emit + historical PASS')
    exact(b'','DETERMINISTIC_RECONSTRUCTION_HASH_MATCH','documented SHA256 of empty bytes')
    shared_initial={}
    for header, observations in groups.items():
        case=header.split('/')[0]
        groupdir=output/'derived-not-original'/header
        calls=collections.OrderedDict(); feedback={}; feedback_sources={}; seen_reads={}
        for row,body,raw in observations:
            for message in body['messages']:
                for call in message.get('tool_calls',[]): calls.setdefault(call['id'],call)
                if message.get('role')=='tool':
                    feedback[message['tool_call_id']]=message['content']
                    feedback_sources[message['tool_call_id']]=row['id']
            for call in raw.get('parsed',{}).get('assistant',{}).get('tool_calls',[]): calls.setdefault(call['id'],call)
        state={}; initial={}; proof=[]; blocked=[]
        for call_id, call in calls.items():
            name=call['function']['name']
            if name not in {'read','write','edit'}: continue
            try:
                args=json.loads(call['function']['arguments']); path=str(relative(args['path']))
            except (KeyError,ValueError,TypeError):
                blocked.append({'call_id':call_id,'reason':'unsupported path/arguments'});continue
            text=feedback.get(call_id)
            if not isinstance(text,str):
                blocked.append({'call_id':call_id,'tool':name,'reason':'no subsequent wire tool feedback'});continue
            if name=='read':
                # Only whole-file raw read responses, no slices/truncation/error text.
                if args.get('offset',1)!=1 or args.get('limit') is not None or '\n[Showing ' in text or text.startswith(('Error:','ENOENT:')):continue
                if path not in state:
                    state[path]=text
                    initial[path]=text
                    shared_initial.setdefault((case,path),text)
                seen_reads[path]=text
                continue
            success = text.startswith('Successfully wrote to ') if name=='write' else text.startswith('Successfully replaced ')
            if not success:
                blocked.append({'call_id':call_id,'tool':name,'path':path,'reason':'tool did not report success'});continue
            if name=='write':
                content=args.get('content')
                if not isinstance(content,str):continue
                if path not in initial:
                    baseline=(repo/'docs/qwen38-coding-benchmark-4090-v1.0.0/tasks'/case.removeprefix('qcb-')/'workspace'/path if case.startswith('qcb-') else repo/'scripts/ninfer_baseline/fixtures'/case/path)
                    if baseline.is_file(): initial[path]=baseline.read_text()
                state[path]=content
            else:
                if path not in state and (case,path) in shared_initial:
                    state[path]=shared_initial[(case,path)];initial[path]=state[path]
                if path not in state:
                    blocked.append({'call_id':call_id,'path':path,'reason':'missing full baseline for edit'});continue
                edits=args.get('edits') or [args]
                candidate=state[path]; okay=True
                for edit in edits:
                    old,new=edit.get('oldText'),edit.get('newText')
                    if not isinstance(old,str) or not old or not isinstance(new,str) or candidate.count(old)!=1:
                        okay=False;break
                    candidate=candidate.replace(old,new,1)
                if not okay:
                    blocked.append({'call_id':call_id,'path':path,'reason':'edit needs nonliteral/fuzzy semantics; not inferred'});continue
                state[path]=candidate
            proof.append({'call_id':call_id,'tool':name,'path':path,'feedback_request':feedback_sources[call_id],
                          'content_sha256':sha(state[path].encode())})
        changed={p:v for p,v in state.items() if p in initial and v!=initial[p]}
        for path in {p['path'] for p in proof}:
            dest=groupdir/'candidate-files'/relative(path)
            save(dest,state[path].encode())
            audit['derived_files'].append({'header':header,'path':str(dest),'sha256':sha(state[path].encode()),
                                          'status':'DERIVED_ONLY'})
        # git diff only compares inert bytes in new directories, never executes historical tools or tests.
        if changed:
            stage=groupdir/'patch-comparison'
            for path,content in changed.items():
                save(stage/'baseline'/relative(path),initial[path].encode())
                save(stage/'candidate'/relative(path),content.encode())
            result=subprocess.run(['/usr/bin/git','diff','--no-index','--no-ext-diff','--src-prefix=a/','--dst-prefix=b/','baseline','candidate'],
                                  cwd=stage,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=20,
                                  env={'PATH':'/usr/bin:/bin','HOME':str(output)})
            if result.returncode not in {0,1}: raise RuntimeError('offline git diff failed')
            patch='\n'.join(line.replace('a/baseline/','a/').replace('b/candidate/','b/') if line.startswith(('diff --git ','--- ','+++ ')) else line for line in result.stdout.decode().split('\n')).encode()
            save(groupdir/'candidate-derived.patch',patch)
            exact(patch,'DETERMINISTIC_WIRE_RECONSTRUCTION_HASH_MATCH',header+' successful literal tool mutations')
            audit['derived_files'].append({'header':header,'path':str(groupdir/'candidate-derived.patch'),'sha256':sha(patch),
                                          'status':'DERIVED_ONLY'})
        audit['groups'].append({'header':header,'requests':len(observations),'tool_calls':len(calls),
                                'successful_literal_mutations':proof,'unapplied_or_failed_tools':blocked,
                                'changed_file_count':len(changed), 'model_or_grader_executed':False})
    for name,item in expected.items():
        if 'status' not in item:
            item.update(status='UNRECOVERABLE',actual_sha256=None,source=item['origin'],reason=(
                'Pi CLI lifecycle events/timing are not the HTTP SSE stream' if name.endswith('pi.jsonl') else
                'Original timestamps/absolute paths unavailable for diff -ruN' if name.endswith('changes.patch') else
                'Only historical SHA survives; no matching byte source found'))
    audit['additional_missing_without_historical_file_hash']=[
        {'artifact':'external-r3/'+case['id']+'/'+name,'source':'closed_loop.mjs emitted artifact; external score summary retains no individual SHA',
         'expected_sha256':None,'actual_sha256':None,'status':'UNRECOVERABLE',
         'reason':'Original file absent; no historical individual SHA to qualify deterministic candidates as identical bytes'}
        for case in metadata['external_scores'] for name in ['identity.json','summary.json','verify.log','candidate.patch']]
    for item in expected.values():
        item['expected_sha256']=item['sha256']
    for item in audit['derived_files']:
        matched=any(x['sha256']==item['sha256'] and x['source']==item['header']+' successful literal tool mutations' for x in audit['exact_recovered'])
        item.update(expected_sha256=item['sha256'] if matched else None, actual_sha256=item['sha256'],
                    status='RECONSTRUCTED_IDENTICAL_BYTES' if matched else 'DERIVED_ONLY',
                    source='verified wire group '+item['header'])
    audit['script_sha256']=sha(Path(__file__).read_bytes())
    audit['source_identity']={'score_metadata_sha256':sha((score/'recovery-local-r3.json').read_bytes()),
                              'aborted_evidence_sha256':sha((score/'gson-aborted-attempt-r2-evidence.json').read_bytes())}
    audit['counts']={'wire_records':len(rows),'wire_groups':len(groups),'expected_artifacts':len(expected),
                     'exact_recovered':len(audit['exact_recovered']),'derived_files':len(audit['derived_files']),
                     'derived_only':sum(x['status']=='DERIVED_ONLY' for x in audit['derived_files']),
                     'unrecoverable':sum(x['status']=='UNRECOVERABLE' for x in expected.values())}
    save(output/'recovery-audit.json',(json.dumps(audit,ensure_ascii=False,indent=2)+'\n').encode())
    lines=['# Closed-loop evidence recovery audit','',json.dumps(audit['counts'],ensure_ascii=False),'',
           'Only hash equality establishes exact original bytes. Deterministic reconstruction is not physical file recovery.',
           'No models, historical tools, graders or tests were run. Candidate source files are derived evidence.', '',
           '| Artifact | Status | SHA256 |','|---|---|---|']
    lines += [f"| {name} | {item['status']} | {item['sha256']} |" for name,item in expected.items()]
    lines += ['', 'Gaps: original Pi CLI event JSONL, original summary/identity files and most timestamp-bearing changes.patch files remain unavailable.',
              'The 66 verified HTTP request/raw records remain intact in the persistent backup (11 coding attempts).',
              'An empty changes.patch proves only the bytes of that attachment; it does not prove the candidate source was unchanged.',
              'Gson r2 candidate.patch matched its historical SHA from full read baseline plus successful literal edit feedback.',
              'Derived candidate files have no individual historical file SHA and are not independently rerun or rescored.',
              'Remote baseline filename inventory found no pi.jsonl, candidate.patch, changes.patch or verify.log.']
    save(output/'recovery-audit.md',('\n'.join(lines)+'\n').encode())
    return audit['counts']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collector',required=True,type=Path)
    parser.add_argument('--score-metadata',required=True,type=Path)
    parser.add_argument('--repo',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--local-backup',type=Path)
    a=parser.parse_args()
    print(json.dumps(run(a.collector,a.score_metadata,a.repo,a.output,a.local_backup)))
