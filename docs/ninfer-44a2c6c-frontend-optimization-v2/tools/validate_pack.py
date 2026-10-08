#!/usr/bin/env python3
"""Validate documentation artifacts, data identities and task DAG. Not NInfer validation."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def dag_errors(tasks:list[dict])->list[str]:
    errors=[];by={}
    for t in tasks:
        if t['id'] in by:errors.append('duplicate task '+t['id'])
        by[t['id']]=t
    seen=set();active=set()
    def visit(k):
        if k not in by:errors.append('missing task '+k);return
        if k in active:errors.append('task dependency cycle at '+k);return
        if k in seen:return
        active.add(k)
        for p in by[k].get('dependencies',[]):visit(p)
        active.remove(k);seen.add(k)
    for k in by:visit(k)
    return errors

def check_links(root:Path)->list[str]:
    errors=[]
    for f in root.rglob('*.md'):
        if 'review-assets' in f.parts:continue
        s=re.sub(r'```.*?```','',f.read_text(encoding='utf-8'),flags=re.S)
        for link in re.findall(r'\]\(([^)]+)\)',s):
            link=link.split('#')[0].strip()
            if not link or re.match(r'^[a-z]+:',link):continue
            if not (f.parent/link).exists():errors.append(f'{f.relative_to(root)}: missing {link}')
    return errors

def validate(root:Path,verify_checksums:bool=True)->dict:
    errors=[];counts={'files':0,'markdown':0,'json':0,'jsonl_rows':0}
    for f in root.rglob('*'):
        if not f.is_file() or '__pycache__' in f.parts:continue
        counts['files']+=1
        if f.suffix=='.md':counts['markdown']+=1
        try:
            if f.suffix=='.json':json.loads(f.read_text());counts['json']+=1
            if f.suffix=='.jsonl':
                for line in f.read_text().splitlines():
                    if line.strip():json.loads(line);counts['jsonl_rows']+=1
        except (ValueError,UnicodeError) as e:errors.append(f'{f.name}: {e}')
    errors+=check_links(root)
    try:
        tasks=json.loads((root/'tasks/index.json').read_text())['tasks'];errors+=dag_errors(tasks)
        for t in tasks:
            if not(root/'tasks'/f"{t['id']}.md").is_file():errors.append('missing task card '+t['id'])
        cases=[json.loads(x) for x in (root/'data/adversarial_cases.jsonl').read_text().splitlines() if x.strip()]
        ids=[x['case_id'] for x in cases]
        if len(set(ids))!=len(ids):errors.append('duplicate adversarial case ID')
        matrix=json.loads((root/'data/test-matrix.json').read_text())['cases']
        if set(ids)!={m['case_id'] for m in matrix}:errors.append('case/matrix mismatch')
        lock=json.loads((root/'source-lock.json').read_text())
        if lock['base_commit']!='44a2c6c3392c9d51e76a895ed97bf1867530d252':errors.append('wrong baseline')
        provenance=json.loads((root/'evidence/input-provenance.json').read_text())
        for rel,h in provenance['review_assets_files'].items():
            if hashlib.sha256((root/'evidence/review-assets'/rel).read_bytes()).hexdigest()!=h:errors.append('review asset changed: '+rel)
        gen=root/'data/generated_sessions';gm=json.loads((gen/'manifest.json').read_text())
        for ent in gm['files']:
            if hashlib.sha256((gen/ent['path']).read_bytes()).hexdigest()!=ent['sha256']:errors.append('generated fixture hash mismatch')
        if verify_checksums:
            manifest=root/'MANIFEST.sha256'
            if not manifest.is_file():errors.append('missing MANIFEST.sha256')
            else:
                listed=set()
                for line in manifest.read_text().splitlines():
                    h,rel=line.split('  ',1);listed.add(rel);f=root/rel
                    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=h:errors.append('checksum mismatch: '+rel)
                expected={str(f.relative_to(root)) for f in root.rglob('*') if f.is_file() and f.name!='MANIFEST.sha256' and '__pycache__' not in f.parts}
                if listed!=expected:errors.append('manifest file set mismatch')
    except (ValueError,OSError,KeyError,TypeError) as e:errors.append(str(e))
    return {'status':'FAIL' if errors else 'PASS','scope':'DOCPACK_ONLY','errors':errors,'counts':counts}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--no-checksums',action='store_true');a=p.parse_args()
    r=validate(a.root,not a.no_checksums);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
