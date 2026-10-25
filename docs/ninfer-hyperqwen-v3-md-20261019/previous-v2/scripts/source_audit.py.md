# V2 支撑材料：`scripts/source_audit.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/source_audit.py -->
<!-- payload-sha256: 683e4e7786a27ae176578f3307363ed4f91696409942b0534c1330a83a80e50a -->
<!-- payload-bytes: 957 -->

<!-- payload-begin -->
````python
#!/usr/bin/env python3
"""Audit already-fetched pinned Git objects; never fetch or push by itself."""
import argparse
import json
from pathlib import Path
from merge_tools import audit_repository

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--pin',type=Path,default=Path(__file__).resolve().parents[1]/'data/source-lock.json')
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--merge-probe',action='store_true',help='Run ort in a disposable local clone, never in the given working tree')
    a=p.parse_args()
    try:
        result=audit_repository(a.repo,json.loads(a.pin.read_text()),a.out,a.merge_probe)
        print(json.dumps({k:v for k,v in result.items() if k!='diffs'},ensure_ascii=False,indent=2))
    except (ValueError,RuntimeError,OSError,KeyError) as e:
        p.exit(2,f'audit blocked: {e}\n')
if __name__=='__main__':main()
````
<!-- payload-end -->
