from __future__ import annotations
import json, os, platform, shutil, subprocess, sys, time, urllib.request
from pathlib import Path
from .core import ROOT, dump, run, sha256, redact, check_separate, available_mib, gpu_inventory, argv


def lock(): return json.loads((ROOT/'sources/LOCK.json').read_text())
def experiment(pr):
    rows=json.loads((ROOT/'config/experiments.json').read_text())
    return next(x for x in rows if int(x['pr'])==int(pr))
def state_dir(c,pr): return Path(c['workspace'])/'state'/f'pr-{pr}'
def candidate_dir(c,pr): return Path(c['workspace'])/'trees'/f'pr-{pr}'
def baseline_dir(c): return Path(c['workspace'])/'trees'/'base'


def inventory(c):
    result={'observed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'platform':platform.platform(),
            'python':sys.version,'max_context':c['max_context'],'production_is_read_only':True,'checks':{}}
    for key in ('deployed_repo','deployed_config','gguf','template','python'):
        result['checks'][key]={'exists':Path(c[key]).exists(),'path':c[key]}
    for name,cmd in [('git',['git','--version']),('cmake',['cmake','--version']),('nvcc',['nvcc','--version']),('cpu',['lscpu'])]:
        try: result[name]=run(cmd,check=False).stdout
        except (OSError,subprocess.SubprocessError) as e: result[name]={'unavailable':str(e)}
    try: result['available_mib']=available_mib()
    except Exception as e: result['available_mib_error']=str(e)
    try: result['gpu']=gpu_inventory(c['gpu'])
    except Exception as e: result['gpu_error']=str(e)
    if Path(c['deployed_config']).is_file():
        cfg=json.loads(Path(c['deployed_config']).read_text(encoding='utf-8-sig'))
        result['deployed_config_sha256']=sha256(Path(c['deployed_config']))
        result['deployed_config_redacted']=redact(cfg)
    if (Path(c['deployed_repo'])/'.git').exists():
        result['deployed_git_head']=run(['git','rev-parse','HEAD'],cwd=c['deployed_repo']).stdout.strip()
        result['deployed_dirty']=run(['git','status','--porcelain'],cwd=c['deployed_repo']).stdout
    p=Path(c['workspace']); p.mkdir(parents=True,exist_ok=True)
    result['free_disk_gib']=shutil.disk_usage(p).free/2**30
    dump(p/'inventory.json',result)
    return result


def bootstrap(c):
    w=Path(c['workspace']);check_separate(w,c['deployed_repo']);w.mkdir(parents=True,exist_ok=True)
    if shutil.disk_usage(w).free<c['min_free_disk_gib']*2**30: raise RuntimeError('Insufficient free workspace disk')
    repo=w/'repo'
    if not repo.exists():
        run(['git','clone','--no-checkout','--no-hardlinks',c['deployed_repo'],str(repo)],timeout=600,log=w/'clone.log')
        run(['git','remote','set-url','origin',lock()['repository_git']],cwd=repo)
        run(['git','config','user.name','Strata Lab'],cwd=repo)
        run(['git','config','user.email','strata-lab@localhost'],cwd=repo)
    if not (repo/'.git').is_dir(): raise RuntimeError('Workspace repo is not an isolated normal clone')
    base=lock()['baseline_sha']
    if run(['git','cat-file','-e',base+'^{commit}'],cwd=repo,check=False).returncode:
        run(['git','fetch','--no-tags','origin',base],cwd=repo,timeout=600,log=w/'fetch-base.log')
    if not baseline_dir(c).exists():
        baseline_dir(c).parent.mkdir(parents=True,exist_ok=True)
        run(['git','worktree','add','--detach',str(baseline_dir(c)),base],cwd=repo,timeout=180)
    observed=run(['git','rev-parse','HEAD'],cwd=baseline_dir(c)).stdout.strip()
    if observed!=base: raise RuntimeError('Baseline tree drifted; refusing to rewrite it')
    return {'baseline':base,'tree':str(baseline_dir(c))}


def prepare(c,pr):
    bootstrap(c); e=experiment(pr);w=Path(c['workspace']); repo=w/'repo'; s=state_dir(c,pr);s.mkdir(parents=True,exist_ok=True)
    pin=e['head_sha']
    if run(['git','cat-file','-e',pin+'^{commit}'],cwd=repo,check=False).returncode:
        run(['git','fetch','--no-tags','https://github.com/'+e['fork']+'.git',pin],cwd=repo,timeout=600,log=s/'fetch-pr.log')
    run(['git','update-ref',f'refs/lab/pr-{pr}',pin],cwd=repo)
    base=lock()['baseline_sha']
    mb=run(['git','merge-base',base,pin],cwd=repo).stdout.strip()
    # Save the complete ORIGINAL feature delta for review, not an unsafe whole-branch merge.
    patch=run(['git','diff','--binary',mb,pin],cwd=repo,timeout=180).stdout
    (s/'upstream.patch').write_text(patch,encoding='utf-8')
    changes=run(['git','diff','--name-status',mb,pin],cwd=repo).stdout
    (s/'upstream-files.txt').write_text(changes,encoding='utf-8')
    history=run(['git','log','--oneline',mb+'..'+pin],cwd=repo).stdout
    (s/'upstream-commits.txt').write_text(history,encoding='utf-8')
    tree=candidate_dir(c,pr)
    if not tree.exists():
        run(['git','worktree','add','-b',f'lab/pr-{pr}',str(tree),base],cwd=repo,timeout=180)
    if run(['git','merge-base','--is-ancestor',base,'HEAD'],cwd=tree,check=False).returncode:
        raise RuntimeError('Candidate is not based on the frozen baseline')
    check=run(['git','apply','--check',str(s/'upstream.patch')],cwd=tree,check=False,timeout=120)
    (s/'apply-check.txt').write_text(check.stdout or 'git apply --check exit '+str(check.returncode),encoding='utf-8')
    doc=next((ROOT/'prs').glob(f'*PR{pr}.md'))
    task=(ROOT/'START_HERE_AI.md').read_text()+ '\n\n# 本轮任务\n\n'+doc.read_text()+f'''\n\n## 已准备的隔离路径\n- baseline: `{baseline_dir(c)}` @ `{base}`\n- candidate: `{tree}`\n- upstream head: `{pin}`\n- upstream delta: `{s/'upstream.patch'}`\n- git apply --check exit: {check.returncode}（仅提示，不代表语义兼容）\n- 交付 READY.json: `{s/'READY.json'}`，使用包内 templates/READY.example.json。\n不得在生产目录修改文件、停止生产服务或运行 GPU 压测。先移植、单测、提交，然后交回编排器。\n'''
    (s/'TASK.md').write_text(task,encoding='utf-8')
    dump(s/'prepared.json',{'pr':pr,'base':base,'head':pin,'merge_base':mb,'apply_check_exit':check.returncode,'state':'PREPARED'})
    return {'task':str(s/'TASK.md'),'candidate':str(tree),'state':'NEEDS_AI_PORT'}


