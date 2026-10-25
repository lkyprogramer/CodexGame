#!/usr/bin/env node
/** Public compile only. Never imports the hidden grading implementation or test patch. */
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {join,resolve} from 'node:path';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {filesAt,writeFiles} from './qcb_adapter.mjs';
export function compileCommand(id){
 if(id==='google__gson-2158')return ['mvnd','-o','-B','-T','1','-pl','gson','-Dmaven.test.skip=true','compile'];
 if(id==='javaparser__javaparser-4561')return ['./mvnw','-o','-B','-pl','javaparser-symbol-solver-core','-am','-Dmaven.test.skip=true','compile'];
 throw Error('No frozen public compiler for this repository');
}
const quote=s=>"'"+s.replaceAll("'","'\\''")+"'";
async function child(command,args,env,cwd,relay=true){return new Promise((ok,reject)=>{const p=spawn(command,args,{env,cwd,stdio:['ignore','pipe','pipe']});let out='',err='';p.stdout.on('data',x=>{out+=x;if(relay)process.stdout.write(x);});p.stderr.on('data',x=>{err+=x;if(relay)process.stderr.write(x);});p.on('error',reject);p.on('close',(code,signal)=>ok({code,signal,out,err}));});}
export async function publicVerify(root,id,workspace){
 root=resolve(root);workspace=resolve(workspace||'');
 if(!root.startsWith('/private/tmp/')&&!root.startsWith('/tmp/'))throw Error('Private run root required');
 if(!workspace.startsWith(join(root,'runs',id)+ '/')||!workspace.endsWith('/workspace'))throw Error('Workspace identity mismatch');
 const manifest=JSON.parse(await readFile(join(root,'manifest.json')));const c=manifest.cases.find(x=>x.id===id&&x.kind==='external');
 if(!c)throw Error('Unknown external descriptor');
 const image=c.environment?.pinned_image,base=c.base_commit,host=c.environment?.docker_host;
 if(!/^swebench\/[^\s]+@sha256:[a-f0-9]{64}$/.test(image||'')||!(/^[a-f0-9]{40}$/.test(base||''))||host!=='unix:///Users/luo/.orbstack/run/docker.sock')throw Error('Public compile identity unavailable');
 const command=compileCommand(id);const evidence=join(workspace,'..','public-verification',String(Date.now()));await mkdir(evidence,{recursive:true,mode:0o700});
 const original=await filesAt(join(root,'fixtures',id));const candidate={...original};
 for(const prefix of c.writable_prefixes){const changed=await filesAt(join(workspace,prefix));for(const p of Object.keys(original))if(p.startsWith(prefix)&&p.endsWith('.java'))delete candidate[p];for(const [p,b]of Object.entries(changed))if(p.endsWith('.java'))candidate[prefix+p]=b;}
 await writeFiles(join(evidence,'baseline'),original);await writeFiles(join(evidence,'candidate'),candidate);
 const env={PATH:'/usr/bin:/bin',HOME:evidence,DOCKER_CONFIG:join(evidence,'docker-config')};await writeFiles(env.DOCKER_CONFIG,{'config.json':Buffer.from('{}\n')});
 const diff=await child('/usr/bin/git',['diff','--no-index','--no-ext-diff','--src-prefix=a/','--dst-prefix=b/','baseline','candidate'],env,evidence,false);
 if(![0,1].includes(diff.code))throw Error('Public source patch failed');
 const patch=diff.out.split('\n').map(line=>/^(diff --git |--- |\+\+\+ )/.test(line)?line.replaceAll('a/baseline/','a/').replaceAll('b/candidate/','b/'):line).join('\n');
 await writeFile(join(evidence,'candidate.patch'),patch);
 const script=['#!/bin/bash','set -euo pipefail','cd /testbed','git config --global --add safe.directory /testbed',`git reset --hard ${base}`,'git clean -fd',
 'if test -s /public/candidate.patch; then git apply /public/candidate.patch; fi',command.map(quote).join(' '),"echo PUBLIC_COMPILE_OK"].join('\n')+'\n';
 await writeFile(join(evidence,'compile.sh'),script);
 const name='ninfer-public-'+createHash('sha256').update(evidence).digest('hex').slice(0,16);const docker='/Users/luo/.local/bin/docker';let result;
 try{result=await child(docker,['--host',host,'run','--rm','--pull=never','--network','none','--cpus','4','--memory','6g','--name',name,'--platform','linux/amd64',
 '--label','ninfer.public-compile=true','-v',`${evidence}:/public:ro`,'--entrypoint','/bin/bash',image,'-c','exec timeout -k 5s 120s /bin/bash /public/compile.sh'],env,evidence);}
 finally{await child(docker,['--host',host,'rm','-f',name],env,evidence,false);}
 const receipt={schema_version:1,scope:'PUBLIC_OFFLINE_COMPILE_ONLY_NO_HIDDEN_TESTS',case_id:id,image,base_commit:base,command,network:'none',timeout_seconds:120,exit_code:result.code,signal:result.signal,
 patch_sha256:createHash('sha256').update(patch).digest('hex')};await writeFile(join(evidence,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify({public_compile:result.code===0?'PASS':'FAIL_OR_ENVIRONMENT_UNAVAILABLE',hidden_tests_run:false,exit_code:result.code}));return result.code===0?0:1;
}
if(process.argv[1]&&resolve(process.argv[1])===new URL(import.meta.url).pathname){try{process.exitCode=await publicVerify(process.argv[2],process.argv[3],process.env.BASELINE_WORKSPACE);}catch(error){console.error('PUBLIC_COMPILE_UNAVAILABLE: '+error.message);process.exitCode=1;}}
