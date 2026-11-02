"""Check unchanged hard-gate expressions on CPU and seal a D1-only command set."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

R=Path(__file__).resolve().parent
B=R.parent/'df01-d0b-20261102'
N=R.parent/'df01-d1n-20261102'
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()
def write(name,value):
    with (R/name).open('x') as f: json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

with (R/'COMPLETION_ATTEMPT.json').open('x') as f: json.dump({'CPU_only':True},f)
assert json.loads((R/'CPU_CHECKS.json').read_text())['status']=='PASS'
source=(B/'state_qualification.hpp').read_text()
target=source[source.index('    auto check_logits='):source.index('    auto step=')]
source2=(R/'drafter_qualification.cpp').read_text()
begin=source2.index('    for(int i=0;i<N;++i)if(out[i]!=ref[i]')
end=source2.index(';',source2.index('throw std::runtime_error("isolated selector token/probability")',begin))+1
selector=source2[begin:end]
test=r'''#include "state_qualification.hpp"
#include <stdexcept>
struct FakeVerifier {std::vector<float> values{1,3,2};bool copy_logits(int,float* p){std::copy(values.begin(),values.end(),p);return true;}};
int main() {
    FakeVerifier ver;std::string error;
    struct Geometry {int n_vocab=3;} g;
    strata::kernels::SamplerParams active_params;active_params.greedy=true;
    auto check=[&](bool ok){if(!ok)throw std::runtime_error("copy");};
    using df01::target_pick;
    TARGET
    int controls=0;
    auto expect=[&](bool failure,auto call) {bool caught=false;try{call();}catch(const std::runtime_error&){caught=true;}if(caught!=failure)throw std::runtime_error("hard-gate control");++controls;};
    expect(false,[&]{check_logits(1,10,{1});});
    expect(true,[&]{check_logits(1,10,{0});});
    ver.values[0]=NAN;expect(true,[&]{check_logits(1,10,{1});});ver.values={1,3,2};
    active_params.greedy=false;active_params.temperature=1;active_params.top_k=3;active_params.top_p=.95f;active_params.seed=20261030;
    int correct=target_pick(ver.values,active_params,10);
    expect(false,[&]{check_logits(1,10,{correct});});
    expect(true,[&]{check_logits(1,10,{(correct+1)%3});});
    const int N=7;std::vector<int> out(N,1),ref(N,1);std::vector<float> p(N,.5f),prob(N,.5f);
    auto isolated=[&](){SELECTOR};
    expect(false,isolated);p[6]=.50002f;expect(true,isolated);p[6]=.5f;
    out[6]=2;expect(true,isolated);out[6]=1;p[6]=NAN;expect(true,isolated);
    std::printf("UNCHANGED_HARD_GATE_CPU_PASS %d controls; target and isolated-selector source blocks; no CUDA calls\n",controls);
}
'''.replace('TARGET',target).replace('SELECTOR',selector)
(R/'unchanged_hard_gate_test.cpp').write_text(test)
commands=[['g++','-O2','-std=c++20','-I'+str(B),'-I/home/hhtele/strata-lab-4090/workspace/trees/base/include','-I/usr/local/cuda-12.3/include',str(R/'unchanged_hard_gate_test.cpp'),'-o',str(R/'build/unchanged_hard_gate_test')],[str(R/'build/unchanged_hard_gate_test')]]
receipts=[]
for i,argv in enumerate(commands):
    p=subprocess.run(argv,cwd=R,text=True,capture_output=True,timeout=120)
    (R/f'hard-gate-{i}.stdout').write_text(p.stdout);(R/f'hard-gate-{i}.stderr').write_text(p.stderr)
    receipts.append({'argv':argv,'exit_code':p.returncode});assert p.returncode==0,(p.stdout,p.stderr)
cmd=json.loads((R/'COMMANDS.json').read_text())
cmd.pop('commands');cmd.pop('D2_generation_commands')
cmd['runner_status']='NOT_INSTALLED; requires separately authorized GPU budget and rebind to FINAL_FREEZE.json'
write('COMMANDS_V2.json',cmd)
auth=json.loads((R/'AUTHORIZATION.json').read_text())
for path,digest in {**auth['frozen_source_and_history_sha256'],**auth['protected_sha256']}.items():assert sha(path)==digest,path
frozen=json.loads((R/'FREEZE.json').read_text())['sha256']
for path,digest in frozen.items():assert sha(path)==digest,path
for p in list(R.iterdir())+list((R/'build').iterdir()):
    if p.is_file() and p.name not in ['FINAL_FREEZE.json']:frozen[str(p)]=sha(p)
write('FINAL_FREEZE.json',{'status':'FROZEN_CPU_ADAPTER_NOT_D1_QUALIFIED','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':frozen,'commands':str(R/'COMMANDS_V2.json'),'original_four_reference_identity':'D1N unchanged','GPU_authorized':False,'D1_qualified':False})
service=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show','openclaw-qwen38-next.service','-p','MainPID','-p','NRestarts','-p','ActiveState','-p','SubState'],text=True).splitlines())
assert service['MainPID']=='0' and service['ActiveState']=='inactive' and service['SubState']=='dead'
assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
ports={}
for port in [18343,18089]:
    ports[str(port)]=bool(subprocess.check_output(['ss','-Hltn','sport = :'+str(port)],text=True).strip());assert not ports[str(port)]
write('FINAL_READBACK.json',{'status':'PASS','utc':dt.datetime.now(dt.timezone.utc).isoformat(),'service':service,'ports':ports,'GPU_compute_apps':[],'protected_files_verified':len(auth['protected_sha256']),'historical_files_verified':len(auth['frozen_source_and_history_sha256']),'final_frozen_files':len(frozen)})
write('RESULT.json',{'status':'CPU_V2_ADAPTER_PREPARED','classification':'only complete-drafter confidence absolute difference is diagnostic','original_FAIL_preserved':True,'four_D1N_references_unchanged':True,'v2_adapter':'BUILT_CPU_TESTED_FROZEN_NOT_GPU_EXECUTED','hard_gate_source_block_controls':receipts,'GPU_programs':0,'model_forwards':0,'generations':0,'service_starts':0,'service_stops':0,'D1_qualified':False,'GPU_hard_gates':'NOT_RUN','D2':'NOT_RUN','production':'INACTIVE_DEAD_KEEP_STOPPED','frozen_files':len(frozen),'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
print(json.dumps({'status':'CPU_V2_ADAPTER_PREPARED','frozen_files':len(frozen),'GPU':0,'D1_qualified':False}),flush=True)
