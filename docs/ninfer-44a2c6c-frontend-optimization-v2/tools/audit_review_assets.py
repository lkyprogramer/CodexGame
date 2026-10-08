#!/usr/bin/env python3
"""Audit retained review JSONL evidence without pretending to rerun its benchmarks."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def audit(root:Path)->dict:
    allrows=[];raw=[];byfile={};hashes={}
    for f in sorted((root/'results-29').glob('*.jsonl')):
        rows=[json.loads(s) for s in f.read_text().splitlines() if s.strip()]
        hashes[str(f.relative_to(root))]=hashlib.sha256(f.read_bytes()).hexdigest()
        for r in rows:
            for k,v in r.items():
                if isinstance(v,float) and (not math.isfinite(v) or v<0):raise ValueError(f'invalid value in {f.name}')
                if ('equal' in k) and v is False:raise ValueError(f'retained mismatch in {f.name}')
        if f.name=='raw.jsonl':raw+=rows
        else:allrows+=rows;byfile[f.name]={'rows':len(rows),'first_row':rows[0] if rows else None}
    if not allrows:raise ValueError('no retained session rows')
    return {'status':'RETAINED_FILES_CHECKED','scope':'ATTACHMENT_AUDIT_NOT_RERUN','session_rows':len(allrows),'raw_rows':len(raw),
      'direct_legacy_rows':sum('legacy_s' in r for r in allrows),'indirect_reference_rows':sum('reference' in r for r in allrows),
      'b0_retained_rows':sum('b0_fastscan_legacy_boundaries_s' in r for r in allrows),
      'b2_rows':sum('b2_s' in r for r in allrows),'over_context_rows':sum(r.get('tokens',0)>262144 for r in allrows),
      'all_recorded_equality_flags_true':True,'files':byfile,'sha256':hashes,
      'limitations':['No production logs, frontend resources, overlay diff or original raw corpora supplied.','B0 10.01 s is review-text evidence; no matching raw result row retained.','Reference B0 path omits validation and cloned legacy path omits uint32 overflow check.','B2 timing starts after LCP/search; it is not a complete cache lifecycle benchmark.','scan_bytes estimates logical search spans, not measured DRAM traffic.']}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--assets',type=Path,default=ROOT/'evidence/review-assets');p.add_argument('--output',type=Path);a=p.parse_args()
    try:o=audit(a.assets);s=json.dumps(o,ensure_ascii=False,indent=2)+'\n'
    except (ValueError,OSError,KeyError) as e:p.exit(2,f'error: {e}\n')
    if a.output:a.output.write_text(s)
    else:print(s,end='')
    return 0
if __name__=='__main__':raise SystemExit(main())
