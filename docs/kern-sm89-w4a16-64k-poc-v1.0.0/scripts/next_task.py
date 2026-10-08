#!/usr/bin/env python3
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
tasks=json.loads((root/'configs/tasks.json').read_text())['tasks']
status_path=root/'work/task-status.json';status=json.loads(status_path.read_text()) if status_path.exists() else {}
def passed(i):
    s=status.get(i,{})
    return isinstance(s,dict) and s.get('status')=='PASS' and bool(s.get('evidence'))
ready=[t for t in tasks if not passed(t['id']) and all(passed(d) for d in t['depends_on'])]
print(json.dumps({'ready':[{'id':t['id'],'title':t['title'],'document':t['document'],'gpu_exclusive':t['gpu_exclusive']} for t in ready], 'note':'Advisory only; source/identity checks and GPU lease still required.'},ensure_ascii=False,indent=2))
