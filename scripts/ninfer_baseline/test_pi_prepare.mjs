import test from 'node:test';
import assert from 'node:assert/strict';
import {loadPi,validateTree,capture,publicRow,hash} from './pi_prepare.mjs';
const pi=await loadPi();
const msg=(id,parentId,text,role='user')=>({type:'message',id,parentId,timestamp:'2026-01-01T00:00:00Z',message:{role,content:[{type:'text',text}],timestamp:1}});
const target={...msg('answer','leaf','answer','assistant'),message:{role:'assistant',model:'openclaw/Qwen3.8-27B-WORK',usage:{input:10,cacheRead:20,output:5},stopReason:'stop'}};
test('parent traversal rejects missing parents and cycles',()=>{
 assert.throws(()=>validateTree([msg('a','missing','x')],'a'),/Missing parent/);
 assert.throws(()=>validateTree([msg('a','b','x'),msg('b','a','x')],'a'),/cycle/);
});
test('canonical Pi projection excludes sibling branch',async()=>{
 const entries=[msg('root',null,'ROOT'),msg('sibling','root','PRIVATE_SIBLING'),msg('leaf','root','KEPT'),target];
 const {payload,fetchCalls}=await capture(pi,entries,target);
 assert.equal(fetchCalls,0);assert.match(JSON.stringify(payload),/KEPT/);assert.doesNotMatch(JSON.stringify(payload),/PRIVATE_SIBLING/);
 assert.equal(payload.max_tokens,32768);assert.equal(payload.reasoning_effort,undefined);assert.equal(payload.enable_thinking,false);
});
test('context edits replace prior content and compaction discards earlier prompt',async()=>{
 const entries=[msg('root',null,'OLD_PRIVATE'),msg('keep','root','REPLACE_ME'),
  {type:'compaction',id:'compact',parentId:'keep',timestamp:'2026-01-01T00:00:00Z',summary:'SUMMARY',firstKeptEntryId:'keep',tokensBefore:10},
  {type:'context_edit',id:'edit',parentId:'compact',targetId:'keep',replacement:{content:'EDITED'}},msg('leaf','edit','CONTINUE'),target];
 const {payload}=await capture(pi,entries,target);const text=JSON.stringify(payload);
 assert.match(text,/SUMMARY/);assert.match(text,/EDITED/);assert.doesNotMatch(text,/OLD_PRIVATE|REPLACE_ME/);
});
test('tool call history is data only; public manifest has no private payload',async()=>{
 const entries=[msg('root',null,'SECRET_USER_TEXT'),
 {type:'message',id:'call',parentId:'root',timestamp:'2026-01-01T00:00:00Z',message:{role:'assistant',provider:'openclaw',model:'openclaw/Qwen3.8-27B-WORK',api:'openai-completions',content:[{type:'toolCall',id:'call1',name:'bash',arguments:{command:'NEVER_EXECUTE_PRIVATE'}}],stopReason:'toolUse',timestamp:1}},
 {type:'message',id:'leaf',parentId:'call',timestamp:'2026-01-01T00:00:00Z',message:{role:'toolResult',toolCallId:'call1',toolName:'bash',content:[{type:'text',text:'SECRET_TOOL_RESULT'}],isError:false,timestamp:2}},target];
 const {payload,fetchCalls}=await capture(pi,entries,target);assert.equal(fetchCalls,0);
 assert.match(JSON.stringify(payload),/NEVER_EXECUTE_PRIVATE/);
 const row=publicRow({id:'fixture',sourceHash:hash('source'),target,payload,sourceName:'fixture.jsonl',entries});
 assert.equal(row.historical_prompt_tokens_usage,30);assert.equal(row.tool_execution,false);
 assert.doesNotMatch(JSON.stringify(row),/SECRET_USER_TEXT|SECRET_TOOL_RESULT|NEVER_EXECUTE_PRIVATE|offline-capture-only/);
 assert.equal(row.payload_sha256,hash(JSON.stringify(payload)));
});
test('stored system sections and tool declarations survive canonical serialization',async()=>{
 const entries=[{type:'message',id:'system',parentId:null,timestamp:'2026-01-01T00:00:00Z',message:{role:'system',content:'',sections:{baseline:'STORED_SYSTEM_SECTION'},toolsAdded:[{name:'fixture_tool',description:'Offline fixture',parameters:{type:'object',properties:{},required:[]}}],timestamp:1}},msg('leaf','system','USER'),target];
 const {payload}=await capture(pi,entries,target);
 assert.match(JSON.stringify(payload.messages),/STORED_SYSTEM_SECTION/);
 assert.equal(payload.tools[0].function.name,'fixture_tool');
});
test('deterministic redaction removes service keys, Bearer and named assignments while preserving structure',async()=>{
 const {redactWire}=await import('./pi_prepare.mjs');
 const input={messages:[{role:'user',content:'apiKey="fixture-credential-12345" password=fixture-password-12345 Authorization: Bearer fixtureBearerToken123456789 sk-fixtureServiceKey123456789012345'}],tools:[{function:{name:'safe_tool',parameters:{token:{type:'string'}}}}],apiKey:'fixture-object-value'};
 const a=redactWire(input),b=redactWire(input);assert.deepEqual(a,b);
 assert.doesNotMatch(JSON.stringify(a.payload),/fixture-credential|fixture-password|fixtureBearer|sk-fixture|fixture-object/);
 assert.equal(a.payload.messages[0].role,'user');assert.equal(a.payload.tools[0].function.name,'safe_tool');
 assert.equal(a.payload.tools[0].function.parameters.token.type,'string');
 assert.equal(a.redaction_count_by_kind.service_key,1);assert.equal(a.redaction_count_by_kind.bearer,1);
 assert.equal(a.redaction_count_by_kind.sensitive_property,1);assert.equal(a.redaction_count_by_kind.named_assignment,2);
 assert.deepEqual(redactWire(a.payload).payload,a.payload);
});
