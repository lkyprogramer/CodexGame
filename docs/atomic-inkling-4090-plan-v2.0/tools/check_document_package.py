#!/usr/bin/env python3
"""Check document/manifest consistency only. No engine, GPU or shell examples run."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output',type=Path)
    args=ap.parse_args();p=args.package.resolve();errors=[];checks={}
    def ck(ok,message):
        if not ok:errors.append(message)
    def strict_pairs(pairs):
        out={}
        for key,value in pairs:
            if key in out:raise ValueError('duplicate JSON key '+key)
            out[key]=value
        return out
    def reject_constant(x):raise ValueError('Nonfinite JSON '+x)
    def read(rel):return json.loads((p/rel).read_text(),object_pairs_hook=strict_pairs,parse_constant=reject_constant)
    files=[f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts]
    for f in files:
        if f.suffix=='.json':read(f.relative_to(p))
        if f.suffix=='.py':ast.parse(f.read_text(),filename=str(f))
    checks['json_files_parsed']=sum(f.suffix=='.json' for f in files)
    checks['python_files_parsed']=sum(f.suffix=='.py' for f in files)
    g=read('manifests/task-graph.json');tasks=g['tasks'];ids={t['id'] for t in tasks}
    ck(len(ids)==len(tasks)==44,'task count/uniqueness')
    graph={t['id']:t['depends_on']+[d['id'] for d in t.get('conditional_dependencies',[])] for t in tasks}
    for name,deps in graph.items():ck(all(x in ids for x in deps),'unknown dependency '+name)
    seen=set();active=set()
    def walk(name):
        if name in active:raise ValueError('dependency cycle '+name)
        if name in seen:return
        active.add(name)
        for dep in graph[name]:walk(dep)
        active.remove(name);seen.add(name)
    for name in graph:walk(name)
    checks['task_count']=len(tasks);checks['union_dependency_dag_acyclic']=True
    byid={t['id']:t for t in tasks}
    ck(byid['R03']['status']=='NOT_RUN','obsolete R03 blocker')
    ck(all(byid[x]['status']=='DEFERRED' for x in ('G04','K07')),'deferred policy changed')
    ck(all(t['status'] in ('NOT_RUN','DEFERRED','BLOCKED') for t in tasks),'task claims unperformed execution')
    cat=read('manifests/test-catalog.json');tests=cat['tests'];testids={t['id'] for t in tests}
    ck(len(testids)==len(tests)==cat['test_count']==148,'test count/uniqueness')
    for t in tests:
        ck(t['status']=='NOT_RUN','planned test executed claim '+t['id'])
        doc=p/t['source_document']
        ck(doc.is_file(),'missing test source '+t['id'])
        if doc.is_file():ck(re.search(r'^\|\s*'+re.escape(t['id'])+r'\s*\|',doc.read_text(),re.M) is not None,'missing test row '+t['id'])
    for t in tasks:
        required=t.get('required_cache_tests',[])+t.get('required_magnitude_tests',[])
        required += [x['id'] for x in t.get('conditional_magnitude_tests',[])]
        required += [y for x in t.get('conditional_required_tests',[]) for y in x['test_ids']]
        ck(all(x in testids for x in required),'missing referenced test '+t['id'])
    ck(set(read('manifests/run-contract.json')['properties']['task_id']['enum'])==ids,'run task enums mismatch')
    checks['planned_tests']=len(tests);checks['all_planned_tests_not_run']=True
    ck(not set(('LX27','LX28','LX29')) & set(byid['L05']['required_cache_tests']),'conditional tests became global')
    checks['conditional_cache_tests_explicit']=True
    source_ids=re.findall(r'^\| (S\d{2}) \|',(p/'docs/02_evidence_register.md').read_text(),re.M)
    ck(len(source_ids)==len(set(source_ids))==58,'source register uniqueness/count')
    pins=read('manifests/source-lock.json')['sources'];ck(len(pins)==42,'source pin count')
    ck(len({s['id'] for s in pins})==len(pins),'duplicate source pin')
    ck(all(s['id'] in source_ids for s in pins),'unregistered source pin')
    checks['source_register_ids']=len(source_ids);checks['source_pins']=len(pins)
    mg=read('manifests/magnitude-source-pins.json')
    ck(len(mg['branches'])==mg['branch_count']==49,'Magnitude branch count')
    ck(len({b['name'] for b in mg['branches']})==49,'Magnitude branch duplicates')
    ck(len(mg['sources'])==58,'Magnitude source pins')
    ck(mg['repo']['tree_truncated'] is False,'Magnitude incomplete tree')
    checks['magnitude_branches']=49;checks['magnitude_source_pins']=58
    counts={'md':0,'fences':0,'bash':0,'links':0}
    for f in sorted(p.rglob('*.md')):
        counts['md']+=1;fence=None;lang='';block=[];prose=[]
        for line in f.read_text().splitlines():
            match=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
            if fence:
                if match and match[1][0]==fence[0] and len(match[1])>=len(fence) and not match[2].strip():
                    if lang in ('bash','sh','shell'):
                        result=subprocess.run(['bash','-n'],input='\n'.join(block)+'\n',text=True,capture_output=True)
                        counts['bash']+=1;ck(result.returncode==0,'shell syntax '+str(f.relative_to(p))+': '+result.stderr)
                    fence=None
                else:block.append(line)
            elif match:
                fence=match[1];lang=match[2].strip().split(' ')[0];block=[];counts['fences']+=1
            else:prose.append(line)
        ck(fence is None,'unclosed fence '+str(f.relative_to(p)))
        for target in re.findall(r'(?<!!)\[[^\]\n]+\]\(([^\s)]+)\)', '\n'.join(prose)):
            if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',target) or target.startswith('#'):continue
            dest=(f.parent/target.split('#',1)[0]).resolve();counts['links']+=1
            ck(dest==p or p in dest.parents,'link escapes package '+str(f.relative_to(p)))
            ck(dest.exists(),'broken link '+str(f.relative_to(p))+' '+target)
    checks.update(markdown_files=counts['md'],fenced_blocks=counts['fences'],shell_blocks_syntax_only=counts['bash'],relative_links=counts['links'])
    checks['topic_documents']=len(list((p/'docs').glob('*.md')))
    ck(checks['topic_documents']==44,'topic document count')
    report={'scope':'document_structure_only','target_execution':'NOT_RUN','grants_qualification':False,
            'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'status':'PASS' if not errors else 'FAIL','checks':checks,'errors':errors}
    if args.output:
        output=args.output.resolve()
        if output in (Path(__file__).resolve(),p/'manifests/task-graph.json',p/'manifests/test-catalog.json'):
            ap.error('output must not overwrite source contracts')
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__=='__main__':raise SystemExit(main())
