"""CPU-only binding checks and explicit authorization overlay; no GPU launch."""
import copy
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path

R=Path(__file__).resolve().parent
Q=R.parent/'df01-d1q-v2-adapter-20261102'
spec=importlib.util.spec_from_file_location('bound_supervisor',R/'supervisor.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(p):return m.s.sha(p)
def write(name,value):
    with (R/name).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
positive=[]
for name in ['saved-n32.v2.json','saved-n2048.v2.json']:
    d=json.loads((Q/name).read_text());m.validate_v2_receipt(d);positive.append(name)
negative=[]
bad=json.loads((Q/'invalid.v2.json').read_text())
cases=[('nonfinite_probability',bad)]
base=json.loads((Q/'saved-n2048.v2.json').read_text())
for name,legacy,reason,hard in [('wrong_token','FAIL','selector token 6','FAIL'),('row_gate','FAIL','row cosine or norm','FAIL'),('fake_legacy_token','FAIL','selector token 6','PASS'),('missing_diagnostic','FAIL',base['legacy_reason'],'PASS')]:
    d=copy.deepcopy(base);d['legacy_v1_numeric_result']=legacy;d['legacy_reason']=reason;d['v2_hard_gates']['drafter_rows_tokens_probability_validity']=hard
    if name=='missing_diagnostic':d['v2_confidence_diagnostic']['threshold_exceeded']=False
    cases.append((name,d))
for name,d in cases:
    try:m.validate_v2_receipt(d)
    except AssertionError:negative.append(name)
    else:raise AssertionError('binding allowed hard failure: '+name)
write('BINDING_CPU_CHECKS.json',{'status':'PASS','positive':positive,'negative_rejected':negative,'no_GPU':True})
old=json.loads((Q/'AUTHORIZATION.json').read_text())
history=old['frozen_source_and_history_sha256'].copy()
for item in json.loads((Q/'RAW_MANIFEST.json').read_text())['files']:history[str(Q/item['path'])]=item['sha256']
expected=history.copy()
for p,h in json.loads((Q/'FINAL_FREEZE.json').read_text())['sha256'].items():
    if p in expected:assert expected[p]==h,p
    expected[p]=h
for p,h in old['protected_sha256'].items():
    if p in expected:assert expected[p]==h,p
    expected[p]=h
for p in [Q/'FINAL_FREEZE.json',Q/'RAW_MANIFEST.json',Q/'COMMANDS_V2.json',R/'supervisor.py',R/'bind_cpu.py',R/'BINDING_CPU_CHECKS.json']:expected[str(p)]=sha(p)
write('AUTHORIZATION.json',{'id':'DF01-D1S-V2-20261102','scope':'new D1 GPU authorization; v2 confidence diagnostic only; stop first hard failure; no retries/replacement; no D2; production KEEP_STOPPED','limits':{'qualification_programs':2,'fixtures':16,'generations':6,'GPU_window_seconds':3600},'GPU_work_seconds':3000,'service_control':'NONE','binding':str(Q/'FINAL_FREEZE.json'),'commands':str(Q/'COMMANDS_V2.json'),'expected_sha256':expected,'frozen_source_and_history_sha256':history,'protected_sha256':old['protected_sha256'],'CPU_model_forwards':0,'created_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
print(json.dumps({'status':'CPU_BINDING_PASS','positive':len(positive),'negative':len(negative),'frozen_files':len(expected),'GPU_started':0}),flush=True)
