# V2 支撑材料：`scripts/phase_gate.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/phase_gate.py -->
<!-- payload-sha256: 32c04c249abc34330bb71e38897e36229b8afda0da69859e33bc5c83b5aa0a3d -->
<!-- payload-bytes: 1065 -->

<!-- payload-begin -->
````python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from merge_tools import check_phase,dump_json,validate_dag

def main():
    p=argparse.ArgumentParser(description='Check phase task, review, JUnit and evidence consistency, not code correctness by assertion.')
    p.add_argument('--plan',type=Path,default=Path(__file__).resolve().parents[1]/'plans/tasks.json')
    p.add_argument('--evidence',type=Path)
    p.add_argument('--out',type=Path)
    p.add_argument('--validate-plan',action='store_true')
    a=p.parse_args();plan=json.loads(a.plan.read_text())
    if a.validate_plan:
        print(json.dumps({'passed':True,'topological_order':validate_dag(plan['tasks'])},ensure_ascii=False,indent=2));return 0
    if not a.evidence:p.error('--evidence is required unless --validate-plan is used')
    r=check_phase(plan,json.loads(a.evidence.read_text()),a.evidence.parent)
    if a.out:dump_json(a.out,r)
    print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
````
<!-- payload-end -->
