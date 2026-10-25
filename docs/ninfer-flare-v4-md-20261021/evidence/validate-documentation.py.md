# 只读文档检查器

仅检查本地文档/快照/图/断言/预算；不联网、不运行产品命令或修改被检文件。负控制只在内存修改registry。

从仓库根目录提取执行：

```bash
python3 - <<'EXTRACT'
from pathlib import Path
p = Path('docs/ninfer-flare-v4-md-20261021/evidence/validate-documentation.py.md')
Path('/tmp/validate_ninfer_v4_performance_scope.py').write_text(p.read_text().split('```python\n', 1)[1].rsplit('\n```', 1)[0]+'\n')
EXTRACT
python3 /tmp/validate_ninfer_v4_performance_scope.py docs/ninfer-flare-v4-md-20261021
```

检查要求原始快照、Baseline和保全来源存在；单独搬运本包缺来源时明确失败。

```python
"""Read-only local documentation/provenance checks. No network or product operations."""
import copy
import hashlib
import json
import re
import sys
import tarfile
from pathlib import Path
from urllib.parse import unquote

def need(c,m):
    if not c: raise ValueError(m)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def block(p): return json.loads(re.search(r'```json\s*([\s\S]*?)```',p.read_text()).group(1))
def dag(edges):
    done=set(); active=set()
    def visit(k):
        need(k not in active,'cycle:'+k)
        if k in done:return
        active.add(k)
        for d in edges[k]:
            need(d in edges,'dangling:'+d);visit(d)
        active.remove(k);done.add(k)
    for k in edges:visit(k)

def graph(d):
    need(d['schema']=='ninfer.plan.md.v4.chat-perf.2','schema')
    ts=d['tasks'];ids=[t['id'] for t in ts];need(len(set(ids))==len(ids),'duplicate_node')
    by={t['id']:t for t in ts}; aa=[]
    required={'PERF-READY','K0-T01','K0-T02','K0-T04','K0-GATE','K1-T01','K1-T02','K2-T01','K3-T01','K3-T02','H1-T01','H1-T07','H2-T01','H3-T01','H4-T01','H6-T01','H7-T01','S0-T01','UP-T01','C0-T01','K4-T01','K4-QUALIFIED','K4-GATE'}
    need(set(ids)==required,'unexpected_or_missing_active_node')
    for t in ts:
        need(t['status']=='PENDING','false_execution_claim')
        need(not t['document'].startswith('baseline-v3/'),'historical_execution_authority')
        need(t['kind'] in ['task','gate','qualification_gate','publication_gate'],'node_kind')
        if t['kind']=='task':
            a=t['assertion_ids'];need(len(a)==4 and len(t['tests'])==4,'missing_assertions')
            need(all(x.startswith('CHATPERF-'+t['id']+'-V') for x in a),'assertion_namespace');aa+=a
            b=t['planned_budget']
            if b:
                need(0<b['wire_max']<=64 and 0<b['total_model_submissions_max']<=50,'budget_cap')
                need(b['total_model_submissions_max']==b['client_model_requests_max']+b['warmup_submissions_max'],'submission_accounting')
                need(b['wire_max']>=b['client_model_requests_max'],'wire_accounting')
                need(b['gpu_minutes_max']<=90 and b['native_calls_max']<=126,'iteration_cap')
    need(len(aa)==len(set(aa)),'duplicate_assertion')
    need(by['K0-T01']['depends_on']==['PERF-READY'],'development_blocked')
    need(by['K0-T04']['depends_on']==['K0-T02'],'correction_or_full_gate_blocks_selection')
    need(by['K0-GATE']['depends_on']==['K0-T04'],'extra_attribution_prerequisite')
    need(by['H4-T01']['depends_on']==['H3-T01'],'w16_needs_w8')
    for k in ['K1-T01','K2-T01','K3-T01','K3-T02','H1-T01','H1-T07','H2-T01','H3-T01','H6-T01','H7-T01','S0-T01','UP-T01','C0-T01']:
        need(by[k]['depends_on']==['K0-GATE'],'unnecessary_serial_prerequisite:'+k)
    need(by['K1-T02']['depends_on']==['K1-T01'],'correction_order')
    need(by['K4-QUALIFIED']['depends_on']==['K4-T01'],'candidate_qualification')
    need(by['K4-GATE']['depends_on']==['K4-QUALIFIED'],'publication_bypass')
    dag({k:t['depends_on'] for k,t in by.items()})
    need(d['scope_contract']['no_automatic_dependency_closure'] is True,'automatic_scope_expansion')
    need(d['scope_contract']['budget_authorization']=='PROPOSED_ONLY_NOT_ADDITIVE','permission_or_additive_budget')
    ev=d['execution_evidence']
    need(ev['research_base_tree']=='35d3dd9e4aa96b1f56f2e9c55482946bd9911cde','wrong_research_base')
    need(ev['G1_differences']==18 and ev['C1_attachment_gap']=='PRESERVED','erased_gap')
    need(ev['original_service']=='STOPPED_DO_NOT_RESTORE','restore_without_request')
    need(ev['p95'] is None and ev['optimization_qualification'] is False,'invented_performance')
    branches={'correction':['K1-T01','K1-T02'],'kernel':['K2-T01'],'workspace':['K3-T01'],'projection_overlap':['K3-T02'],'lookup':['H1-T01','H1-T07'],'draft_head':['H2-T01','H1-T07'],'w8':['H3-T01','H1-T07'],'w16':['H3-T01','H4-T01','H1-T07'],'dflash2':['H6-T01','H1-T07'],'global_retrieval':['H7-T01','H1-T07'],'utility':['S0-T01'],'upstream_selective':['UP-T01'],'upstream_full':['UP-T01'],'cpu_sha':['C0-T01']}
    scopes=d['release_scopes'];need(len(scopes)==29,'scope_count')
    names=[s['scope_id'] for s in scopes];need(len(set(names))==len(names),'duplicate_scope')
    need(set(names)=={'attribution_only'}|{k+'_'+m for k in branches for m in ['candidate','publication']},'optional_experiment_scope_missing')
    core={'PERF-READY','K0-T01','K0-T02','K0-T04','K0-GATE'}
    result={}
    for s in scopes:
        chosen=set(s['include_ids']);need(len(chosen)==len(s['include_ids']),'duplicate_scope_node')
        need(chosen<=set(by),'unknown_scope_node')
        need(s['requires_future_implementation_authorization'] is True,'permission_inferred')
        if s['mode']=='research':
            need(s['scope_id']=='attribution_only' and chosen==core,'research_scope_expanded')
            need(not s['dependency_overrides'],'research_override')
        else:
            need(s['mode'] in ('candidate','publication'),'scope_mode')
            branch=branches[s['variant']]
            expected=core|set(branch)|{'K4-T01','K4-QUALIFIED'}
            if s['mode']=='publication':expected.add('K4-GATE')
            need(chosen==expected,'unselected_branch_or_missing_node:'+s['scope_id'])
            need(s['dependency_overrides']=={'K4-T01':branch},'scope_validation_dependencies')
        need(s['requires_future_production_authorization']==(s['mode']=='publication'),'publication_authorization')
        need(sorted(chosen)==s['resolved_node_ids'],'scope_resolved_mismatch')
        need(set(s['dependency_overrides'])<=chosen,'override_outside_scope')
        edges={k:by[k]['depends_on'] for k in chosen};edges.update(s['dependency_overrides']);dag(edges)
        if s['mode']!='publication':need('K4-GATE' not in chosen,'candidate_publishes')
        result[s['scope_id']]=len(chosen)
    return by,aa,result

def mutations(d):
    out={}
    def reject(name,fun):
        x=copy.deepcopy(d);fun(x)
        try:graph(x)
        except (ValueError,KeyError):out[name]='REJECTED'
        else:raise ValueError('accepted_negative:'+name)
    def node(x,k):return next(t for t in x['tasks'] if t['id']==k)
    def scope(x,k):return next(t for t in x['release_scopes'] if t['scope_id']==k)
    reject('duplicate_node',lambda x:x['tasks'].append(copy.deepcopy(x['tasks'][0])))
    reject('dangling_dependency',lambda x:node(x,'K4-T01')['depends_on'].append('MISSING'))
    reject('cycle',lambda x:node(x,'PERF-READY')['depends_on'].append('K0-T01'))
    reject('false_pass',lambda x:node(x,'K2-T01').update(status='PASS'))
    reject('missing_assertion',lambda x:node(x,'K2-T01').update(assertion_ids=[]))
    reject('historical_task_authority',lambda x:node(x,'K2-T01').update(document='baseline-v3/plans/tasks/H1-T01.md'))
    reject('P5_feature_prerequisite',lambda x:node(x,'K0-T01').update(depends_on=['P5-GATE']))
    reject('P6_blocks_attribution',lambda x:node(x,'K0-T04').update(depends_on=['P6-QUALIFIED']))
    reject('correction_oracle_blocks_all',lambda x:node(x,'K0-GATE')['depends_on'].append('K1-T01'))
    reject('W16_blocks_kernel',lambda x:node(x,'K2-T01')['depends_on'].append('H4-T01'))
    reject('Lookup_blocks_DFlash',lambda x:node(x,'H6-T01')['depends_on'].append('H1-T01'))
    reject('DFlash_blocks_token_retrieval',lambda x:node(x,'H7-T01')['depends_on'].append('H6-T01'))
    reject('full_ladder_blocks_utility',lambda x:node(x,'S0-T01')['depends_on'].extend(['H4-T01','H6-T01','H7-T01']))
    reject('W16_bypasses_W8',lambda x:node(x,'H4-T01').update(depends_on=['K0-GATE']))
    reject('remove_advanced_experiment',lambda x:x['tasks'].remove(node(x,'H6-T01')))
    reject('remove_full_upstream_candidate',lambda x:x['release_scopes'].remove(scope(x,'upstream_full_candidate')))
    reject('candidate_contains_release',lambda x:scope(x,'kernel_candidate')['include_ids'].append('K4-GATE'))
    reject('omit_sampling_contract',lambda x:scope(x,'lookup_candidate')['dependency_overrides'].update({'K4-T01':['H1-T01']}))
    reject('scope_set_drift',lambda x:scope(x,'kernel_candidate')['resolved_node_ids'].pop())
    reject('override_outside_scope',lambda x:scope(x,'kernel_candidate')['dependency_overrides'].update({'H6-T01':[]}))
    reject('auto_expand_scope',lambda x:x['scope_contract'].update(no_automatic_dependency_closure=False))
    reject('sum_per_task_budgets',lambda x:x['scope_contract'].update(budget_authorization='PER_TASK_ADDITIVE'))
    reject('exceed_budget',lambda x:node(x,'H6-T01')['planned_budget'].update(wire_max=999))
    reject('hide_warmup_submissions',lambda x:node(x,'H6-T01')['planned_budget'].update(total_model_submissions_max=48))
    reject('erase_C1_gap',lambda x:x['execution_evidence'].update(C1_attachment_gap='PASS'))
    reject('fake_p95',lambda x:x['execution_evidence'].update(p95=0))
    reject('restore_original_automatically',lambda x:x['execution_evidence'].update(original_service='RESTORE'))
    return out

def check(root):
    repo=root.parent.parent;out=repo/'output/ninfer-v4-performance-scope-20261023'
    before=json.loads((out/'before-files.json').read_text());receipt=json.loads((out/'archive-receipt.json').read_text())
    need(digest(out/receipt['archive'])==receipt['archive_sha256'],'archive_hash')
    need(digest(out/'before-files.json')==receipt['before_files_sha256'],'before_manifest_hash')
    need(digest(out/'before-registry.json')==receipt['original_registry_sha256'],'old_registry_hash')
    with tarfile.open(out/receipt['archive'],'r:gz') as tf:
        members={m.name:m for m in tf.getmembers() if m.isfile()};need(set(members)==set(before),'archive_members')
        for p,m in before.items():
            raw=tf.extractfile(members[p]).read();need(len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256'],'archive_bytes:'+p)
    hist=[p for p in before if p.startswith('baseline-v3/')];need(len(hist)==288,'historical_count')
    for p in hist:need(digest(root/p)==before[p]['sha256'],'historical_modified:'+p)
    orig=block(repo/'output/ninfer-flare-v4-revision-20261021/PRESERVATION-RECEIPT.md')
    for key,base in [('original_files',Path(orig['archive_root'])),('source_v3_files',Path(orig['latest_v3_source_root']))]:
        need(set(orig[key])=={str(p.relative_to(base)) for p in base.rglob('*.md')},'original_source_members')
        for p,m in orig[key].items():need((base/p).stat().st_size==m['bytes'] and digest(base/p)==m['sha256'],'original_source_changed:'+p)
    payload=0
    source=Path(orig['latest_v3_source_root'])
    for sub in ['previous-v2','inputs']:
        for f in (source/sub).rglob('*.md'):
            need(f.read_bytes()==(root/'baseline-v3'/f.relative_to(source)).read_bytes(),'historical_payload_changed');payload+=1
    expected={'FINAL-REPORT.md':'e2353fe3078054a5bab4b7b2bbea975b9f65a188d05dad7a4d2a8f8f02419acb','final-summary.json':'42360b6f88d9c875d4beb8be9ef5744f5bf8e2c39d7ac92e82df241fb17a158a','reference-metrics.csv':'28776efb58c43177c82dd72cebccb879c3aec7e0297cd932db36a8f3cda93e14'}
    need(block(root/'evidence/03-revision-provenance.md')==expected,'baseline_hash_contract')
    for p,h in expected.items():need(digest(repo/'output/ninfer-baseline-29-20261020'/p)==h,'baseline_changed')
    bs=json.loads((repo/'output/ninfer-baseline-29-20261020/final-summary.json').read_text())
    need((bs['resolved'],bs['reused'],bs['collected'])==(278,28,250),'baseline_denominator')
    need(bs['p95'] is None and bs['optimization_qualification'] is False,'baseline_fake_pass')
    need(bs['manifest_sha256']=='2a1679ad2f21d20a4348d1747f4b450687b0db7b6fdac3c4d841d003a136f76e','baseline_manifest')
    old=json.loads((out/'before-registry.json').read_text());audit=json.loads((out/'node-disposition.json').read_text());assertaudit=json.loads((out/'assertion-disposition.json').read_text())
    need(len(audit)==144 and {t['original_id'] for t in audit}=={t['id'] for t in old['tasks']},'old_node_disposition')
    oldassert={a:(t['id'],v) for t in old['tasks'] for a,v in zip(t.get('assertion_ids',[]),t.get('tests',[]))}
    need(len(assertaudit)==373 and {a['id']:(a['node'],a['meaning']) for a in assertaudit}==oldassert,'old_assertion_meaning_changed')
    docaudit=json.loads((out/'document-disposition.json').read_text());need(len(docaudit)==115 and {a['path'] for a in docaudit}==set(before)-set(hist),'document_audit_coverage')
    data=block(root/'plans/02-task-registry.md');by,aa,scopes=graph(data)
    need(len(by)==23 and len(aa)==76,'current_counts')
    for a in audit:need(set(a['successor_ids'])<=set(by),'disposition_successor')
    for t in by.values():
        doc=root/t['document'];need(doc.exists(),'node_document_missing')
        txt=doc.read_text()
        if t['kind']=='task':
            need(re.findall(r'\*\*(CHATPERF-[A-Z0-9-]+)\*\*',txt)==t['assertion_ids'],'task_assertions:'+t['id'])
            for meaning in t['tests']:need(meaning in txt,'task_meaning:'+t['id'])
        header=next(line for line in txt.splitlines() if '前置：' in line)
        need(re.findall(r'`([^`]+)`',header)==t['depends_on'],'task_dependencies:'+t['id'])
    matrix=(root/'plans/04-acceptance-matrix.md').read_text()
    need(re.findall(r'^\| (CHATPERF-[A-Z0-9-]+) \|',matrix,re.M)==aa,'matrix_order_or_set')
    for t in by.values():
        for a,v in zip(t.get('assertion_ids',[]),t.get('tests',[])):
            need('| '+a+' | '+t['id']+' | '+v.replace('|','&#124;')+' |' in matrix,'matrix_meaning')
    files=sorted(p for p in root.rglob('*') if p.is_file());need(all(p.suffix=='.md' for p in files),'non_markdown_member')
    links=0
    for f in files:
        fence=None;plain=[]
        for line in f.read_text().splitlines():
            m=re.match(r'^\s*(`{3,}|~{3,})(.*)$',line)
            if m:
                run,suffix=m.groups()
                if fence is None:fence=run
                elif run[0]==fence[0] and len(run)>=len(fence) and not suffix.strip():fence=None
            elif fence is None:plain.append(line)
        need(fence is None,'unclosed_fence:'+str(f))
        for dest in re.findall(r'\]\(([^\n)]+)\)','\n'.join(plain)):
            dest=dest.strip().split(' "')[0].strip('<>')
            if '://' in dest or dest.startswith(('#','mailto:')):continue
            dest=unquote(dest.split('#')[0]);dest=re.sub(r':\d+$','',dest)
            if dest:need((f.parent/dest).exists(),'broken_link:'+str(f)+':'+dest);links+=1
    rows=re.findall(r'^\| `([^`]+)` \| (\d+) \| `([a-f0-9]{64})` \|$',(root/'MANIFEST.md').read_text(),re.M)
    rels={str(f.relative_to(root)) for f in files}
    need(len(rows)==len(files)-1 and {p for p,_,_ in rows}==rels-{'MANIFEST.md'},'manifest_members')
    for p,n,h in rows:need((root/p).stat().st_size==int(n) and digest(root/p)==h,'manifest_hash:'+p)
    index=(root/'INDEX.md').read_text();need(set(re.findall(r'^- \[([^]]+)\]',index,re.M))==rels,'index_members')
    for p in data['governing_documents']:need((root/p).exists(),'governing_document_missing')
    upstream=json.loads((out/'upstream-source-audit.json').read_text())
    need(upstream['remaining_changed_files']==139 and upstream['remaining_gpu_ops_changed']==[],'upstream_assessment_drift')
    for w in upstream['source_witnesses']:need(digest(out/w['copy'])==w['sha256'],'source_witness_hash')
    p4=json.loads((repo/'output/ninfer-v4-p4-chat-recheck-20261023-r2/final-summary.json').read_text())
    need(p4['source_tree']==data['execution_evidence']['research_base_tree'] and p4['original_service_running'] is False,'P4_base_mismatch')
    need(p4['G1_differences_preserved']==18 and p4['C1_attachment_gap']=='PRESERVED_UNRESOLVED','P4_limitations')
    k0=json.loads((repo/'output/ninfer-v4-k0-20261023/selection.json').read_text())
    need(k0['candidate_scope']=='cpu_sha_candidate' and k0['task']=='C0-T01','K0_selection_drift')
    need(k0['new_execution_this_K0']['model_requests']==0 and k0['new_execution_this_K0']['GPU_op']==0,'K0_execution_scope')
    c0=json.loads((repo/'output/ninfer-v4-c0-20261023/final-summary.json').read_text())
    need(c0['CPU_validation']==dict(scenarios=31,comparisons=58,timing_pairs=7),'C0_budget_receipt')
    need(c0['GPU_model_HTTP_requests']==0 and c0['original_service_running'] is False,'C0_execution_scope')
    need(data['execution_evidence']['C0']['candidate_tree']==c0['source_tree'],'C0_candidate_identity')
    need(c0['p95'] is None and c0['optimization_qualification'] is False and not c0['candidate_K4_qualified'],'C0_qualification_boundary')
    prep=json.loads((repo/'output/ninfer-v4-c0-hw-prep-20261023/preparation-receipt.json').read_text())
    need(prep['GPU_HTTP_model_executed']==0 and not prep['original_running'] and not prep['real_run_invoked'],'C0_prep_execution_boundary')
    need(all(value==0 for value in prep['budget_used'].values()),'C0_prep_budget_not_empty')
    need(data['execution_evidence']['C0_hardware_preparation']['freeze_sha256']==prep['freeze_sha256'],'C0_prep_freeze_binding')
    return dict(status='PASS_DOCUMENTS_ONLY',markdown_files=len(files),active_tasks=19,gates=4,assertions=len(aa),candidate_scopes=14,publication_scopes=14,research_scopes=1,scopes=scopes,archive_members_verified=len(before),unchanged_inherited_files=len(hist),old_nodes_audited=len(audit),old_assertions_preserved=len(assertaudit),current_layer_documents_audited=len(docaudit),original_V4_files_verified=len(orig['original_files']),original_V3_files_verified=len(orig['source_v3_files']),historical_payloads_verified=payload,baseline_artifact_hashes_verified=3,local_links_verified=links,manifest_verified=True,upstream_source_witnesses_verified=len(upstream['source_witnesses']),negative_controls=mutations(data),validator_executed_product_tests=False,new_GPU_model_HTTP_grader=0,production_changes=0)

if __name__=='__main__':print(json.dumps(check(Path(sys.argv[1]).resolve()),ensure_ascii=False,indent=2))
```
