# V2 支撑材料：`scripts/compare_metrics.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: scripts/compare_metrics.py -->
<!-- payload-sha256: 33e7d3defd6e5d36781e48ff40e3092de9bc14505410150c3060992eada5d90a -->
<!-- payload-bytes: 1900 -->

<!-- payload-begin -->
````python
#!/usr/bin/env python3
"""Compare normalized paired measurements. Never infer values from raw log schemas."""
import argparse
import json
from pathlib import Path
from merge_tools import compare_samples,dump_json

MATCH_KEYS=('gpu_uuid','model_sha256','dataset_sha256','profile','concurrency','max_context','reasoning_effort','kv_dtype','spec','draft_tokens')
def read(path):
    rows=[json.loads(s) for s in path.read_text().splitlines() if s.strip()]
    if not rows or rows[0].get('kind')!='run_metadata':raise ValueError(f'{path}: first row must be run_metadata')
    return rows[0],[r for r in rows[1:] if r.get('kind')=='sample']
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--allow-change',action='append',default=[],choices=MATCH_KEYS)
    p.add_argument('--rules',type=Path);p.add_argument('--min-samples',type=int,default=10);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:
        bm,b=read(a.baseline);cm,c=read(a.candidate)
        for key in MATCH_KEYS:
            if key not in bm or key not in cm:raise ValueError('missing metadata: '+key)
            if key not in a.allow_change and bm[key]!=cm[key]:raise ValueError('uncontrolled comparison factor: '+key)
        # Changing source commit is expected. Changing data/hardware is not silently accepted.
        r=compare_samples(b,c,json.loads(a.rules.read_text()) if a.rules else None,a.min_samples)
        r['declared_changed_factors']={key:{'baseline':bm[key],'candidate':cm[key]} for key in a.allow_change}
        dump_json(a.out,r);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['passed'] else 1
    except (ValueError,KeyError,OSError) as e:p.exit(2,f'comparison blocked: {e}\n')
if __name__=='__main__':raise SystemExit(main())
````
<!-- payload-end -->
