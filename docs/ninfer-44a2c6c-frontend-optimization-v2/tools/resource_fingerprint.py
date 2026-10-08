#!/usr/bin/env python3
"""Hash six raw frontend resources. Does not use the converter's official allowlist."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
NAMES=('tokenizer.json','tokenizer_config.json','chat_template.jinja','generation_config.json','preprocessor_config.json','video_preprocessor_config.json')

def fingerprint(root:Path)->dict:
    files={}
    for name in NAMES:
        f=root/name
        if not f.is_file():raise ValueError(f'missing resource: {name}')
        raw=f.read_bytes();files[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    canonical=json.dumps(files,sort_keys=True,separators=(',',':')).encode()
    return {'status':'LOCAL_BYTES_MEASURED_NOT_PRODUCTION_CERTIFIED','files':files,'resources_sha256':hashlib.sha256(canonical).hexdigest(),'production_provenance_requires_artifact_directory_receipt':True}

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try:s=json.dumps(fingerprint(a.directory),indent=2)+'\n'
    except (ValueError,OSError) as e:p.exit(2,f'error: {e}\n')
    if a.output:a.output.write_text(s)
    else:print(s,end='')
    return 0
if __name__=='__main__':raise SystemExit(main())
