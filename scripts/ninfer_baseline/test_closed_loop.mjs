import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,readFile,mkdir,readdir} from 'node:fs/promises';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {CASES,EXTENSION,NODE,prepare,run,parseEvents,bounded,minimalEnv,PI_ROOT,fixtureFiles,judgeVerification} from './closed_loop.mjs';
test('20 frozen business fixtures and dry-run isolation without network',async()=>{
 const root=await mkdtemp('/tmp/ninfer-closed-loop-test-');const m=await prepare(root);
 assert.equal(m.case_count,20);assert.equal(new Set(CASES.map(x=>x.id)).size,20);assert.equal(m.repetitions,3);
 const r=await run({root,id:'business-pagination',repeat:1,dryRun:true});
 assert.equal(r.identity.pi,'1.3.0');assert.equal(r.identity.seed,1701);assert.equal(r.identity.maxTokens,32768);assert.equal(r.identity.thinking,'medium');assert.equal(r.identity.sampling.top_k,20);assert.ok(r.identity.java_root.endsWith('/25.0.1-open'));assert.match(r.identity.javac_version,/25.0.1/);assert.ok(r.identity.args.includes('--no-context-files'));assert.ok(r.identity.args.includes('--no-mcp'));assert.ok(r.identity.args.includes('--no-approve'));
 const env=minimalEnv(root,root,1,1);assert.equal(env.OPENAI_API_KEY,undefined);assert.equal(env.HOME,join(root,'home'));
 await assert.rejects(run({root,id:'business-pagination',repeat:2,endpoint:'https://external.example/v1',dryRun:true}),/127/);
 await writeFile(join(root,'fixtures','business-cache-invalidation','src/test/java/ServiceTest.java'),'tampered');
 await assert.rejects(run({root,id:'business-cache-invalidation',repeat:1,dryRun:true}),/fixture mismatch/);
});
test('sum usage across final assistant messages exactly once, not streaming deltas',()=>{
 const raw=[{type:'message_update',message:{role:'assistant',usage:{input:100}}},{type:'message_end',message:{role:'assistant',usage:{input:10,output:2,cacheRead:3,totalTokens:15}}},{type:'message_end',message:{role:'toolResult',usage:{input:999}}},{type:'message_end',message:{role:'assistant',usage:{input:20,output:4,totalTokens:24}}},{type:'tool_execution_start',toolName:'bash'}].map(JSON.stringify).join('\n');
 const m=parseEvents(raw);assert.equal(m.usage.input,30);assert.equal(m.usage.output,6);assert.equal(m.usage.cacheRead,3);assert.equal(m.assistant_turns,2);assert.equal(m.tool_calls,1);
});
test('unique explicit extension gates tools before execution and aborts budgets',async()=>{
 const root=await mkdtemp('/tmp/ninfer-closed-loop-gate-');await writeFile(join(root,'budget.mjs'),EXTENSION);
 const handlers={};const mod=await import(pathToFileURL(join(root,'budget.mjs')).href);mod.default({on:(n,f)=>handlers[n]=f});
 const old={...process.env};Object.assign(process.env,{BASELINE_WORKSPACE:root,BASELINE_BUDGET_LOG:join(root,'events'),BASELINE_MAX_TURNS:'1',BASELINE_MAX_TOOLS:'4'});
 let aborted=0;const ctx={abort(){aborted++;}};
 try{handlers.turn_start({},ctx);handlers.turn_start({},ctx);assert.equal(aborted,1);
 assert.equal(handlers.tool_call({toolName:'read',input:{path:'Main.java'}},ctx),undefined);
 assert.equal(handlers.tool_call({toolName:'edit',input:{path:'src/main/java/Service.java'}},ctx),undefined);
 assert.equal(handlers.tool_call({toolName:'bash',input:{command:'cat ~/.ssh/id_rsa'}},ctx).block,true);
 assert.equal(handlers.tool_call({toolName:'edit',input:{path:'MainTest.java'}},ctx).block,true);
 assert.equal(handlers.tool_call({toolName:'bash',input:{command:'./verify.sh'}},ctx).reason,'TOOL_BUDGET');
 }finally{for(const k of Object.keys(process.env))if(!(k in old))delete process.env[k];Object.assign(process.env,old);}
});
test('bounded execution times out whole detached process group',async()=>{
 const r=await bounded(NODE,['-e','setInterval(()=>{},1000)'],{},100);assert.equal(r.timedOut,true);assert.equal(r.signal,'SIGKILL');assert.ok(r.elapsed_ms<3000);
});
test('20 business fixtures compile and fail real behavioral assertions; targeted repair passes',async()=>{
 const root=await mkdtemp('/tmp/ninfer-closed-loop-business-');await prepare(root);
 for(const {id}of CASES){const dir=join(root,'fixtures',id),env=minimalEnv(root,dir,24,60);await mkdir(env.TMPDIR,{recursive:true});const r=await bounded('/bin/bash',['verify.sh'],{cwd:dir,env},30000);assert.equal(r.code,1,`${id}: ${r.err}`);assert.match(r.err,id==='business-soft-delete'?/IllegalStateException: duplicate/:id==='java-agent-2-retry-contract'?/IllegalStateException: retry exhausted/:/AssertionError/,id);}
 const dir=join(root,'fixtures','business-pagination');const f=join(dir,'src/main/java/Service.java');await writeFile(f,(await readFile(f,'utf8')).replace('new Page(ids,ids.size())','new Page(ids,all.size())'));const r=await bounded('/bin/bash',['verify.sh'],{cwd:dir,env:minimalEnv(root,dir,24,60)},30000);assert.equal(r.code,0,r.err);assert.match(r.out,/PASS business-pagination/);
});
test('actual Pi provider serializes frozen production sampling and seed without network',async()=>{
 const {stream}=await import(pathToFileURL(PI_ROOT+'/node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js').href);let body,fetches=0;
 const model={id:'test',provider:'baseline-local',api:'openai-completions',baseUrl:'http://127.0.0.1:1/v1',reasoning:true,contextWindow:262144,maxTokens:32768,input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},compat:{maxTokensField:'max_tokens',supportsDeveloperRole:false,supportsStore:false},samplingParams:{temperature:1,top_p:0.95,top_k:20,seed:1701,max_tokens:32768,presence_penalty:0,preserve_thinking:true}};
 const s=stream(model,{messages:[{role:'user',content:'offline',timestamp:0}]},{apiKey:'local-no-secret',reasoningEffort:'medium',maxRetries:0,onPayload(payload){body=payload;throw Error('OFFLINE_STOP');},fetch(){fetches++;throw Error('NETWORK_FORBIDDEN');}});await s.result();assert.equal(fetches,0);assert.equal(body.temperature,1);assert.equal(body.top_p,0.95);assert.equal(body.top_k,20);assert.equal(body.seed,1701);assert.equal(body.max_tokens,32768);assert.equal(body.reasoning_effort,'medium');
});

