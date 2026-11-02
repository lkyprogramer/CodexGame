"""Build/freeze the isolated v2 adapter. Never execute CUDA-linked programs."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

R = Path(__file__).resolve().parent
P = R.parent / 'df01-d1p-contract-20261102'
N = R.parent / 'df01-d1n-20261102'
B = R.parent / 'df01-d0b-20261102'
L = R.parent / 'df01-d1l-20261102'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def write(name, value):
    with (R/name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def run(label, argv, cwd=None, expected=0):
    p = subprocess.run(argv, cwd=cwd or R, capture_output=True, text=True, timeout=180)
    (R/(label+'.stdout')).write_text(p.stdout)
    (R/(label+'.stderr')).write_text(p.stderr)
    receipts.append({'name':label,'argv':list(map(str,argv)),'cwd':str(cwd or R),'exit_code':p.returncode,'expected':expected})
    assert p.returncode == expected, (label, p.returncode, p.stdout, p.stderr)
    return p

old = json.loads((P/'AUTHORIZATION.json').read_text())
history = old['frozen_source_and_history_sha256'].copy()
for item in json.loads((P/'RAW_MANIFEST.json').read_text())['files']:
    history[str(P/item['path'])] = item['sha256']
for path, digest in {**history, **old['protected_sha256']}.items():
    assert sha(path) == digest, path
service_cmd = ['systemctl','show','openclaw-qwen38-next.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','SubState']
service = dict(line.split('=',1) for line in subprocess.check_output(service_cmd,text=True).splitlines())
assert service['MainPID']=='0' and service['ActiveState']=='inactive' and service['SubState']=='dead'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
write('AUTHORIZATION.json', {'scope':'D1 v2 minimal classification adaptation, CPU controls and identity freeze only','GPU_programs':0,'model_forwards':0,'generations':0,'D1_qualified':False,'D2':False,'production':'KEEP_STOPPED','protected_sha256':old['protected_sha256'],'frozen_source_and_history_sha256':history,'service':service,'started_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
receipts = []
(R/'build').mkdir()
for name in ['qualification_compare.hpp','qualification_observation.hpp','drafter_qualification.cpp']:
    shutil.copy2(N/name,R/name)
source = (R/'drafter_qualification.cpp').read_text()
source = source.replace('#include "qualification_compare.hpp"','#include "qualification_v2.hpp"',1)
begin = source.index('    if(!df01_compare(rows,ref,actual.data()')
end = source.index('    ck(cudaFree(dt));',begin)
replacement = '''    const auto result = df01_compare_v2(rows,ref,actual.data(),tokens.data(),ap.data(),probs.data(),vocab);
    const std::string observation = std::filesystem::path(path).filename().string() + ".v2-observed.bin";
    if (!df01_write_observation(observation,rows,actual.data(),ap.data(),err)) throw std::runtime_error(err);
    if (!df01_write_v2(observation + ".json",result)) throw std::runtime_error("v2 receipt write");
    if (!result.hard_pass) throw std::runtime_error(path + std::string(": ") + result.hard_reason);
    if (result.confidence_difference) std::fprintf(stderr,"DF01 v2 confidence diagnostic: %s; legacy=%s\\n",path,result.legacy_pass?"PASS":"FAIL");
'''
adapted = source[:begin]+replacement+source[end:]
(R/'drafter_qualification.cpp').write_text(adapted)
legacy_source = (N/'drafter_qualification.cpp').read_text()
assert adapted[adapted.index('static void selector('):adapted.index('static void run_case(')] == legacy_source[legacy_source.index('static void selector('):legacy_source.index('static void run_case(')]
write('ADAPTATION.json', {'only_changed':['include v2 comparator','full-drafter comparison, observation and diagnostic receipt block'],'isolated_selector_byte_identical':True,'legacy_comparator_sha256':sha(R/'qualification_compare.hpp'),'legacy_comparator_unchanged':sha(R/'qualification_compare.hpp')==sha(N/'qualification_compare.hpp'),'target_state_binary_unchanged':True,'nonzero_exit_handling':'original supervisor assert p.returncode == 0 retained; this task installs no GPU runner'})
for name in ['adapter_controls','replay_saved']:
    run(name+'-compile',['g++','-O2','-std=c++20','-Wall','-Wextra',str(R/(name+'.cpp')),'-o',str(R/'build'/name)])
run('adapter-controls',[str(R/'build/adapter_controls')])
control=json.loads((R/'control.v2.json').read_text()); invalid=json.loads((R/'invalid.v2.json').read_text())
assert control['legacy_v1_numeric_result']=='FAIL' and control['v2_hard_gates']['drafter_rows_tokens_probability_validity']=='PASS'
assert invalid['v2_hard_gates']['drafter_rows_tokens_probability_validity']=='FAIL' and invalid['v2_confidence_diagnostic']['values'][6]['actual'] is None
assert control['D1_v2_qualified'] is False and invalid['D1_v2_qualified'] is False
refs=json.loads((N/'REFERENCES.json').read_text()); assert len(refs['fixtures'])==4
for x in refs['fixtures']:
    assert sha(x['fixture'])==x['fixture_sha256']
    assert sha(N/f"reference-n{x['context']}.bin")==x['reference_sha256']
write('REFERENCES.json', refs)
for context, observed in [(32,L/'drafter-n32-seed1.df01-observed.bin'),(2048,N/'drafter-n2048-seed2.bin.df01-observed.bin')]:
    x=next(x for x in refs['fixtures'] if x['context']==context)
    run('saved-n'+str(context),[str(R/'build/replay_saved'),str(observed),str(N/f'reference-n{context}.bin'),x['fixture'],str(R/f'saved-n{context}.v2.json')])

# Reuse the real host hard-gate controls. These binaries have no CUDA calls.
run('state-sampler-controls',[str(B/'build/state_compare_test')])
for mode in ['none','first','middle','bad_output','bad_commit']:
    run('EOS-'+mode,[str(B/'build/cli_termination_test'),mode],expected=1 if mode.startswith('bad') else 0)
# Program errors remain hard failures, irrespective of any confidence receipt.
runner=(N/'supervisor.py').read_text()
assert "assert p.returncode == 0, 'NATIVE_PROGRAM_FAILURE'" in runner
assert "assert marker in stdout, 'INCOMPLETE_FIXTURE_RECEIPT'" in runner

# CPU compilation/linking only. Never load or run this CUDA-linked executable.
build=json.loads((B/'QUALIFICATION_BUILD.json').read_text())
for label in ['drafter_qualification-compile','drafter_qualification-link']:
    old_cmd=next(c for c in build['commands'] if c['name']==label)
    argv=[v.replace(str(B),str(R)) for v in old_cmd['argv']]
    run(label,argv,cwd=old_cmd['cwd'].replace(str(B),str(R)))

commands=json.loads((N/'COMMANDS.json').read_text())
commands['qualification_programs'][0]['argv'][0]=str(R/'build/drafter_qualification')
commands['status']='FROZEN_CPU_PREPARED_GPU_NOT_AUTHORIZED'
commands['execute']=False
commands['execution_budget']={'GPU_programs':0,'generations':0,'new_GPU_authorization_required':True}
for c in commands['qualification_programs']+commands['D1_generation_commands']: c['execute']=False
assert len(commands['qualification_programs'])==2 and sum(c['fixtures'] for c in commands['qualification_programs'])==16 and len(commands['D1_generation_commands'])==6
assert not any(k in commands['env'] for k in ['STRATA_SPEC_PROB','STRATA_SPEC_COUPLED','STRATA_SPEC_GATE_PICK','STRATA_SPEC_GUMBEL','STRATA_SPEC_COST'])
write('COMMANDS.json',commands)
frozen=json.loads((N/'FREEZE.json').read_text())['sha256'].copy()
for p,h in frozen.items(): assert sha(p)==h,p
for p in R.iterdir():
    if p.is_file() and p.suffix in ['.py','.cpp','.hpp','.json']: frozen[str(p)]=sha(p)
for p in (R/'build').iterdir():
    if p.is_file(): frozen[str(p)]=sha(p)
write('FREEZE.json',{'status':'FROZEN_CPU_ONLY_GPU_NOT_AUTHORIZED','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':frozen,'original_four_references_unchanged':True,'D1_qualified':False})
write('CPU_CHECKS.json',{'status':'PASS','commands':receipts,'original_four_reference_SHA_match':True,'saved_replays':2,'GPU_programs':0,'model_forwards':0,'generations':0,'D1_qualified':False,'GPU_hard_gates':'NOT_RUN','D2':'NOT_RUN','finished_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
print(json.dumps({'status':'CPU_ADAPTER_PREPARATION_PASS','commands':len(receipts),'frozen_files':len(frozen),'D1_qualified':False,'GPU':0}),flush=True)
