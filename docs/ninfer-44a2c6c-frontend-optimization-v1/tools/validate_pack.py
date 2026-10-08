#!/usr/bin/env python3
"""Validate this documentation bundle only; no inference, network or source modification."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

PIN='44a2c6c3392c9d51e76a895ed97bf1867530d252'
REQUIRED=['README.md','AI_START_HERE.md','AGENTS.md','source-lock.json','tasks/index.json',
          'data/diagnostic_summary.json','data/adversarial_cases.jsonl','data/session_recipes.json',
          'schemas/benchmark-row.schema.json','schemas/validation-report.schema.json',
          'tools/check_source_pin.py','tools/summarize_bench.py','tools/generate_sessions.py',
          'templates/gate-report.json','tests/test_tools.py']

def dag_errors(tasks: list[dict]) -> list[str]:
    errors=[];by_id={}
    for t in tasks:
        if t['id'] in by_id:errors.append('duplicate task '+t['id'])
        by_id[t['id']]=t
    def deps(t):return t.get('depends_on',t.get('dependencies',[]))
    for t in tasks:
        for dep in deps(t):
            if dep not in by_id:errors.append(f'unknown dependency {dep}')
    active=set();done=set()
    def visit(tid):
        if tid in active:errors.append('task cycle at '+tid);return
        if tid in done or tid not in by_id:return
        active.add(tid)
        for d in deps(by_id[tid]):visit(d)
        active.remove(tid);done.add(tid)
    for tid in by_id:visit(tid)
    return errors

def check_links(root: Path) -> list[str]:
    errors=[]
    for p in root.rglob('*.md'):
        # Only ordinary Markdown inline links outside fenced code blocks.
        text=re.sub(r'```.*?```','',p.read_text(encoding='utf-8'),flags=re.S)
        for match in re.finditer(r'\[[^\]\n]*\]\(([^)\n]+)\)',text):
            target=match.group(1).split(' "',1)[0].strip('<> ')
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
            target=unquote(target.split('#',1)[0])
            if target and not (p.parent/target).exists():errors.append(f'{p.relative_to(root)} -> missing {target}')
    return errors

def validate(root: Path, verify_checksums: bool=True) -> dict:
    errors=[];warnings=[];counts={}
    if not root.is_dir():return {'status':'FAIL','errors':['bundle directory not found'],'warnings':[],'counts':{}}
    for path in REQUIRED:
        if not (root/path).is_file():errors.append('missing required '+path)
    counts['markdown_files']=len(list(root.rglob('*.md')))
    counts['json_files']=len(list(root.rglob('*.json')))
    for p in root.rglob('*.json'):
        try:json.loads(p.read_text(encoding='utf-8'))
        except (ValueError,OSError) as e:errors.append(f'{p.relative_to(root)}: {e}')
    for p in root.rglob('*.jsonl'):
        for i,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
            if not line.strip():continue
            try:json.loads(line)
            except ValueError as e:errors.append(f'{p.relative_to(root)}:{i}: {e}')
    try:
        lock=json.loads((root/'source-lock.json').read_text(encoding='utf-8'))
        if lock['base_commit']!=PIN:errors.append('source-lock base mismatch')
        files=lock['files'];counts['source_entries']=len(files)
        for src in files:
            if f'/blob/{PIN}/' not in src['url']:errors.append('source URL not pinned: '+src['id'])
            if not re.fullmatch('[0-9a-f]{40}',src['git_blob_sha']):errors.append('bad blob SHA '+src['id'])
        ts=json.loads((root/'tasks/index.json').read_text(encoding='utf-8'))['tasks']
        errors.extend(dag_errors(ts));counts['tasks']=len(ts)
        for t in ts:
            if not (root/'tasks'/t['file']).is_file():errors.append('task card missing '+t['id'])
        fs=[json.loads(x) for x in (root/'data/adversarial_cases.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
        counts['adversarial_cases']=len(fs)
        if len({f['case_id'] for f in fs})!=len(fs):errors.append('duplicate fixture IDs')
        for f in fs:
            if not f.get('checks'):errors.append('fixture has no checks '+f['case_id'])
            if 'byte_cuts' in f:
                n=len(f['text'].encode('utf-8'))
                if any(type(b) is not int or b<0 or b>n for b in f['byte_cuts']):errors.append('invalid raw cut '+f['case_id'])
        ds=json.loads((root/'data/diagnostic_summary.json').read_text(encoding='utf-8'))
        delta=ds['reported_requests']-sum(x['n'] for x in ds['bins'])
        if delta: warnings.append(f'User aggregate bins differ from total by {delta}; intentionally retained, not repaired.')
        recipes=json.loads((root/'data/session_recipes.json').read_text(encoding='utf-8'))['recipes'];counts['session_recipes']=len(recipes)
    except (OSError,KeyError,ValueError,TypeError) as e:errors.append('bundle structure: '+str(e))
    errors.extend(check_links(root))
    mf=root/'MANIFEST.sha256'
    if verify_checksums and mf.exists():
        expected=set()
        for line in mf.read_text(encoding='utf-8').splitlines():
            try:sha,rel=line.split('  ',1)
            except ValueError:errors.append('bad checksum line');continue
            p=root/rel;expected.add(rel)
            if not p.is_file():errors.append('checksum file missing '+rel)
            elif hashlib.sha256(p.read_bytes()).hexdigest()!=sha:errors.append('checksum mismatch '+rel)
        counts['checksummed_files']=len(expected)
        for p in root.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts or p.name=='MANIFEST.sha256':continue
            rel=str(p.relative_to(root))
            if rel not in expected:errors.append('unmanifested file '+rel)
    elif verify_checksums:warnings.append('MANIFEST.sha256 not present yet; structure-only validation.')
    return {'status':'FAIL' if errors else 'PASS','errors':errors,'warnings':warnings,'counts':counts}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--no-checksums',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args()
    r=validate(a.root,not a.no_checksums);text=json.dumps(r,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.write_text(text,encoding='utf-8')
    else:print(text,end='')
    return 0 if r['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
