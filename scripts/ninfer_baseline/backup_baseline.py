#!/usr/bin/env python3
"""Private evidence snapshots, without stopping or resending any measurement."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = Path('/Users/luo/.codex/task-evidence/ninfer-baseline-29-20261020')
REMOTE_CAPTURE = r'''
import datetime as dt,hashlib,json,os,shutil,tarfile
from pathlib import Path
source=Path('/home/hhtele/ninfer-baseline-20261020')
state=json.loads((source/'slim-v1/status.json').read_text())
watch=json.loads((source/'slim-v1/watchdog.json').read_text())
if FINAL and (state['state']!='MEASUREMENT_STAGES_FINISHED' or watch['state']!='MEASUREMENT_STAGES_FINISHED'):
 raise RuntimeError('final capture requires finished measurement and guardian')
if FINAL:
 report=json.loads((source/'slim-v1/reference-report.json').read_text())
 if report['planned']!=278 or report['resolved']!=278 or report['pending']:
  raise RuntimeError('final capture requires complete logical coverage')
destination=Path('/home/hhtele/ninfer-baseline-backups-20261021')/LABEL
destination.mkdir(parents=True,mode=0o700)
payload=destination/'payload';payload.mkdir(mode=0o700)
cuts={}
for f in source.rglob('records.jsonl'):
 data=f.read_bytes();boundary=data.rfind(b'\n')+1
 # rglob snapshots only complete JSONL records. Unfinished append bytes are not records.
 if boundary==0 and data:raise RuntimeError('no complete record boundary: '+str(f))
 cuts[str(f.relative_to(source))]=data[:boundary]
files=[f for f in source.rglob('*') if f.is_file() and not f.is_symlink()]
index=[]
for f in sorted(files):
 relative=str(f.relative_to(source));before=f.stat()
 with f.open('rb') as stream:data=stream.read(before.st_size)
 if relative in cuts:data=cuts[relative]
 target=payload/relative;target.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
 target.write_bytes(data);target.chmod(0o600)
 after=f.stat();index.append({'path':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
  'source_changed_during_copy':before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns})
record_sets=[];integrity_gaps=[];committed=set()
for relative,data in cuts.items():
 rows=[json.loads(line) for line in data.splitlines()]
 root=payload/'formal' if relative.startswith('formal/attempts/') else payload/Path(relative).parent
 for row in rows:
  d=root/'requests'/row['id']
  committed.add(str(d.relative_to(payload)))
  for name,key in [('raw.json.gz','raw_sha256')]:
   f=d/name
   if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=row[key]:
    integrity_gaps.append({'records':relative,'id':row['id'],'artifact':name,'reason':'MISSING_OR_ORIGINAL_HASH_MISMATCH'})
  f=d/'request.json'
  if not f.exists():integrity_gaps.append({'records':relative,'id':row['id'],'artifact':'request.json','reason':'MISSING'})
  else:
   body=json.loads(f.read_text());digest=hashlib.sha256(json.dumps(body,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
   if digest!=row['request_sha256']:integrity_gaps.append({'records':relative,'id':row['id'],'artifact':'request.json','reason':'ORIGINAL_HASH_MISMATCH'})
 record_sets.append({'path':relative,'records':len(rows),'sha256':hashlib.sha256(data).hexdigest()})
uncommitted=sorted({str(f.parent.relative_to(payload)) for f in payload.rglob('request.json')
 if f.parent.parent.name=='requests' and str(f.parent.relative_to(payload)) not in committed})
manifest={'schema_version':1,'captured_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'source_root':str(source),
 'final':FINAL,'state_at_start':state,'guardian_at_start':watch,'files':index,'record_sets':record_sets,
 'original_integrity_gaps':integrity_gaps,'uncommitted_request_directories':uncommitted,
 'snapshot_semantics':'Complete record-stream prefixes; immutable committed request/raw files; other live files copied at their individual captured size. Source not stopped or mutated.'}
(payload/'SNAPSHOT-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=destination/'remote-evidence.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=1) as tar:tar.add(payload,arcname='remote')
print(json.dumps({'archive':str(archive),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
 'archive_bytes':archive.stat().st_size,'files':len(index),'record_sets':record_sets,'original_integrity_gaps':integrity_gaps,
 'state_at_start':state,'snapshot_manifest_sha256':hashlib.sha256((payload/'SNAPSHOT-MANIFEST.json').read_bytes()).hexdigest()}))
'''


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main(final=False):
    os.umask(0o077)
    label = ('final-' if final else 'snapshot-') + dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root = EVIDENCE/'backups'/label
    root.mkdir(parents=True, mode=0o700)
    code = 'LABEL='+repr(label)+'\nFINAL='+repr(final)+'\n'+REMOTE_CAPTURE
    result = subprocess.run(['ssh', '-oBatchMode=yes', '-oConnectTimeout=20', '29', 'python3 -'],
                            input=code, text=True, capture_output=True, timeout=600, check=True)
    remote = json.loads(result.stdout)
    (root/'remote-receipt.json').write_text(json.dumps(remote, indent=2)+'\n')
    print('Remote immutable snapshot created: '+label, flush=True)
    archive = root/'remote-evidence.tar.gz'
    subprocess.run(['scp', '-q', '29:'+remote['archive'], str(archive)], timeout=600, check=True)
    if digest(archive) != remote['archive_sha256']:
        raise RuntimeError('downloaded archive checksum mismatch')
    with tarfile.open(archive) as tar:
        tar.extractall(root, filter='data')
    remote_manifest = root/'remote/SNAPSHOT-MANIFEST.json'
    if digest(remote_manifest) != remote['snapshot_manifest_sha256']:
        raise RuntimeError('remote snapshot manifest changed')
    manifest = json.loads(remote_manifest.read_text())
    for entry in manifest['files']:
        if digest(root/'remote'/entry['path']) != entry['sha256']:
            raise RuntimeError('backup content changed: '+entry['path'])
    for source, name in [(REPO/'output/ninfer-baseline-29-20261020', 'score-evidence'),
                         (REPO/'output/ninfer-hyperqwen-v3-review-20261020', 'original-review-evidence'),
                         (REPO/'scripts/ninfer_baseline', 'scripts'),
                         (REPO/'docs/ninfer-hyperqwen-v3-md-20261019', 'design')]:
        shutil.copytree(source, root/'local'/name, ignore=shutil.ignore_patterns('__pycache__'))
    local_index = [{'path':str(f.relative_to(root/'local')), 'bytes':f.stat().st_size, 'sha256':digest(f)}
                   for f in sorted((root/'local').rglob('*')) if f.is_file()]
    (root/'LOCAL-MANIFEST.json').write_text(json.dumps(local_index, indent=2)+'\n')
    receipt = {'schema_version':1, 'label':label, 'root':str(root), 'final':final,
               'verified_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
               'remote_archive_sha256':remote['archive_sha256'], 'remote_files':remote['files'],
               'local_files':len(local_index), 'record_sets':remote['record_sets'],
               'original_integrity_gaps':remote['original_integrity_gaps'], 'backup_hash_verification':'PASS',
               'local_manifest_sha256':digest(root/'LOCAL-MANIFEST.json')}
    (root/'BACKUP-RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n')
    (EVIDENCE/'latest-backup.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({'root':str(root),'remote_files':remote['files'],'local_files':len(local_index),
                      'record_sets':remote['record_sets'],'original_integrity_gaps':len(remote['original_integrity_gaps']),
                      'backup_hash_verification':'PASS'}), flush=True)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--final', action='store_true')
    main(parser.parse_args().final)