test('judge requires genuine completion, unchanged tests, no exit/halt and no timeout',()=>{
 const good={code:0,out:'PASS business-pagination\n',timedOut:false};
 assert.equal(judgeVerification('business-pagination',good,true,false).passed,true);
 assert.equal(judgeVerification('business-pagination',{...good,out:''},true,false).passed,false);
 assert.equal(judgeVerification('business-pagination',good,true,true).passed,false);
 assert.equal(judgeVerification('business-pagination',good,false,false).passed,false);
 assert.equal(judgeVerification('business-pagination',{...good,timedOut:true},true,false).passed,false);
});

test('slim freezes old three plus five QCB cases without exposing hidden/reference files',async()=>{
 const root=await mkdtemp('/tmp/ninfer-closed-slim-');const manifest=await prepare(root,'slim');
 assert.equal(manifest.case_count,8);assert.deepEqual(manifest.seeds,[1701]);assert.equal(manifest.repetitions,1);
 assert.deepEqual(manifest.cases.slice(3).map(c=>c.id),['qcb-BF009','qcb-RE003','qcb-RE007','qcb-AT005','qcb-LC003']);
 for(const c of manifest.cases.slice(3)){assert.ok(Object.keys(c.files).every(p=>!p.includes('hidden_tests')&&!p.includes('reference')));assert.ok(!c.grader.startsWith(join(root,'fixtures')));}
 const dry=await run({root,id:'qcb-BF009',repeat:1,dryRun:true});assert.equal(dry.identity.maxTokens,32768);assert.equal(dry.identity.seed,1701);assert.deepEqual(dry.identity.enabledTools,['read','edit','write','bash','grep','find','ls']);assert.match(dry.identity.navigationToolchain.rg.version,/ripgrep/);assert.match(dry.identity.navigationToolchain.fd.version,/fd /);
 assert.ok(!dry.identity.args.at(-1).includes('TestMain.java'));assert.match(dry.identity.args.at(-1),/src\/\*\*/);
 await assert.rejects(run({root,id:'qcb-RE003',repeat:1,maxTokens:4096,dryRun:true}),/budget\/profile/);
 await assert.rejects(run({root,id:'qcb-RE003',repeat:2,dryRun:true}),/repeat exceeds/);
});
test('fresh QCB grader fails original defect and passes reference overlay without inheriting compiled files',async()=>{
 const {freshGrade,filesAt,writeFiles,QCB_ROOT,qcbJudge}=await import('./qcb_adapter.mjs');
 const root=await mkdtemp('/tmp/ninfer-fresh-grade-');const m=await prepare(root,'slim');const c=m.cases.find(c=>c.id==='qcb-BF009');
 const workspace=join(root,'candidate');await writeFiles(workspace,await filesAt(join(root,'fixtures',c.id)));
 const env=minimalEnv(root,workspace,24,60);await mkdir(env.TMPDIR,{recursive:true});
 const grade=async name=>{const runRoot=join(root,name);await mkdir(runRoot);return freshGrade({runRoot,workspace,source:join(root,'fixtures',c.id),files:c.files,writablePrefix:'src/',grader:c.grader,graderHashes:c.grader_files,env,bounded});};
 const bad=await grade('bad');assert.equal(qcbJudge(bad,true,false).passed,false);
 await writeFiles(workspace,await filesAt(join(QCB_ROOT,'tasks/BF009/reference')));await writeFile(join(workspace,'src','untrusted.class'),'NOT A REAL CLASS');
 const good=await grade('good');assert.equal(qcbJudge(good,true,false).passed,true,good.out+good.err);
 assert.ok(!(await readdir(join(root,'good','fresh-grader-workspace','src'))).includes('untrusted.class'));
 assert.equal(qcbJudge({...good,out:'{}'},true,false).passed,false);assert.equal(qcbJudge({...good,timedOut:true},true,false).passed,false);
});

