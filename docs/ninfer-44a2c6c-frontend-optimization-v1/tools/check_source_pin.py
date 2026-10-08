#!/usr/bin/env python3
"""Read-only verification of the pinned Git commit/blob set; never fetches or resets."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess

def check(repo: Path, lock: dict) -> dict:
    errors=[];warnings=[];details={}
    def git(*args: str) -> str:
        r=subprocess.run(['git','-C',str(repo),*args],text=True,capture_output=True,timeout=30)
        if r.returncode:raise ValueError(r.stderr.strip() or f'git failed: {args[0]}')
        return r.stdout.strip()
    try:
        pin=lock.get('commit') or lock.get('base_commit')
        if not isinstance(pin,str):raise ValueError('lock has no commit')
        actual=git('rev-parse','--verify',pin+'^{commit}')
        if actual!=pin:errors.append('commit must be a full exact SHA')
        details['base_commit']=actual;details['head']=git('rev-parse','HEAD')
        details['subject']=git('show','-s','--format=%s',pin)
        subject=lock.get('subject') or lock.get('commit_subject')
        if subject and details['subject']!=subject:errors.append('commit subject mismatch')
        if details['head']!=actual:
            git('merge-base','--is-ancestor',actual,'HEAD')
            warnings.append('HEAD is a descendant, not the base. Archive and review its full overlay before comparing.')
        seen={}
        for src in lock.get('sources',lock.get('files',[])):
            path=src['path'];expected=src.get('blob_sha') or src.get('git_blob_sha') or src.get('blob')
            if not expected:raise ValueError(f'missing expected blob for {path}')
            if path in seen and seen[path]!=expected:raise ValueError(f'conflicting lock for {path}')
            seen[path]=expected
        for path,expected in seen.items():
            value=git('rev-parse',pin+':'+path)
            if value!=expected:errors.append(f'blob mismatch: {path}')
        details['checked_unique_blobs']=len(seen)
        dirty=git('status','--porcelain')
        details['working_tree_dirty']=bool(dirty)
        if dirty:warnings.append('Working tree changes exist; this check does not certify the diagnostic image or overlay.')
    except (OSError,ValueError,subprocess.TimeoutExpired,KeyError) as e:errors.append(str(e))
    return {'status':'FAIL' if errors else 'PASS','scope':'BASE_COMMIT_AND_BLOBS_ONLY','errors':errors,'warnings':warnings,**details}

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--lock',type=Path,default=Path(__file__).resolve().parents[1]/'source-lock.json');p.add_argument('--output',type=Path)
    a=p.parse_args()
    try:lock=json.loads(a.lock.read_text(encoding='utf-8'))
    except (ValueError,OSError) as e:p.exit(2,f'error: {e}\n')
    result=check(a.repo,lock);text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.write_text(text,encoding='utf-8')
    else:print(text,end='')
    return 0 if result['status']=='PASS' else 2
if __name__=='__main__':raise SystemExit(main())
