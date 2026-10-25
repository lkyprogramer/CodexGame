#!/usr/bin/env node
/** Fresh, bounded Java fixture benchmark. No historical sessions/config are loaded. */
import {mkdir,writeFile,readFile,realpath,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {resolve,join,dirname} from 'node:path';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {QCB_IDS,prepareQcb,writeFiles,filesAt,freshGrade,qcbJudge,prepareExternal,externalGrade} from './qcb_adapter.mjs';
export const PROFILE='ISOLATED_PI_FIXTURE';
export const PI_ROOT='/Users/luo/.nvm/versions/node/v22.19.0/lib/node_modules/@earendil-works/pi-coding-agent';
export const NODE='/Users/luo/.nvm/versions/node/v22.19.0/bin/node';
const sha=x=>createHash('sha256').update(x).digest('hex');
export const SEEDS=[1701,2901,4101];
export const NAVIGATION_BINARIES={rg:'/opt/homebrew/bin/rg',fd:'/Users/luo/.pi/agent/bin/fd'};
export const JAVA_ROOT='/Users/luo/.sdkman/candidates/java/25.0.1-open';
export const FIXTURE_ROOT=join(dirname(new URL(import.meta.url).pathname),'fixtures');
export const CASES=(await readdir(FIXTURE_ROOT,{withFileTypes:true})).filter(x=>x.isDirectory()).map(x=>({id:x.name,origin:x.name.startsWith('java-agent-')?'REUSED_EXISTING_BUSINESS_FIXTURE':'SYNTHETIC_BUSINESS_CONTRACT'})).sort((a,b)=>a.id.localeCompare(b.id));
async function treeFiles(root) {
 const out={}; async function walk(dir,prefix=''){for(const e of await readdir(dir,{withFileTypes:true})){const n=prefix+e.name;if(e.isDirectory())await walk(join(dir,e.name),n+'/');else if(e.isFile())out[n]=await readFile(join(dir,e.name),'utf8');else throw Error('Fixture symlink forbidden');}}
 await walk(root);return out;
}
export async function fixtureFiles(c){return treeFiles(join(FIXTURE_ROOT,c.id));}
export const EXTENSION=`import {appendFileSync} from 'node:fs';
import {resolve} from 'node:path';
export default function(pi) {
 let turns=0,tools=0;
 function stop(ctx,reason) { appendFileSync(process.env.BASELINE_BUDGET_LOG,JSON.stringify({kind:'hard_budget',reason,turns,tools})+'\\n'); ctx.abort(); return {block:true,reason}; }
 function deny(reason) { appendFileSync(process.env.BASELINE_BUDGET_LOG,JSON.stringify({kind:'policy_denial',reason,turns,tools})+'\\n'); return {block:true,reason:reason+'; retry with enabled read/grep/find/ls, edit/write allowed production sources, or bash command exactly ./verify.sh. Ordinary rejection does not stop this task.'}; }
 pi.on('turn_start',(_event,ctx)=> { if(++turns>Number(process.env.BASELINE_MAX_TURNS)) stop(ctx,'TURN_BUDGET'); });
 pi.on('tool_call',(event,ctx)=> {
  if(++tools>Number(process.env.BASELINE_MAX_TOOLS)) return stop(ctx,'TOOL_BUDGET');
  const root=process.env.BASELINE_WORKSPACE;
  if(event.toolName==='bash') {
   if(!['./verify.sh','bash verify.sh'].includes(event.input.command?.trim())) return deny('BASH_NOT_ALLOWLISTED');
   return;
  }
  const navigation=process.env.BASELINE_NAVIGATION==='1'&&['grep','find','ls'].includes(event.toolName);
  if(!['read','edit','write'].includes(event.toolName)&&!navigation) return deny('TOOL_NOT_ALLOWLISTED');
  const path=resolve(root,event.input.path||'.');
  if(path!==root&&!path.startsWith(root+'/')) return deny('PATH_OUTSIDE_FIXTURE');
  const prefixes=JSON.parse(process.env.BASELINE_WRITE_PREFIXES||JSON.stringify([process.env.BASELINE_WRITE_PREFIX||'src/main/']));
  if(!navigation&&event.toolName!=='read' && !prefixes.some(prefix=>path.startsWith(root+'/'+prefix))) return deny('PROTECTED_FILE');
 });
}`;
function tmpPath(p) { const r=resolve(p);if(!r.startsWith('/tmp/')&&!r.startsWith('/private/tmp/'))throw Error('Output and workspace must be under /tmp');return r; }
async function json(p,v){await writeFile(p,JSON.stringify(v,null,2)+'\n');}
export async function prepare(root,mode='full') {
 root=tmpPath(root); await mkdir(root,{recursive:true,mode:0o700}); root=tmpPath(await realpath(root));
 if(CASES.length!==20)throw Error('Expected frozen 20-case business corpus');
 const rows=[];
 for(const c of (mode==='slim'?CASES.filter(x=>x.id.startsWith('java-agent-')):CASES)){const files=await fixtureFiles(c),dir=join(root,'fixtures',c.id);await mkdir(dir,{recursive:true});for(const [n,s]of Object.entries(files)){await mkdir(dirname(join(dir,n)),{recursive:true});await writeFile(join(dir,n),s,{mode:n==='verify.sh'?0o700:0o600});}rows.push({id:c.id,origin:c.origin,files:Object.fromEntries(Object.entries(files).map(([n,s])=>[n,sha(s)]))});}
 if(mode==='slim')for(const id of QCB_IDS){const row=await prepareQcb(root,id);await writeFiles(join(root,'fixtures',row.id),row.payload);delete row.payload;rows.push(row);}
 await writeFile(join(root,'budget.mjs'),EXTENSION);
 const manifest={schema_version:1,profile:PROFILE,equivalent_to_historical_sol_pi:false,mode,case_count:rows.length,repetitions:mode==='slim'?1:3,seeds:mode==='slim'?[1701]:SEEDS,cases:rows,extension_sha256:sha(EXTENSION)};
 await json(join(root,'manifest.json'),manifest);return manifest;
}
export async function addExternal(root,path){const manifest=JSON.parse(await readFile(join(root,'manifest.json')));const rows=await prepareExternal(root,path);for(const row of rows)if(!manifest.cases.some(c=>c.id===row.id))manifest.cases.push(row);manifest.case_count=manifest.cases.length;await json(join(root,'manifest.json'),manifest);return rows;}
export function parseEvents(raw) {
 const result={assistant_turns:0,usage_observations:0,tool_calls:0,tool_by_name:{},usage:{input:0,output:0,cacheRead:0,cacheWrite:0,totalTokens:0},cost:{input:0,output:0,cacheRead:0,cacheWrite:0,total:0},errors:[],invalid_lines:0,assistant_stop_reasons:[]};
 for(const line of raw.split('\n').filter(Boolean)){let e;try{e=JSON.parse(line);}catch{result.invalid_lines++;continue;}
 if(e.type==='tool_execution_start'){result.tool_calls++;const n=e.toolName||e.name||'?';result.tool_by_name[n]=(result.tool_by_name[n]||0)+1;}
 if(e.type==='message_end'&&e.message?.role==='assistant'){result.assistant_turns++;if(e.message.usage)result.usage_observations++;for(const k of Object.keys(result.usage))result.usage[k]+=Number(e.message.usage?.[k]||0);for(const k of Object.keys(result.cost))result.cost[k]+=Number(e.message.usage?.cost?.[k]||0);result.assistant_stop_reasons.push(e.message.stopReason||null);if(e.message.errorMessage)result.errors.push(e.message.errorMessage);}
 }return result;
}
export function classifyPolicyEvents(raw){const denials=[],hard=[];for(const line of raw.split('\n').filter(Boolean)){let e;try{e=JSON.parse(line);}catch{hard.push({reason:'MALFORMED_POLICY_EVENT'});continue;}if(e.kind==='policy_denial')denials.push(e);else hard.push(e);}return {denials,hard};}
export function judgeVerification(id,verify,protectedOk,forbiddenExit){
 const marker=id.startsWith('java-agent-1')?'PASS OrderServiceTest':id.startsWith('java-agent-2')?'PASS RetryingClientTest':id.startsWith('java-agent-3')?'PASS ReconnectCoordinatorTest':'PASS '+id;
 const completed=verify.out.split('\n').includes(marker);
 return {completed,passed:verify.code===0&&!verify.timedOut&&completed&&protectedOk&&!forbiddenExit};
}
export function minimalEnv(root,workspace,maxTurns,maxTools){return {PATH:`${dirname(NODE)}:${JAVA_ROOT}/bin:/opt/homebrew/bin:/Users/luo/.pi/agent/bin:/usr/bin:/bin:/usr/sbin:/sbin`,HOME:join(root,'home'),TMPDIR:join(root,'tmp'),LANG:'en_US.UTF-8',PI_CODING_AGENT_DIR:join(root,'agent'),PI_OFFLINE:'1',PI_SKIP_VERSION_CHECK:'1',PI_TELEMETRY:'0',BASELINE_WORKSPACE:workspace,BASELINE_BUDGET_LOG:join(root,'budget-events.jsonl'),BASELINE_MAX_TURNS:String(maxTurns),BASELINE_MAX_TOOLS:String(maxTools)};}
export async function bounded(command,args,options,timeoutMs){return new Promise((ok,reject)=>{let out='',err='',timedOut=false;const start=performance.now();const child=spawn(command,args,{...options,detached:true,stdio:['ignore','pipe','pipe']});child.stdout.on('data',x=>out+=x);child.stderr.on('data',x=>err+=x);child.on('error',reject);const timer=setTimeout(()=>{timedOut=true;try{process.kill(-child.pid,'SIGKILL');}catch{}},timeoutMs);child.on('close',(code,signal)=>{clearTimeout(timer);ok({out,err,code,signal,timedOut,elapsed_ms:performance.now()-start});});});}
export async function run({root,id,repeat,endpoint='http://127.0.0.1:18030/v1',model='openclaw/Qwen3.8-27B-WORK',timeout=600000,maxTurns=24,maxTools=60,maxTokens=32768,thinking='medium',samplingProfile='PRODUCTION',dryRun=false}){
 root=tmpPath(await realpath(tmpPath(root))); const u=new URL(endpoint);if(u.protocol!=='http:'||u.hostname!=='127.0.0.1'||u.username||u.password)throw Error('Only unauthenticated 127.0.0.1 HTTP endpoint allowed');
 for(const n of [repeat,timeout,maxTurns,maxTools,maxTokens])if(!Number.isInteger(Number(n))||Number(n)<=0)throw Error('Budgets/repeat must be positive integers');
 if(Number(repeat)>3)throw Error('repeat must be 1..3');
 const manifest=JSON.parse(await readFile(join(root,'manifest.json')));const c=manifest.cases.find(x=>x.id===id);if(!c)throw Error('Unknown case');if(Number(repeat)>manifest.repetitions)throw Error('repeat exceeds frozen plan');if(manifest.mode==='slim'&&(Number(maxTokens)!==32768||thinking!=='medium'||samplingProfile!=='PRODUCTION'||Number(repeat)!==1))throw Error('Slim budget/profile must remain medium/32768/production/seed1701');if(manifest.extension_sha256!==sha(EXTENSION))throw Error('Extension manifest mismatch');
 const runRoot=join(root,'runs',id,`repeat-${repeat}`);await mkdir(dirname(runRoot),{recursive:true});await mkdir(runRoot);const workspace=join(runRoot,'workspace');await mkdir(workspace);
 const source=join(root,'fixtures',id),files=Object.fromEntries(await Promise.all(Object.keys(c.files).map(async n=>[n,await readFile(join(root,'fixtures',id,n))])));for(const [n,s]of Object.entries(files)){const b=await readFile(join(source,n));if(sha(b)!==c.files[n])throw Error('Frozen fixture mismatch');await mkdir(dirname(join(workspace,n)),{recursive:true});await writeFile(join(workspace,n),b,{mode:n==='verify.sh'?0o700:0o600});}
 const env=minimalEnv(runRoot,workspace,maxTurns,maxTools);env.BASELINE_NAVIGATION=manifest.mode==='slim'?'1':'0';env.BASELINE_WRITE_PREFIX=c.writable_prefix||'src/main/';env.BASELINE_WRITE_PREFIXES=JSON.stringify(c.writable_prefixes||[env.BASELINE_WRITE_PREFIX]);for(const p of [env.HOME,env.TMPDIR,env.PI_CODING_AGENT_DIR])await mkdir(p,{recursive:true,mode:0o700});
 if(c.kind==='external'&&c.public_verifier_sha256!==sha(await readFile(new URL('./public_verify.mjs',import.meta.url))))throw Error('Public compiler identity changed');
 const executionAttempt=Number(process.env.BASELINE_EXECUTION_ATTEMPT||1);if(!Number.isInteger(executionAttempt)||executionAttempt<1)throw Error('Invalid explicit execution attempt');
 const seed=SEEDS[Number(repeat)-1];if(!['PRODUCTION','GREEDY'].includes(samplingProfile))throw Error('Unknown sampling profile');
 const modelDef={id:model,name:model,reasoning:true,contextWindow:262144,maxTokens:Number(maxTokens),input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},compat:{maxTokensField:'max_tokens',supportsDeveloperRole:false,supportsStore:false},samplingParams:{temperature:samplingProfile==='GREEDY'?0:1,top_p:samplingProfile==='GREEDY'?1:0.95,top_k:20,presence_penalty:0,seed,max_tokens:Number(maxTokens),enable_thinking:thinking!=='off',preserve_thinking:true}};
 await json(join(env.PI_CODING_AGENT_DIR,'models.json'),{providers:{'baseline-local':{baseUrl:endpoint,api:'openai-completions',apiKey:'local-no-secret',headers:{'X-Baseline-Case':`${id}/repeat-${repeat}/attempt-${executionAttempt}/ordinal-${process.env.BASELINE_CASE_ORDINAL||'unset'}`},models:[modelDef]}}});await json(join(env.PI_CODING_AGENT_DIR,'settings.json'),{compaction:{enabled:false},retry:{enabled:false},extensionPaths:[]});
 const extension=join(runRoot,'budget.mjs');await writeFile(extension,EXTENSION);
 const prompt=files['TASK.md']+'\nFrozen fixture inventory:\n'+Object.keys(files).sort().join('\n')+'\nTool policy: read and search fixture files using enabled read/grep/find/ls tools, edit/write only '+(c.writable_prefix||'src/main/')+'**. Bash command must be exactly ./verify.sh or bash verify.sh. Never modify tests or verifier.\n';
 const enabledTools=manifest.mode==='slim'?['read','edit','write','bash','grep','find','ls']:['read','edit','write','bash'];
 const navigationToolchain={};if(manifest.mode==='slim')for(const [name,path]of Object.entries(NAVIGATION_BINARIES)){const version=await bounded(path,['--version'],{env},5000);if(version.code!==0||version.timedOut)throw Error('Required navigation binary unavailable');navigationToolchain[name]={path,sha256:sha(await readFile(path)),version:version.out.trim()};}
 const args=[join(PI_ROOT,'dist/cli.js'),'--print','--mode','json','--no-session','--provider','baseline-local','--model',`baseline-local/${model}`,'--no-extensions','--extension',extension,'--no-skills','--no-context-files','--no-prompt-templates','--no-themes','--no-mcp','--no-approve','--offline','--thinking',thinking,'--tools',enabledTools.join(','),'--',prompt];
 const packageInfo=JSON.parse(await readFile(join(PI_ROOT,'package.json')));if(packageInfo.version!=='1.3.0')throw Error('Expected frozen Pi 1.3.0');if(process.version!=='v22.19.0')throw Error('Expected Node v22.19.0');
 const javaVersion=await bounded(JAVA_ROOT+'/bin/java',['-version'],{env},5000),javacVersion=await bounded(JAVA_ROOT+'/bin/javac',['-version'],{env},5000);
 const identity={executionAttempt,trustedGradeTimeoutMs:c.kind==='external'?450000:null,public_verifier_sha256:c.public_verifier_sha256||null,enabledTools,navigationToolchain,qcb_adapter_sha256:sha(await readFile(new URL('./qcb_adapter.mjs',import.meta.url))),case_ordinal:process.env.BASELINE_CASE_ORDINAL||null,prompt_sha256:sha(prompt),seed,samplingProfile,java_root:JAVA_ROOT,java_version:javaVersion.err+javaVersion.out,javac_version:javacVersion.err+javacVersion.out,java_sha256:sha(await readFile(JAVA_ROOT+'/bin/java')),javac_sha256:sha(await readFile(JAVA_ROOT+'/bin/javac')),profile:PROFILE,equivalent_to_historical_sol_pi:false,node:process.version,pi:packageInfo.version,pi_cli_sha256:sha(await readFile(args[0])),extension_sha256:sha(EXTENSION),endpoint,model,timeout,maxTurns,maxTools,maxTokens,thinking,sampling:modelDef.samplingParams,fixture:manifest.cases.find(x=>x.id===id),args};await json(join(runRoot,'identity.json'),identity);
 if(dryRun)return{runRoot,dryRun:true,identity};
 const pi=await bounded(NODE,args,{cwd:workspace,env},Number(timeout));await writeFile(join(runRoot,'pi.jsonl'),pi.out);await writeFile(join(runRoot,'stderr.log'),pi.err);
 const writePrefixes=c.writable_prefixes||[c.writable_prefix||'src/main/'];const mainNames=(await Promise.all(writePrefixes.map(async prefix=>Object.keys(await treeFiles(join(workspace,prefix))).map(n=>prefix+n)))).flat();
 const after=Object.fromEntries(await Promise.all([...new Set([...Object.keys(files),...mainNames])].map(async n=>[n,sha(await readFile(join(workspace,n)).catch(()=>Buffer.from('MISSING')))])));
 const protectedOk=Object.keys(files).filter(x=>!writePrefixes.some(prefix=>x.startsWith(prefix))).every(n=>after[n]===sha(files[n]));
 const mainFiles=mainNames;const forbiddenExit=(await Promise.all(mainFiles.map(n=>readFile(join(workspace,n),'utf8').catch(()=>'')))).some(text=>/\b(?:exit|halt)\s*\(/.test(text));
 const verify=c.kind==='external'?await externalGrade({runRoot,workspace,source,descriptor:c,env,bounded}):await freshGrade({runRoot,workspace,source,files:c.files,writablePrefix:c.writable_prefix||'src/main/',grader:c.grader,graderHashes:c.grader_files,env,bounded});await writeFile(join(runRoot,'verify.log'),verify.out+verify.err);
 const diff=await bounded('/usr/bin/diff',['-ruN',join(source,c.writable_prefix||'src/main/'),join(workspace,c.writable_prefix||'src/main/')],{cwd:workspace,env},5000);await writeFile(join(runRoot,'changes.patch'),diff.out);
 const postVerifyProtected=Object.keys(files).filter(x=>!writePrefixes.some(prefix=>x.startsWith(prefix)));const protectedAfterVerify=(await Promise.all(postVerifyProtected.map(async n=>sha(await readFile(join(workspace,n)).catch(()=>Buffer.from('MISSING')))===sha(files[n])))).every(Boolean);
 const judge=['qcb','external'].includes(c.kind)?qcbJudge(verify,protectedOk&&protectedAfterVerify,forbiddenExit):judgeVerification(id,verify,protectedOk&&protectedAfterVerify,forbiddenExit);const judgeCompleted=judge.completed;
 const budget=await readFile(env.BASELINE_BUDGET_LOG,'utf8').catch(()=> '');const metrics=parseEvents(pi.out);
 const policy=classifyPolicyEvents(budget);
 const summary={execution_attempt:executionAttempt,policy_denials:policy.denials,hard_budget_events:policy.hard,id,repeat:Number(repeat),profile:PROFILE,status:pi.timedOut?'TIMEOUT':policy.hard.length?'BUDGET_HARD_STOP':pi.code!==0||metrics.assistant_turns===0||metrics.usage_observations!==metrics.assistant_turns||metrics.errors.length||metrics.invalid_lines||metrics.assistant_stop_reasons.some(x=>['error','aborted'].includes(x))?'AGENT_ERROR':metrics.assistant_stop_reasons.includes('length')?'OUTPUT_LIMIT':judge.passed?'PASS':'FAIL',pi_exit:pi.code,pi_signal:pi.signal,verify_exit:verify.code,verify_timeout:verify.timedOut,protected_ok:protectedOk&&protectedAfterVerify,judge_completed:judgeCompleted,forbidden_exit:forbiddenExit,source_changed:Object.keys(after).filter(n=>writePrefixes.some(prefix=>n.startsWith(prefix))).some(n=>after[n]!==sha(files[n]??'')),elapsed_ms:pi.elapsed_ms,metrics,budget_events:budget,final_hashes:after,raw_sha256:sha(pi.out),patch_sha256:sha(diff.out),identity_sha256:sha(JSON.stringify(identity)),runRoot};await json(join(runRoot,'summary.json'),summary);return summary;
}
async function main(){const [cmd,root,...rest]=process.argv.slice(2);if(cmd==='add-external')console.log(JSON.stringify(await addExternal(root,rest[0])));else if(cmd==='prepare')console.log(JSON.stringify(await prepare(root,rest[0]||'full')));else if(cmd==='run'){const [id,repeat,endpoint,model]=rest;console.log(JSON.stringify(await run({root,id,repeat:Number(repeat),endpoint,model,dryRun:process.env.BASELINE_DRY_RUN==='1',timeout:Number(process.env.BASELINE_TIMEOUT_MS||600000),maxTurns:Number(process.env.BASELINE_MAX_TURNS||24),maxTools:Number(process.env.BASELINE_MAX_TOOLS||60),maxTokens:Number(process.env.BASELINE_MAX_TOKENS||32768),thinking:process.env.BASELINE_THINKING||'medium',samplingProfile:process.env.BASELINE_SAMPLING_PROFILE||'PRODUCTION'})));}else throw Error('Usage: closed_loop.mjs prepare /tmp/root | run /tmp/root CASE REPEAT [http://127.0.0.1:18030/v1] [MODEL]');}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url)await main();