test('external adapter freezes production prefixes, keeps grader private, and makes clean Java-only patch',async()=>{
 const {prepareExternal,externalGrade,filesAt,writeFiles,qcbJudge,sha}=await import('./qcb_adapter.mjs');
 const root=await mkdtemp('/tmp/ninfer-external-adapter-'),base=join(root,'base'),visible=join(root,'visible');
 await writeFiles(base,{'module/src/main/java/Example.java':Buffer.from('class Example { int value(){ return 1; } }\n'),'README.md':Buffer.from('public docs')});
 const grader=join(root,'grade.sh');await writeFile(grader,'#!/bin/bash\nset -eu\ngrep -q "^--- a/module/src/main/java/Example.java" "$1"\necho \'{"passed":true,"tests_passed":1,"tests_total":1}\'\n');
 const prompt=join(root,'prompt.md');await writeFile(prompt,'Fix value to return 2.');const mp=join(root,'external.json');
 await writeFile(mp,JSON.stringify({cases:[{case_id:'fixture-external-1',status:'READY',base_dir:base,prompt_file:prompt,grade_script:grader,grade_files:{[grader]:sha(await readFile(grader))},environment:{production_prefixes:['module/src/main/java/']}}]}));
 const [descriptor]=await prepareExternal(visible,mp);const source=join(visible,'fixtures',descriptor.id);const workspace=join(root,'agent');await writeFiles(workspace,await filesAt(source));
 await writeFile(join(workspace,'module/src/main/java/Example.java'),'class Example { int value(){ return 2; } }\n');await writeFile(join(workspace,'module/src/main/java/ignore.class'),'not code');
 const runRoot=join(root,'run');await mkdir(runRoot);const env=minimalEnv(root,workspace,24,60);
 const result=await externalGrade({runRoot,workspace,source,descriptor,env,bounded:(command,args,options,timeout)=>{if(command==='/bin/bash')assert.equal(timeout,450000);return bounded(command,args,options,timeout);}});assert.equal(qcbJudge(result,true,false).passed,true,result.out+result.err);
 const patch=await readFile(join(runRoot,'candidate.patch'),'utf8');assert.ok(!patch.includes('ignore.class'));assert.ok(!patch.includes(grader));
 await writeFile(grader,'changed');await assert.rejects(externalGrade({runRoot,workspace,source,descriptor,env,bounded}),/grader dependency changed/);
 await writeFile(mp,JSON.stringify({cases:[{case_id:'bad',status:'READY',base_dir:base,prompt_file:prompt,grade_script:grader,grade_files:{[grader]:sha(await readFile(grader))},environment:{}}]}));
 await assert.rejects(prepareExternal(visible,mp),/prefixes required/);
});