def ai_port(c,pr):
    s=state_dir(c,pr)
    if not (s/'TASK.md').exists(): prepare(c,pr)
    if not c.get('agent_command'):
        return {'state':'NEEDS_AI_PORT','task':str(s/'TASK.md'),'reason':'No external coding-agent argv configured; provide TASK.md to your existing AI session.'}
    values={'task_file':str(s/'TASK.md'),'worktree':str(candidate_dir(c,pr)),'package':str(ROOT)}
    cmd=[x.format(**values) for x in argv(c['agent_command'])]
    # The user-chosen agent inherits credentials but we never log its command/environment.
    run(cmd,cwd=candidate_dir(c,pr),timeout=int(c.get('agent_timeout_s',14400)),log=s/'agent.log')
    return validate_ready(c,pr)


def validate_ready(c,pr):
    s=state_dir(c,pr);p=s/'READY.json'
    if not p.exists(): raise RuntimeError('NEEDS_AI_PORT: READY.json is missing')
    r=json.loads(p.read_text()); base=lock()['baseline_sha']; tree=candidate_dir(c,pr)
    if r.get('status') in ('NOT_APPLICABLE','ALREADY_UPSTREAM','NO_MECHANISM_BENEFIT','BLOCKED'):
        return r
    if r.get('status')!='READY' or not r.get('reviewed'): raise RuntimeError('Candidate not reviewed/READY')
    from .eligibility import qualify
    gate=qualify(c,pr)
    if gate['blocks']:raise RuntimeError('NOT_APPLICABLE_UNDER_CURRENT_PROFILE: '+'; '.join(gate['blocks']))
    if r.get('baseline_sha')!=base or r.get('pr_head_sha')!=experiment(pr)['head_sha']:
        raise RuntimeError('READY provenance differs from source lock')
    head=run(['git','rev-parse','HEAD'],cwd=tree).stdout.strip()
    if r.get('candidate_sha')!=head or head==base: raise RuntimeError('Candidate commit mismatch or no implementation')
    if run(['git','status','--porcelain','--untracked-files=no'],cwd=tree).stdout.strip(): raise RuntimeError('Candidate has uncommitted tracked changes')
    if run(['git','merge-base','--is-ancestor',base,head],cwd=tree,check=False).returncode: raise RuntimeError('Candidate does not descend from frozen base')
    for arm in ('off','on'):
        if not r.get('activation',{}).get(arm): raise RuntimeError('Missing positive feature activation receipt regex')
    if not r.get('unit_commands'): raise RuntimeError('No executed unit-test commands supplied')
    for i,cmd in enumerate(r['unit_commands']):
        # Commands are trusted, locally reviewed development commands, not model-produced tool calls.
        run(argv(cmd),cwd=tree,timeout=1800,log=s/f'unit-recheck-{i}.log')
    dump(s/'ready-verified.json',dict(r,verified_candidate_sha=head))
    return r


def build(c,pr=None):
    tree=baseline_dir(c) if pr is None else candidate_dir(c,pr)
    if not tree.exists(): raise RuntimeError('Prepare the worktree first')
    if available_mib()<c['min_available_mib']+1024: raise RuntimeError('Not enough free RAM to compile safely')
    flags=argv(c['cmake_args'])
    if any('CUDA_ARCHITECTURES=' in x and x.split('=',1)[1] not in ('89','89-real') for x in flags):
        raise RuntimeError('Build only sm_89 for this dedicated 4090 lab')
    if c.get('ggml_dir'): flags=flags+['-DSTRATA_GGML_DIR='+str(Path(c['ggml_dir']).expanduser().resolve())]
    b=tree/'build-lab'; logs=Path(c['workspace'])/'build-logs';logs.mkdir(parents=True,exist_ok=True)
    name='base' if pr is None else f'pr-{pr}'
    run(['cmake','-S',str(tree),'-B',str(b)]+flags,timeout=900,log=logs/(name+'-configure.log'))
    run(['cmake','--build',str(b),'--target','strata','--parallel',str(c['build_jobs'])],timeout=14400,log=logs/(name+'-build.log'))
    exe=b/'strata'
    if not exe.exists(): raise RuntimeError('Expected build-lab/strata is missing; inspect build outputs instead of guessing a binary')
    stamp={'source_sha':run(['git','rev-parse','HEAD'],cwd=tree).stdout.strip(),'exe':str(exe),'exe_sha256':sha256(exe),'flags':flags}
    dump(b/'LAB_BUILD.json',stamp)
    return stamp
