#!/usr/bin/env python3
import json,re,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];errors=[]
for p in root.rglob('*.json'):
 if any(x in p.parts for x in ('work','results','.state')):continue
 try:json.loads(p.read_text())
 except Exception as e:errors.append(f'{p.relative_to(root)}: {e}')
tasks=json.loads((root/'configs/tasks.json').read_text())['tasks'];ids={x['id'] for x in tasks}
if len(ids)!=len(tasks):errors.append('duplicate task ids')
seen=set()
for t in tasks:
 if not (root/t['document']).is_file():errors.append('missing '+t['document'])
 if set(t['depends_on'])-seen:errors.append('non-topological/unknown dependency '+t['id'])
 seen.add(t['id'])
for required in ['AGENT_START.md','README.md','AGENTS.md','references/sources.md','references/source-lock.json','docs/00-master-plan.md']:
 if not(root/required).is_file():errors.append('missing '+required)
for p in (root/'docs').glob('*.md'):
 if any(s in p.read_text() for s in ('TBD','TODO:','PLACEHOLDER')):errors.append('unresolved prose placeholder '+p.name)
print(json.dumps({'status':'PASS' if not errors else 'FAIL','tasks':len(tasks),'errors':errors},ensure_ascii=False,indent=2))
if errors:sys.exit(2)