test('fresh graders preserve production Java deletion instead of restoring baseline source',async()=>{
 const {freshGrade,writeFiles,externalGrade,sha}=await import('./qcb_adapter.mjs');const {unlink}=await import('node:fs/promises');
 const root=await mkdtemp('/tmp/ninfer-delete-grade-');const source=join(root,'base'),workspace=join(root,'candidate');
 const files={'src/main/java/Service.java':Buffer.from('class Service {}\n'),'src/main/java/Removed.java':Buffer.from('class Removed {}\n'),
 'verify.sh':Buffer.from('#!/bin/bash\nset -eu\ntest ! -f src/main/java/Removed.java\necho PASS delete\n')};
 await writeFiles(source,files);await writeFiles(workspace,files);await unlink(join(workspace,'src/main/java/Removed.java'));
 const hashes=Object.fromEntries(Object.entries(files).map(([p,b])=>[p,sha(b)]));const env=minimalEnv(root,workspace,24,60);const runRoot=join(root,'fresh');await mkdir(runRoot);
 const verify=await freshGrade({runRoot,workspace,source,files:hashes,writablePrefix:'src/main/',env,bounded});assert.equal(verify.code,0,verify.out+verify.err);
 const grade=join(root,'grade.sh');await writeFile(grade,'#!/bin/bash\nset -eu\ngrep -q "^+++ /dev/null" "$1"\necho \'{"passed":true,"tests_passed":1,"tests_total":1}\'\n');
 const externalRoot=join(root,'external');await mkdir(externalRoot);
 const descriptor={external_grade_script:grade,external_grade_sha256:sha(await readFile(grade)),writable_prefixes:['src/main/']};
 const result=await externalGrade({runRoot:externalRoot,workspace,source,descriptor,env,bounded});assert.equal(result.code,0,result.out+result.err);
 const patch=await readFile(join(externalRoot,'candidate.patch'),'utf8');assert.match(patch,/Removed.java/);assert.match(patch,/\+\+\+ \/dev\/null/);
});

test('slim navigation allows workspace root searches and refuses traversal and arbitrary shell',async()=>{
 const root=await mkdtemp('/tmp/ninfer-navigation-gate-');await writeFile(join(root,'budget.mjs'),EXTENSION);const handlers={};
 (await import(pathToFileURL(join(root,'budget.mjs')).href)).default({on:(n,f)=>handlers[n]=f});
 const previous={...process.env};Object.assign(process.env,{BASELINE_WORKSPACE:root,BASELINE_BUDGET_LOG:join(root,'events'),BASELINE_MAX_TURNS:'24',BASELINE_MAX_TOOLS:'60',BASELINE_NAVIGATION:'1',BASELINE_WRITE_PREFIXES:'["src/"]'});
 try{for(const toolName of ['grep','find','ls']){assert.equal(handlers.tool_call({toolName,input:{}},{abort(){}}),undefined);assert.equal(handlers.tool_call({toolName,input:{path:'src'}},{abort(){}}),undefined);assert.equal(handlers.tool_call({toolName,input:{path:'../'}},{abort(){}}).reason.startsWith('PATH_OUTSIDE_FIXTURE'),true);}
 assert.equal(handlers.tool_call({toolName:'edit',input:{path:'README.md'}},{abort(){}}).reason.startsWith('PROTECTED_FILE'),true);
 assert.equal(handlers.tool_call({toolName:'bash',input:{command:'find .'}},{abort(){}}).reason.startsWith('BASH_NOT_ALLOWLISTED'),true);
 }finally{for(const k of Object.keys(process.env))if(!(k in previous))delete process.env[k];Object.assign(process.env,previous);}
});
test('installed Pi navigation tools execute offline against a real fixture',async()=>{
 const root=await mkdtemp('/tmp/ninfer-navigation-tools-');await mkdir(join(root,'src'));await writeFile(join(root,'src','Example.java'),'class NavigationFixture {}\n');
 const previous={PATH:process.env.PATH,PI_OFFLINE:process.env.PI_OFFLINE};process.env.PATH=minimalEnv(root,root,24,60).PATH;process.env.PI_OFFLINE='1';
 try{const tools=await import(pathToFileURL(PI_ROOT+'/dist/core/tools/index.js').href);
 const ls=await tools.createLsToolDefinition(root).execute('ls-fixture',{},undefined);assert.match(JSON.stringify(ls),/src/);
 const find=await tools.createFindToolDefinition(root).execute('find-fixture',{pattern:'*.java'},undefined);assert.match(JSON.stringify(find),/Example.java/);
 const grep=await tools.createGrepToolDefinition(root).execute('grep-fixture',{pattern:'NavigationFixture'},undefined);assert.match(JSON.stringify(grep),/NavigationFixture/);
 }finally{for(const [k,v]of Object.entries(previous))if(v===undefined)delete process.env[k];else process.env[k]=v;}
});

