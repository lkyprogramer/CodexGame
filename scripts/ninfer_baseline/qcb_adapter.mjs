/** Frozen hidden graders are outside every agent-visible workspace. */
import {readFile,readdir,mkdir,writeFile,unlink} from 'node:fs/promises';
import {join,dirname,resolve,isAbsolute} from 'node:path';
import {createHash} from 'node:crypto';
export const QCB_IDS=['BF009','RE003','RE007','AT005','LC003'];
export const QCB_ROOT=join(dirname(new URL(import.meta.url).pathname),'../../docs/qwen38-coding-benchmark-4090-v1.0.0');
export const sha=x=>createHash('sha256').update(x).digest('hex');
export async function filesAt(root){const out={};async function walk(dir,p=''){for(const e of await readdir(dir,{withFileTypes:true})){if(e.isSymbolicLink())throw Error('Symlink forbidden');if(e.isDirectory())await walk(join(dir,e.name),p+e.name+'/');else if(e.isFile())out[p+e.name]=await readFile(join(dir,e.name));}}await walk(root);return out;}
export async function writeFiles(root,files){for(const [p,b]of Object.entries(files)){if(p.startsWith('/')||p.split('/').includes('..'))throw Error('Unsafe relative file');await mkdir(dirname(join(root,p)),{recursive:true});await writeFile(join(root,p),b,{mode:p==='verify.sh'?0o700:0o600});}}
export const PUBLIC_VERIFY=`#!/bin/bash
set -euo pipefail
build=$(mktemp -d)
trap 'rm -rf "$build"' EXIT
find src -name '*.java' -print0 | xargs -0 javac -encoding UTF-8 -d "$build"
echo 'PUBLIC_COMPILE_OK'
`;
export async function prepareQcb(root,id){
 const source=join(QCB_ROOT,'tasks',id);const files=await filesAt(join(source,'workspace'));
 files['TASK.md']=await readFile(join(source,'prompt.md'));files['verify.sh']=Buffer.from(PUBLIC_VERIFY);
 const hidden=await filesAt(join(source,'hidden_tests'));const helpers={'qcb/__init__.py':Buffer.from(''), 'qcb/verifier_helpers.py':await readFile(join(QCB_ROOT,'qcb/verifier_helpers.py'))};
 const grader=join(root,'private-graders','qcb-'+id);await writeFiles(grader,{...hidden,...helpers});
 return {id:'qcb-'+id,kind:'qcb',origin:'FROZEN_QCB_HIDDEN_VERIFIER',writable_prefix:'src/',grader,
  files:Object.fromEntries(Object.entries(files).map(([p,b])=>[p,sha(b)])),grader_files:Object.fromEntries(Object.entries({...hidden,...helpers}).map(([p,b])=>[p,sha(b)])),payload:files};
}
export function qcbJudge(verify,protectedOk,forbiddenExit){
 let result=null;try{const lines=verify.out.trim().split('\n');result=JSON.parse(lines.at(-1));}catch{}
 const completed=!!result&&typeof result.passed==='boolean'&&Number.isInteger(result.tests_total)&&result.tests_total>0&&Number.isInteger(result.tests_passed)&&result.tests_passed>=0&&result.tests_passed<=result.tests_total;
 return {completed,passed:completed&&verify.code===0&&!verify.timedOut&&result.passed===true&&result.tests_passed===result.tests_total&&!result.error&&protectedOk&&!forbiddenExit};
}
export async function freshGrade({runRoot,workspace,source,files,writablePrefix,grader,graderHashes,env,bounded,python='/usr/bin/python3'}){
 const clean=join(runRoot,'fresh-grader-workspace');await mkdir(clean);
 for(const [p,h]of Object.entries(files)){const b=await readFile(join(source,p));if(sha(b)!==h)throw Error('Frozen grading baseline mismatch');await writeFiles(clean,{[p]:b});}
 const patch=await filesAt(join(workspace,writablePrefix));
 for(const p of Object.keys(files)){if(p.startsWith(writablePrefix)&&p.endsWith('.java')&&!(p.slice(writablePrefix.length) in patch))await unlink(join(clean,p));}
 // Source-only overlay: no agent-generated class files, scripts, tests or cached outputs.
 for(const [p,b]of Object.entries(patch)){if(!p.endsWith('.java'))continue;await writeFiles(clean,{[writablePrefix+p]:b});}
 if(grader){for(const [p,h]of Object.entries(graderHashes)){if(sha(await readFile(join(grader,p)))!==h)throw Error('Hidden grader identity changed');}
  return bounded(python,[join(grader,'verify.py'),clean],{cwd:clean,env:{...env,PYTHONPATH:grader}},210000);
 }
 return bounded('/bin/bash',['verify.sh'],{cwd:clean,env},30000);
}
export const TRUSTED_RUNTIME_DEPENDENCIES=new Set([
 '/Users/luo/Documents/github/CodexGame/scripts/ninfer_baseline/external_java_prepare.py',
 '/opt/homebrew/opt/python@3.14/bin/python3.14',
 '/Users/luo/.local/bin/docker',
]);
export async function verifyGradeFiles(files,wrapper){
 if(!wrapper||!isAbsolute(wrapper)||(!wrapper.startsWith('/tmp/')&&!wrapper.startsWith('/private/tmp/'))||resolve(wrapper)!==wrapper)throw Error('Private grader wrapper must remain under /tmp');
 if(!files||typeof files!=='object'||Array.isArray(files)||!(wrapper in files))throw Error('External grader dependency manifest required');
 for(const [p,h]of Object.entries(files)){
  if(!isAbsolute(p)||resolve(p)!==p||((!p.startsWith('/tmp/')&&!p.startsWith('/private/tmp/'))&&!TRUSTED_RUNTIME_DEPENDENCIES.has(p))||!/^([a-f0-9]{64})$/.test(h))throw Error('Invalid private grader dependency identity');
  if(sha(await readFile(p))!==h)throw Error('External grader dependency changed');
 }
}
export async function prepareExternal(root,manifestPath){
 const manifest=JSON.parse(await readFile(manifestPath));const rows=[];
 for(const c of manifest.cases||[]){if(c.status!=='READY')continue;
  if(!/^[A-Za-z0-9_.-]+$/.test(c.case_id))throw Error('Unsafe external case ID');
  for(const p of [c.base_dir,c.prompt_file,c.grade_script])if(!p||(!p.startsWith('/private/tmp/')&&!p.startsWith('/tmp/')))throw Error('External private source must be under /tmp');
  await verifyGradeFiles(c.grade_files,c.grade_script);
  const payload=await filesAt(c.base_dir);if(Object.keys(payload).some(x=>x.startsWith('.git/')||x.startsWith('hidden_tests/')||x.startsWith('reference/')))throw Error('External agent baseline contains forbidden private directory');
  payload['TASK.md']=await readFile(c.prompt_file);const publicVerifier=join(dirname(new URL(import.meta.url).pathname),'public_verify.mjs');
  const shellQuote=s=>"'"+s.replaceAll("'","'\\''")+"'";
  payload['verify.sh']=Buffer.from('#!/bin/bash\nset -eu\nexec '+['/Users/luo/.nvm/versions/node/v22.19.0/bin/node',publicVerifier,root,c.case_id].map(shellQuote).join(' ')+'\n');
  const prefixes=c.environment?.production_prefixes||c.production_prefixes;
  if(!Array.isArray(prefixes)||!prefixes.length||prefixes.some(p=>typeof p!=='string'||p.startsWith('/')||p.split('/').includes('..')||!p.endsWith('/')))throw Error('External production prefixes required');
  await writeFiles(join(root,'fixtures',c.case_id),payload);
  rows.push({id:c.case_id,trustedGradeTimeoutMs:450000,base_commit:c.base_commit,public_verifier_sha256:sha(await readFile(publicVerifier)),kind:'external',origin:'FROZEN_SWE_BENCH_JAVA',writable_prefix:prefixes[0],writable_prefixes:prefixes,
    grade_files:c.grade_files,external_grade_script:c.grade_script,external_grade_sha256:sha(await readFile(c.grade_script)),environment:c.environment,
    preparation_manifest_sha256:sha(await readFile(manifestPath)),files:Object.fromEntries(Object.entries(payload).map(([p,b])=>[p,sha(b)]))});
 }
 return rows;
}
export async function externalGrade({runRoot,workspace,source,descriptor,env,bounded}){
 if(descriptor.grade_files)await verifyGradeFiles(descriptor.grade_files,descriptor.external_grade_script);
 if(sha(await readFile(descriptor.external_grade_script))!==descriptor.external_grade_sha256)throw Error('Frozen external grader changed');
 const stage=join(runRoot,'external-patch');await mkdir(stage);const base=await filesAt(source);
 await writeFiles(join(stage,'baseline'),base);await writeFiles(join(stage,'candidate'),base);
 for(const prefix of descriptor.writable_prefixes){const patch=await filesAt(join(workspace,prefix));for(const p of Object.keys(base))if(p.startsWith(prefix)&&p.endsWith('.java')&&!(p.slice(prefix.length) in patch))await unlink(join(stage,'candidate',p));for(const [p,b]of Object.entries(patch))if(p.endsWith('.java'))await writeFiles(join(stage,'candidate'),{[prefix+p]:b});}
 const diff=await bounded('/usr/bin/git',['diff','--no-index','--no-ext-diff','--src-prefix=a/','--dst-prefix=b/','baseline','candidate'],{cwd:stage,env},30000);
 if(diff.timedOut||![0,1].includes(diff.code))throw Error('Patch capture failed');
 const patch=diff.out.split('\n').map(line=>/^(diff --git |--- |\+\+\+ )/.test(line)?line.replaceAll('a/baseline/','a/').replaceAll('b/candidate/','b/'):line).join('\n');
 const path=join(runRoot,'candidate.patch');await writeFile(path,patch);
 return bounded('/bin/bash',[descriptor.external_grade_script,path],{cwd:runRoot,env},450000);
}
