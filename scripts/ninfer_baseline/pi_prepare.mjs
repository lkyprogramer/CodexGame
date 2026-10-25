#!/usr/bin/env node
/** Offline session-derived corpus. Never resumes agents or executes tools. */
import { readFile, writeFile, mkdir, readdir, chmod } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { resolve, join, basename } from 'node:path';
import { pathToFileURL } from 'node:url';

export const PI_ROOT = process.env.PI_PACKAGE_ROOT || '/Users/luo/.nvm/versions/node/v22.19.0/lib/node_modules/@earendil-works/pi-coding-agent';
export const hash = value => createHash('sha256').update(value).digest('hex');
export const REDACTION_POLICY = {
  version: 'pi-wire-secrets-v1',
  placeholder: '[REDACTED_<KIND>]',
  scope: 'Recursive string values and sensitive property values after Pi serialization',
  confidence: 'Service key shapes and Bearer are high confidence patterns; named assignments are conservative heuristics and can include fixture values.',
};
export function redactWire(value) {
  const counts = {};
  const bump = kind => { counts[kind] = (counts[kind] || 0) + 1; return `[REDACTED_${kind.toUpperCase()}]`; };
  const text = input => input
    .replace(/\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b/g, () => bump('service_key'))
    .replace(/\bBearer[ \t]+[A-Za-z0-9._~+\/-]{8,}={0,2}/gi, () => `Bearer ${bump('bearer')}`)
    .replace(/((?:["']?)(?:api[_-]?key|access[_-]?token|auth[_-]?token|token|password|passwd|secret|client[_-]?secret)(?:["']?)[ \t]*[:=][ \t]*)(["'])([^\r\n]*?)\2/gi,
      (all, prefix, quote, secret) => secret.includes('[REDACTED_') ? all : `${prefix}${quote}${bump('named_assignment')}${quote}`)
    .replace(/((?:api[_-]?key|access[_-]?token|auth[_-]?token|token|password|passwd|secret|client[_-]?secret)[ \t]*[:=][ \t]*)([^\s"'`,;{}<>]{6,})/gi,
      (all, prefix, secret) => secret.includes('[REDACTED_') ? all : `${prefix}${bump('named_assignment')}`);
  const walk = input => {
    if (typeof input === 'string') return text(input);
    if (Array.isArray(input)) return input.map(walk);
    if (input && typeof input === 'object') return Object.fromEntries(Object.entries(input).map(([key, child]) => {
      if (/^(?:api[_-]?key|access[_-]?token|auth[_-]?token|token|password|passwd|secret|client[_-]?secret|authorization)$/i.test(key)
          && typeof child === 'string' && child && !child.includes('[REDACTED_')) return [key, bump('sensitive_property')];
      return [key, walk(child)];
    }));
    return input;
  };
  return {payload:walk(value),redaction_count_by_kind:counts};
}

export async function loadPi() {
  const mod = path => import(pathToFileURL(join(PI_ROOT, path)).href);
  const [session, messages, provider] = await Promise.all([
    mod('dist/core/session-manager.js'), mod('dist/core/messages.js'),
    mod('node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js'),
  ]);
  return { ...session, ...messages, stream: provider.stream };
}
export function validateTree(entries, leaf) {
  const byId = new Map(entries.filter(x => x.id && x.type !== 'session').map(x => [x.id, x]));
  if (byId.size !== entries.filter(x => x.id && x.type !== 'session').length) throw Error('Duplicate entry IDs');
  const seen = new Set(); let id = leaf;
  while (id) {
    if (seen.has(id)) throw Error('Parent cycle');
    seen.add(id); const entry = byId.get(id);
    if (!entry) throw Error('Missing parent entry');
    id = entry.parentId;
  }
  return byId;
}
export function selectEntries(entries) {
  const assistants = entries.filter(x => x.type === 'message' && x.message?.role === 'assistant' && x.message.model === 'openclaw/Qwen3.8-27B-WORK');
  const selected = new Set();
  // Natural historical usage only guides selection; actual tokenizer calibration is separate.
  for (const target of [4096, 8192, 16384, 32768, 65536, 98304, 131072, 163840, 184320, 196608, 229376, 245760]) {
    const eligible = assistants.filter(x => x.message.stopReason !== 'error' && x.parentId);
    eligible.sort((a,b) => Math.abs(promptUsage(a)-target)-Math.abs(promptUsage(b)-target));
    if (eligible[0]) selected.add(eligible[0].id);
  }
  for (const id of ['f89c5dcc','97fc7be6']) {
    const i = assistants.findIndex(x => x.id === id);
    if (i >= 0) for (let j=Math.max(0,i-2); j<=Math.min(assistants.length-1,i+2); j++) selected.add(assistants[j].id);
  }
  // Preserve a contiguous cold-to-tool-append trace rather than only isolated points.
  for (const entry of assistants.slice(0,4)) selected.add(entry.id);
  return assistants.filter(x => selected.has(x.id));
}
function promptUsage(entry) {
  const u=entry.message.usage || {}; return (u.input||0)+(u.cacheRead||0)+(u.cacheWrite||0);
}
export async function capture(pi, entries, target) {
  const byId=validateTree(entries,target.parentId);
  const projection=pi.buildSessionContext(entries,target.parentId,byId);
  const messages=pi.convertToLlm(projection.messages);
  let payload; let fetchCalls=0;
  const stream=pi.stream({ id:'openclaw/Qwen3.8-27B-WORK', provider:'openclaw', api:'openai-completions', baseUrl:'http://127.0.0.1:1/v1', reasoning:true,
    contextWindow:262144, maxTokens:32768, input:['text'],cost:{input:0,output:0,cacheRead:0,cacheWrite:0},
    compat:{maxTokensField:'max_tokens',supportsDeveloperRole:false,supportsStore:false,supportsReasoningEffort:true} },
    { messages }, { apiKey:'offline-capture-only', maxTokens:32768, reasoningEffort:projection.thinkingLevel || 'medium',
      temperature:1, maxRetries:0,
      onPayload(value) { payload=JSON.parse(JSON.stringify(value)); throw Error('OFFLINE_CAPTURE_COMPLETE'); },
      fetch() { fetchCalls++; throw Error('NETWORK_FORBIDDEN'); },
    });
  await stream.result();
  if (fetchCalls || !payload) throw Error('Offline capture failed');
  // Explicitly freeze historically deployed sampling; current defaults are not evidence.
  Object.assign(payload,{top_p:0.95,top_k:20,presence_penalty:0,preserve_thinking:true});
  if (projection.thinkingLevel === 'off') { delete payload.reasoning_effort; payload.enable_thinking=false; }
  return {payload, projection, fetchCalls};
}
export function publicRow({id, sourceHash, target, payload, sourceName, entries}) {
  const body=JSON.stringify(payload); const lineage=[]; const byId=validateTree(entries,target.parentId); let p=target.parentId;
  while(p) {const e=byId.get(p);lineage.push({id:e.id,type:e.type});p=e.parentId;}
  return {id,source_name:sourceName,source_sha256:sourceHash,entry_id:target.id,parent_id:target.parentId,
    historical_timestamp:target.timestamp,historical_engine_identity:'ENGINE_IDENTITY_UNKNOWN',
    historical_prompt_tokens_usage:promptUsage(target),historical_output_tokens:target.message.usage?.output??null,
    historical_stop_reason:target.message.stopReason,qualification:'FROZEN_SESSION_DERIVED_REDACTED',
    payload_file:`${id}.json`,payload_sha256:hash(body),payload_bytes:Buffer.byteLength(body),
    message_count:payload.messages.length,tool_count:payload.tools?.length||0,
    max_tokens:payload.max_tokens,reasoning_effort:payload.reasoning_effort??null,
    budget_provenance:['f89c5dcc','97fc7be6'].includes(target.id)?'HISTORICAL_SERVER_VERIFIED_32768':'HISTORICAL_DEPLOYMENT_POLICY_32768_NOT_REQUEST_VERIFIED',
    lineage_sha256:hash(JSON.stringify(lineage)),lineage_events:lineage.length,
    compaction_count:lineage.filter(e=>e.type==='compaction').length,context_edit_count:lineage.filter(e=>e.type==='context_edit').length,
    mandatory_truncation:['f89c5dcc','97fc7be6'].includes(target.id),
    token_calibration:'PENDING_TARGET_TOKENIZER',tool_execution:false,network_calls_during_preparation:0};
}
export async function main() {
  const sessionRoot=process.env.PI_SESSION_ROOT || '/Users/luo/.pi/agent/sessions';
  const privateDir=resolve(process.env.PI_PRIVATE_CORPUS || '/tmp/ninfer-baseline-29-20261020-pi-private');
  if (!privateDir.startsWith('/tmp/') && !privateDir.startsWith('/private/tmp/')) throw Error('Private corpus must be under /tmp');
  await mkdir(privateDir,{recursive:true,mode:0o700}); await chmod(privateDir,0o700);
  const pi=await loadPi(); const rows=[]; const sources=[];
  for(const dir of (await readdir(sessionRoot,{withFileTypes:true})).filter(x=>x.isDirectory()).sort((a,b)=>a.name.localeCompare(b.name))) {
    for(const file of (await readdir(join(sessionRoot,dir.name))).filter(x=>x.endsWith('.jsonl')).sort()) {
      const bytes=await readFile(join(sessionRoot,dir.name,file));const entries=bytes.toString().split('\n').filter(Boolean).map(x=>JSON.parse(x));
      const selected=selectEntries(entries);if(!selected.length)continue;
      const sourceHash=hash(bytes);sources.push({name:file,sha256:sourceHash,selected_count:selected.length});
      for(const target of selected) {
        const id=`pi-${sourceHash.slice(0,12)}-${target.id}`;const captured=await capture(pi,entries,target);
        const preRedactionHash=hash(JSON.stringify(captured.payload));
        const {payload,redaction_count_by_kind}=redactWire(captured.payload);
        await writeFile(join(privateDir,`${id}.json`),JSON.stringify(payload),{mode:0o600});
        rows.push({...publicRow({id,sourceHash,target,payload,sourceName:file,entries}),pre_redaction_payload_sha256:preRedactionHash,post_redaction_payload_sha256:hash(JSON.stringify(payload)),redaction_count_by_kind});
      }
    }
  }
  for (const id of ['f89c5dcc','97fc7be6']) if(!rows.some(x=>x.entry_id===id)) throw Error('Missing mandatory truncation entry');
  const packageBytes=await readFile(join(PI_ROOT,'package.json'));
  const serializerFiles = ['dist/core/session-manager.js','dist/core/messages.js','node_modules/@earendil-works/pi-ai/dist/api/openai-completions.js','node_modules/@earendil-works/pi-ai/dist/utils/transcript.js','node_modules/@earendil-works/pi-ai/dist/utils/text.js'];
  const serializer_sha256 = Object.fromEntries(await Promise.all(serializerFiles.map(async name=>[name,hash(await readFile(join(PI_ROOT,name)))])));
  const result={schema_version:1,preparer_script_sha256:hash(await readFile(new URL(import.meta.url))),redaction_policy:REDACTION_POLICY,redaction_policy_sha256:hash(JSON.stringify(REDACTION_POLICY)),serializer_sha256,qualification:'FROZEN_SESSION_DERIVED_REDACTED',private_corpus_dir:privateDir,
    pi_version:JSON.parse(packageBytes).version,pi_package_sha256:hash(packageBytes),node_version:process.version,
    sources,cases:rows,case_count:rows.length,
    preparation_guards:{no_agent_started:true,no_tool_execution:true,no_network:true,source_sessions_read_only:true},
    unresolved:['Historical Pi serializer and dynamic sol-pi transform are unavailable. Canonical stored context edits/compactions/system sections/custom messages are projected by frozen current Pi; dynamic extension plan is not re-executed.',
      'Historical per-request budgets missing except two verified truncations; others explicitly freeze 32768 policy assumption.',
      'Actual rendered token lengths require post-redaction target tokenizer calibration; historical usage is selection metadata only. Redacted input is not historical exact.',
      'Engine identity cannot be established from model strings; this corpus is not historical speed evidence.',
      'Closed-loop Pi fixture runs are separate and have not run.'],
    closed_loop_fixture:'output/qwen38-4090-compare/scripts/run_pi_java.sh'};
  await writeFile(join(privateDir,'manifest.json'),JSON.stringify(result,null,2),{mode:0o600});
  await mkdir('output/ninfer-baseline-29-20261020',{recursive:true});
  await writeFile('output/ninfer-baseline-29-20261020/pi-preparation.json',JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify({case_count:rows.length,source_count:sources.length,private_corpus_dir:privateDir}));
}
if(process.argv[1] && resolve(process.argv[1])===resolve(new URL(import.meta.url).pathname)) await main();
