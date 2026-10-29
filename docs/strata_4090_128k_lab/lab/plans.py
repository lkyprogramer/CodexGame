"""Offline plan checks only. No engine session/park/restore adapter is shipped."""
from .core import check_budget, hash_obj


REQUIRED_RECEIPTS = {
    'request_sha256', 'session_identity', 'usage_prompt_tokens', 'usage_completion_tokens',
    'park_count', 'restore_count', 'evict_count', 'snapshot_bytes', 'heap_rss_mib',
    'mem_available_mib', 'swap_mib', 'read_tokens', 'reused_tokens', 'ttft_s',
    'park_ms', 'restore_ms', 'trim_ms', 'quality_assertion',
}
EVENTS = {'park', 'restore', 'evict', 'refuse', 'cancel', 'capture'}


def validate_plan(plan):
    if not isinstance(plan,dict) or plan.get('schema_version')!=1 or plan.get('kind')!='park_restore':
        raise ValueError('Expected schema_version=1, kind=park_restore')
    if plan.get('engine_adapter') is not None:
        raise ValueError('Only offline plans are supported; the engine adapter is NOT_IMPLEMENTED')
    if plan.get('max_context')!=131072 or type(plan.get('max_context')) is not int:
        raise ValueError('Total context must be exactly 131072, including template/history/output')
    if type(plan.get('safety_tokens')) is not int or plan['safety_tokens']<4096:
        raise ValueError('Offline plan must reserve at least 4096 tokens')
    if type(plan.get('min_available_mib')) is not int or plan['min_available_mib']<4096:
        raise ValueError('Host memory safety gate must be at least 4096 MiB')
    if type(plan.get('max_active_gpu_contexts')) is not int or plan['max_active_gpu_contexts']!=1:
        raise ValueError('Exactly one active GPU context is allowed')
    sessions=plan.get('sessions')
    if not isinstance(sessions,list) or len(sessions)<2 or any(not isinstance(s,str) or not s for s in sessions) or len(set(sessions))!=len(sessions):
        raise ValueError('At least two unique session identifiers are required')
    receipts=plan.get('required_receipts')
    if not isinstance(receipts,list) or any(not isinstance(x,str) for x in receipts) or not REQUIRED_RECEIPTS.issubset(receipts):
        raise ValueError('Missing request/quality/park/restore/memory evidence receipts')
    steps=plan.get('steps')
    if not isinstance(steps,list) or len(steps)<3:raise ValueError('Need an explicit session-switch-and-restore sequence')
    ids=set();seen=set();previous=None;restore_seen=False;park_seen=False;hashes=[]
    for step in steps:
        if not isinstance(step,dict):raise ValueError('Each step must be an object')
        sid=step.get('session');step_id=step.get('id')
        if not isinstance(step_id,str) or not step_id or step_id in ids:raise ValueError('Step IDs must be unique nonempty strings')
        ids.add(step_id)
        if sid not in sessions:raise ValueError('Step uses an undeclared session')
        request=step.get('request')
        if not isinstance(request,dict) or not isinstance(request.get('messages'),list) or not request['messages']:
            raise ValueError('Each step must embed a frozen nonempty request transcript')
        for message in request['messages']:
            if not isinstance(message,dict) or message.get('role') not in ('system','user','assistant','tool','developer'):
                raise ValueError('Malformed request message')
        check_budget(step.get('counted_prompt_tokens'),request.get('max_tokens'),plan['max_context'],plan['safety_tokens'])
        events=step.get('expected_events')
        if not isinstance(events,list) or any(e not in EVENTS for e in events):raise ValueError('Unknown expected mechanism event')
        if 'restore' in events:
            if sid not in seen or sid==previous:raise ValueError('Restore must revisit a prior session after switching away')
            restore_seen=True
        if 'park' in events:
            if previous is None or previous==sid:raise ValueError('Park must occur across a session switch')
            park_seen=True
        hashes.append({'step_id':step_id,'session':sid,'request_sha256':hash_obj(request)})
        seen.add(sid);previous=sid
    if not restore_seen or not park_seen:raise ValueError('Plan must explicitly expect both park and restore events')
    return {'status':'OFFLINE_PLAN_VALID','steps':len(steps),'sessions':len(sessions),
            'request_hashes':hashes,'plan_sha256':hash_obj(plan),
            'live_ready':False,'tokenizer_verified':False,'execution_result':'NOT_RUN',
            'engine_adapter':'NOT_IMPLEMENTED',
            'limitations':['Declared token counts were range-checked, not recomputed by the model tokenizer.',
                           'No request was sent; no parking, restoring, memory bound, or quality assertion was executed.',
                           'A reviewed engine session adapter and actual event receipts are required before any mechanism claim.']}