test('explicit trusted runtime dependencies accept SHA-verified absolute binaries without widening private grader paths',async()=>{
 const {verifyGradeFiles,TRUSTED_RUNTIME_DEPENDENCIES,sha}=await import('./qcb_adapter.mjs');
 const root=await mkdtemp('/tmp/ninfer-runtime-dependencies-');const wrapper=join(root,'grade.sh');await writeFile(wrapper,'#!/bin/bash\nexit 0\n');
 const python='/opt/homebrew/opt/python@3.14/bin/python3.14';assert.ok(TRUSTED_RUNTIME_DEPENDENCIES.has(python));
 const files={[wrapper]:sha(await readFile(wrapper)),[python]:sha(await readFile(python))};await verifyGradeFiles(files,wrapper);
 await assert.rejects(verifyGradeFiles({...files,[python]:'0'.repeat(64)},wrapper),/dependency changed/);
 await assert.rejects(verifyGradeFiles({...files,'/usr/bin/python3':'0'.repeat(64)},wrapper),/dependency identity/);
 await assert.rejects(verifyGradeFiles(files,python),/wrapper must remain/);
 await assert.rejects(verifyGradeFiles({...files,'/tmp/../etc/passwd':'0'.repeat(64)},wrapper),/dependency identity/);
});

test('real extension writes recoverable denials as newline JSON and next tool still executes; hard budget aborts',async()=>{
 const {classifyPolicyEvents}=await import('./closed_loop.mjs');const root=await mkdtemp('/tmp/ninfer-soft-policy-');await writeFile(join(root,'budget.mjs'),EXTENSION);const handlers={};
 (await import(pathToFileURL(join(root,'budget.mjs')).href)).default({on:(name,fn)=>handlers[name]=fn});const old={...process.env};let aborted=0;
 Object.assign(process.env,{BASELINE_WORKSPACE:root,BASELINE_BUDGET_LOG:join(root,'events'),BASELINE_MAX_TURNS:'24',BASELINE_MAX_TOOLS:'4',BASELINE_NAVIGATION:'1'});
 try{const ctx={abort(){aborted++;}};
 assert.equal(handlers.tool_call({toolName:'bash',input:{command:'cd gson && javac unsafe'}},ctx).block,true);
 assert.equal(handlers.tool_call({toolName:'write',input:{path:'/tmp/unsafe.java'}},ctx).block,true);assert.equal(aborted,0);
 assert.equal(handlers.tool_call({toolName:'read',input:{path:'src/main/java/Main.java'}},ctx),undefined);
 const before=await readFile(join(root,'events'),'utf8');assert.equal(before.split('\n').filter(Boolean).length,2);assert.equal(classifyPolicyEvents(before).denials.length,2);assert.deepEqual(classifyPolicyEvents(before).hard,[]);
 assert.equal(handlers.tool_call({toolName:'bash',input:{command:'./verify.sh'}},ctx),undefined);
 assert.equal(handlers.tool_call({toolName:'read',input:{path:'src/main/java/Main.java'}},ctx).reason,'TOOL_BUDGET');assert.equal(aborted,1);
 const all=classifyPolicyEvents(await readFile(join(root,'events'),'utf8'));assert.equal(all.denials.length,2);assert.equal(all.hard.length,1);
 }finally{for(const key of Object.keys(process.env))if(!(key in old))delete process.env[key];Object.assign(process.env,old);}
});
test('public compile commands use only offline production modules and reject unknown repositories',async()=>{
 const {compileCommand}=await import('./public_verify.mjs');
 for(const id of ['google__gson-2158','javaparser__javaparser-4561']){const command=compileCommand(id);assert.ok(command.includes('-o'));assert.ok(command.includes('-Dmaven.test.skip=true'));assert.ok(command.includes('compile'));assert.ok(!command.includes('test'));}
 assert.throws(()=>compileCommand('arbitrary-repo'),/No frozen public compiler/);
});
