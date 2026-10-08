import json
from pathlib import Path
b=Path(__file__).resolve().parents[1]
tasks=json.loads((b/'configs/tasks.json').read_text());p=b/'results/tasks-state.json';state=json.loads(p.read_text()) if p.exists() else {}
ready=[t for t in tasks if t['enabled'] and state.get(t['id'])!='PASS' and all(state.get(d)=='PASS' for d in t['depends_on'])]
print('\n'.join(f"{x['id']} {x['title']} -> {x['file']}" for x in ready) or 'No enabled task is ready. Check dependencies/blocked decisions; do not bypass them.')
