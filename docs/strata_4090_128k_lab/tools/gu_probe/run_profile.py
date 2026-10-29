"""Observe complete-config CPU misses, then optionally capture one frozen dtype."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools/combination'))
import run_boundaries as boundary
from boundary_memory import MemorySampler
from lab.assets import verify as verify_assets
from lab.core import dump,gpu_lock,hash_obj,load_config
from lab.tokenizer import StrataCounter
from profile import read_profile


def run(args):
    c=load_config(args.config);tree=Path(args.tree).resolve();out=Path(args.out).resolve()
    combo=boundary.combo
    if c['port']!=18089 or c['max_context']!=131072:raise ValueError('PROFILE_PROTECTION_MISMATCH')
    protected=combo.protected_hashes(c);combo.assert_service_inactive();verify_assets(c)
    receipt=json.loads((tree/'build-lab/LAB_BUILD.json').read_text())
    if hashlib.sha256((tree/'build-lab/strata').read_bytes()).hexdigest()!=receipt['exe_sha256']:
        raise RuntimeError('PROFILE_BINARY_CHANGED')
    corpus=json.loads(Path(args.corpus).read_text())
    if hash_obj(corpus['cases'])!=corpus['corpus_sha256']:raise ValueError('PROFILE_CORPUS_IDENTITY')
    out.mkdir(parents=True,exist_ok=False)
    env={'STRATA_LAB_GU_PROFILE':str(out/'profile.bin')}
    if args.capture_type is not None:
        (out/'fixtures').mkdir();env.update(STRATA_LAB_GU_CAPTURE=str(out/'fixtures'),
                                          STRATA_LAB_GU_CAPTURE_TYPE=str(args.capture_type))
    ready={'common':{'env':env}}
    dump(out/'plan.json',{'mode':'capture' if args.capture_type is not None else 'selection',
                         'source_receipt':receipt,'corpus':corpus['corpus_sha256'],'env':env})
    dump(out/'production-before.json',{'service':combo.assert_service_inactive(),'hashes':protected})
    os.environ.update(STRATA_PRESERVE_THINKING='0',STRATA_REPLY_REUSE='1')
    counter=StrataCounter(tree,c['gguf'],c['template']);server=combo.OwnedServer(c,tree,'cfg',ready,out)
    a=None;error=None
    with gpu_lock(c.get('gpu_lock_workspace',c['workspace'])):
        try:
            dump(out/'cooldown.json',combo.wait_cool(c))
            with MemorySampler(out,lambda:boundary.descendants(server)) as memory:
                try:
                    server.__enter__();dump(out/'activation.json',combo.validate_startup(server,'cfg'))
                    if 'LAB_GU_PROFILE version=1' not in (out/'engine.log').read_text():raise RuntimeError('PROFILE_NOT_ACTIVATED')
                    a=boundary.Arm(c,server,counter,out,memory)
                    q={'model':'strata','messages':[{'role':'user','content':'Return only OK.'}],
                       'max_tokens':32,'temperature':0,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False}}
                    a.request('qualification',q,'OK');boundary.wait_idle(server,out,'qualification')
                    shutil.copy2(out/'profile.bin',out/'qualification.profile.bin')
                    for case in corpus['cases']:
                        a.request(case['id'],copy.deepcopy(case['body']))
                        boundary.wait_idle(server,out,case['id'])
                        shutil.copy2(out/'profile.bin',out/(case['id']+'.profile.bin'))
                        dump(out/(case['id']+'.profile.json'),read_profile(out/'profile.bin'))
                finally:
                    server.__exit__(None,None,None);combo.wait_released(c)
        except BaseException as e:
            error=str(e)
            if not isinstance(e,Exception):raise
        finally:
            dump(out/'production-after.json',{'service':combo.assert_service_inactive(),'hashes':combo.assert_protected(c,protected)})
            dump(out/'result.json',{'error':error,'abort_reason':server.abort_reason,'requests':a.rows if a else []})
    if error:raise RuntimeError(error)
    result=read_profile(out/'profile.bin');dump(out/'profile.json',result)
    return {'state':'COMPLETE','requests':len(a.rows),'selected_type_including_qualification':result['selected_type'],
            'note':'Subtract qualification snapshot before freezing dtype; profile time is not performance evidence.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['config','tree','corpus','out']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--capture-type',type=int)
    print(json.dumps(run(parser.parse_args()),indent=2),flush=True)
