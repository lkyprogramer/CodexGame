# V2 支撑材料：`scripts/check_junit.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/check_junit.py -->
<!-- payload-sha256: 598604f1bf6910b1673938e8b056fba6b2d23e1839aadb72a42774397e475cd4 -->
<!-- payload-bytes: 662 -->

<!-- payload-begin -->
````python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from merge_tools import check_junit,dump_json

def main():
    p=argparse.ArgumentParser(description='Reject missing, failed, or skipped mandatory tests.')
    p.add_argument('xml',type=Path)
    p.add_argument('--require',action='append',required=True,help='Required test-name regular expression; repeat for each family')
    p.add_argument('--out',type=Path)
    a=p.parse_args()
    r=check_junit(a.xml,a.require)
    if a.out:dump_json(a.out,r)
    print(json.dumps(r,ensure_ascii=False,indent=2))
    return 0 if r['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
````
<!-- payload-end -->
