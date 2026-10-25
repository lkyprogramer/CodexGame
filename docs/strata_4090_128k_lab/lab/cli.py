from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
from .core import ROOT, dump, load_config, sha256
from . import workspace


def verify_package():
    manifest=ROOT/'MANIFEST.sha256'
    if not manifest.exists(): return {'status':'BUILDING_PACKAGE'}
    bad=[]
    for line in manifest.read_text().splitlines():
        digest,name=line.split('  ',1);p=ROOT/name
        if not p.is_file() or sha256(p)!=digest:bad.append(name)
    if bad:raise RuntimeError('Package integrity failed: '+', '.join(bad))
    return {'status':'VERIFIED','files':len(manifest.read_text().splitlines())}


def main():
    ap=argparse.ArgumentParser(description='Strata single-4090 / 128K isolated PR laboratory')
    ap.add_argument('--config',default=str(ROOT/'config/local.json'))
    sub=ap.add_subparsers(dest='command',required=True)
    ini=sub.add_parser('init');ini.add_argument('--deployed-repo',required=True);ini.add_argument('--deployed-config',required=True)
    ini.add_argument('--gguf',required=True);ini.add_argument('--template',required=True);ini.add_argument('--python',default=sys.executable)
    sub.add_parser('verify');sub.add_parser('doctor');sub.add_parser('bootstrap');sub.add_parser('list');sub.add_parser('assets')
    st=sub.add_parser('selftest')
    qual=sub.add_parser('qualify');qual.add_argument('--pr',type=int,required=True)
    sc=sub.add_parser('scenario');sc.add_argument('--pr',type=int,required=True);sc.add_argument('--name',choices=('java-agent','preemption','reply-chain'),required=True);sc.add_argument('--execute',action='store_true')
    for cmd in ('prepare','ai','build','run','auto','noise'):
        x=sub.add_parser(cmd);x.add_argument('--pr',type=int,choices=[r['pr'] for r in json.loads((ROOT/'config/experiments.json').read_text())])
        if cmd in ('ai','run','auto','noise'):x.add_argument('--execute',action='store_true')
        if cmd in ('run','auto','noise'):
            x.add_argument('--suite',choices=('smoke','full'),default='smoke');x.add_argument('--groups',default='')
    co=sub.add_parser('corpus');co.add_argument('--suite',choices=('smoke','full'),default='smoke')
    ss=sub.add_parser('stats');ss.add_argument('--results',required=True)
    args=ap.parse_args()
    if args.command=='selftest':
        return subprocess.call([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT)
    if args.command=='verify':result=verify_package()
    elif args.command=='list':result=json.loads((ROOT/'config/experiments.json').read_text())
    elif args.command=='stats':
        from .statistics import summarize
        result=summarize(args.results)
    elif args.command=='init':
        target=Path(args.config).expanduser().resolve()
        if target.exists():raise RuntimeError('Refusing to overwrite an existing local configuration')
        c=json.loads((ROOT/'config/lab.example.json').read_text())
        for k in ('deployed_repo','deployed_config','gguf','template','python'):
            c[k]=str(Path(getattr(args,k)).expanduser().resolve())
        c['workspace']=str(ROOT/'workspace');dump(target,c)
        result={'created':str(target),'next':'doctor → bootstrap → prepare --pr <N> → AI TASK.md → build → run; production is untouched'}
    else:
        verify_package();c=load_config(args.config)
        if args.command=='doctor':result=workspace.inventory(c)
        elif args.command=='bootstrap':result=workspace.bootstrap(c)
        elif args.command=='assets':
            from .assets import snapshot
            result=snapshot(c)
        elif args.command=='qualify':
            from .eligibility import qualify
            result=qualify(c,args.pr)
        elif args.command=='scenario':
            if not args.execute:result={'state':'DRY_RUN','scenario':args.name,'pr':args.pr}
            else:
                from .scenarios import run_scenario
                result=run_scenario(c,args.pr,args.name)
        elif args.command=='prepare':
            if args.pr is None:raise ValueError('--pr is required')
            result=workspace.prepare(c,args.pr)
        elif args.command=='ai':
            if args.pr is None:raise ValueError('--pr is required')
            if not args.execute:result={'state':'DRY_RUN','next':f'ai --pr {args.pr} --execute','note':'Runs only the external agent argv configured by you.'}
            else:result=workspace.ai_port(c,args.pr)
        elif args.command=='build':result=workspace.build(c,args.pr)
        elif args.command in ('corpus','run','auto','noise'):
            if args.command in ('run','auto') and args.pr is None:raise ValueError('--pr is required')
            if args.command in ('run','auto','noise') and not args.execute:
                result={'state':'DRY_RUN','pr':args.pr,'suite':args.suite,'context_ceiling':131072,'execute_requires':'isolated reviewed port, explicit maintenance flag, idle RTX4090, enough RAM, valid corpus counter'}
            else:
                if args.command=='auto':
                    workspace.prepare(c,args.pr)
                    from .eligibility import qualify
                    eligibility=qualify(c,args.pr)
                    if eligibility['blocks']:
                        print(json.dumps(eligibility,ensure_ascii=False,indent=2));return 2
                    r=workspace.ai_port(c,args.pr)
                    if r.get('status')!='READY':print(json.dumps(r,ensure_ascii=False,indent=2));return 2
                    workspace.build(c);workspace.build(c,args.pr)
                    from .assets import snapshot,verify
                    if not (Path(c['workspace'])/'assets.json').exists():snapshot(c)
                    else:verify(c)
                from .corpus import build
                from .tokenizer import StrataCounter
                counter=StrataCounter(workspace.baseline_dir(c),c['gguf'],c['template'])
                corpus=build(counter,c['max_context'],suite=args.suite,root_target=int(c.get('root_target_tokens',24576)))
                p=Path(c['workspace'])/'corpora'/f'{args.suite}-{corpus["corpus_sha256"][:12]}.json';dump(p,corpus)
                result={'corpus':str(p),'cases':len(corpus['cases']),'sha256':corpus['corpus_sha256']}
                if args.command in ('run','auto','noise'):
                    from .runner import campaign
                    from .statistics import summarize
                    result=campaign(c,args.pr or 0,p,set(args.groups.split(',')) if args.groups else None,aa=args.command=='noise')
                    if result.get('results'):result['report']=summarize(result['results'])
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as e:
        print('LAB_BLOCKED: '+str(e),file=sys.stderr);raise SystemExit(2)
