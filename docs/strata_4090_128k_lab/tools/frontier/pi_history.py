"""Derive a secret-redacted request from a Pi parent chain before any compaction.

This is a documented projection, not a captured HTTP request or live tool runner.
"""
import copy
import hashlib
import json
from pathlib import Path
import re


def sha_bytes(value):return hashlib.sha256(value).hexdigest()
def hash_json(value):return sha_bytes(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())

def sanitize(text,counts):
    rules=[('home',re.compile(r'/Users/luo(?=/|\b)'),'/workspace/user'),
           ('bearer',re.compile(r'(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}'),'Bearer [REDACTED]'),
           ('key',re.compile(r'\bsk-[A-Za-z0-9_-]{16,}'),'[REDACTED_KEY]'),
           ('credential_assignment',re.compile(r'''(?im)(["']?(?:api[_-]?key|access[_-]?token|password|passwd|secret)["']?\s*[:=]\s*)(["'])([^\n"']{8,})\2'''),r'\1"[REDACTED]"')]
    rules.append(('unquoted_credential',re.compile(r'''(?im)(\b(?:export\s+)?(?:[A-Z_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|PASSWORD|PASSWD|SECRET)[A-Z_]*|apiKey|accessToken)\s*[:=]\s*)(?![\"'\s\[])([^\s;#,}\]]{8,})'''),r'\1[REDACTED]'))
    rules.append(('url_credential',re.compile(r'(https?://)[^/@\s:]+:[^/@\s]+@'),r'\1[REDACTED]@'))
    for name,pattern,replacement in rules:
        text,n=pattern.subn(replacement,text);counts[name]=counts.get(name,0)+n
    return text


def project_session(path:Path,before_assistant_id:str):
    raw=Path(path).read_bytes();rows=[json.loads(x) for x in raw.splitlines() if x.strip()]
    by_id={r['id']:r for r in rows if 'id' in r}
    target=by_id[before_assistant_id]
    if target.get('message',{}).get('role')!='assistant':raise ValueError('ASSISTANT_BOUNDARY_REQUIRED')
    branch=[];node=target.get('parentId');seen=set()
    while node is not None:
        if node in seen or node not in by_id:raise ValueError('BROKEN_PARENT_CHAIN')
        seen.add(node);row=by_id[node];branch.append(row);node=row.get('parentId')
    branch.reverse()
    if any(r.get('type')=='compaction' for r in branch):raise ValueError('COMPACTION_REPLAY_NOT_IMPLEMENTED')
    sections={};tools={};messages=[];mapping=[];redactions={};pending=set()
    for row in branch:
        if row.get('type')!='message':continue
        msg=row['message'];role=msg['role'];content=msg.get('content',[])
        if role=='system':
            sections.update(msg.get('sections',{}))
            for t in msg.get('toolsAdded',[]):tools[t['name']]=t
            for name in msg.get('toolsRemoved',[]):tools.pop(name,None)
            mapping.append({'entry_id':row['id'],'role':role,'projection':'sections delta merged; tool registry updated'});continue
        result={'role':'tool' if role=='toolResult' else role}
        blocks=content if isinstance(content,list) else [{'type':'text','text':content}]
        allowed={'assistant':{'text','thinking','toolCall'},'user':{'text'},'toolResult':{'text'}}.get(role,set())
        if any(not isinstance(b,dict) or b.get('type') not in allowed for b in blocks):
            raise ValueError('UNSUPPORTED_CONTENT_BLOCK')
        result['content']='\n'.join(b.get('text','') for b in blocks if b.get('type')=='text')
        if role=='assistant':
            calls=[{'id':b['id'],'type':'function','function':{'name':b['name'],'arguments':json.dumps(b['arguments'],ensure_ascii=False,separators=(',',':'))}} for b in blocks if b.get('type')=='toolCall']
            thinking='\n'.join(b.get('thinking','') for b in blocks if b.get('type')=='thinking')
            if calls:result['tool_calls']=calls;pending.update(c['id'] for c in calls)
            if thinking:result['reasoning_content']=thinking
        elif role=='toolResult':
            call=msg['toolCallId']
            if call not in pending:raise ValueError('ORPHAN_TOOL_RESULT')
            pending.remove(call);result['tool_call_id']=call
        elif role!='user':raise ValueError('UNSUPPORTED_ROLE')
        messages.append(result);mapping.append({'entry_id':row['id'],'role':role,'projected_message_index':len(messages)})
    if pending:raise ValueError('INCOMPLETE_TOOL_CYCLE')
    system='\n\n'.join(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False) for v in sections.values())
    body={'model':'strata','messages':[{'role':'system','content':system}]+messages,'tools':[{'type':'function','function':{k:t[k] for k in ('name','description','parameters') if k in t}} for t in tools.values()],
          'tool_choice':'none','temperature':1.0,'top_p':0.95,'top_k':20,'seed':20261030,'reasoning_effort':'xhigh','max_tokens':2048,'stream':True,'chat_template_kwargs':{'preserve_thinking':False}}
    def clean(value):
        if isinstance(value,str):return sanitize(value,redactions)
        if isinstance(value,list):return [clean(v) for v in value]
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
        return value
    body=clean(body)
    provenance={'schema_version':1,'source_session_id':rows[0]['id'],'source_file_sha256':sha_bytes(raw),'source_file_bytes':len(raw),'before_assistant_entry_id':before_assistant_id,'branch_entry_ids':[x['id'] for x in branch], 'mapping':mapping,'redactions':redactions,'request_body_sha256':hash_json(body),'projection':'Pi parent chain before compaction; system sections merged; tools mapped to OpenAI; tool_choice none prevents tool execution','wire_capture':False,'pt_policy':'retain real history; server PT0 omits prior thinking','limitations':['Original Pi transport normalization not independently reconstructed','tool_choice none is a diagnostic request constraint, not original task replay','Historical completion is excluded; new prime completion must be generated and appended unmodified']}
    return body,provenance
