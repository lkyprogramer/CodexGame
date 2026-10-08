"""Validate document links, DAG, fixture identity. Does not touch user services."""
import json,hashlib,re
from pathlib import Path
b=Path(__file__).resolve().parents[1];tasks=json.loads((b/'configs/tasks.json').read_text());by={t['id']:t for t in tasks};assert len(by)==len(tasks)
done=set();active=set()
def visit(t):
    if t in active:raise AssertionError('DAG cycle')
    if t in done:return
    assert t in by;active.add(t)
    for d in by[t]['depends_on']:visit(d)
    active.remove(t);done.add(t)
for t in by:visit(t)
for t in tasks:assert (b/t['file']).is_file(),t['file']
for f in json.loads((b/'references/fixture-lock.json').read_text()):
    p=b/f['path'];assert p.is_file();assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256'],f['path']
for p in list((b/'docs').glob('*.md'))+[b/'README.md']:
    for dest in re.findall(r'\]\(([^)]+)\)',p.read_text()):
        if '://' in dest or dest.startswith('#'):continue
        q=(p.parent/dest.split('#')[0]).resolve();assert q.exists(),f'{p.name}: missing link {dest}'
print(f'DAG {len(tasks)} tasks PASS; original 23 fixture files PASS; Markdown links PASS')
