from __future__ import annotations
import json, re, math


def strict_json(text):
    """Parse standard JSON without duplicate keys or NaN/Infinity extensions."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('Nonfinite JSON number: ' + value)

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def typed_equal(actual, expected):
    """Exact fixture equality, including JSON representation types (false != 0)."""
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(typed_equal(actual[k], expected[k]) for k in actual)
    if isinstance(actual, list):
        return len(actual) == len(expected) and all(typed_equal(a, b) for a, b in zip(actual, expected))
    if isinstance(actual, float) and not math.isfinite(actual):
        return False
    return actual == expected


def score(case,r):
    if r.get('error'): return {'pass':False,'reason':r['error']}
    kind=case.get('kind','performance'); text=(r.get('text') or '').strip(); calls=r.get('tools') or []
    if kind=='performance':
        ok=not calls and r.get('finish_reason') in ('stop','length') and bool(text or r.get('reasoning'))
        return {'pass':ok,'reason':'performance completion' if ok else 'empty/error/tool output'}
    if r.get('finish_reason')=='length': return {'pass':False,'reason':'quality response truncated'}
    if kind in ('exact','no_tools','json'):
        if calls: return {'pass':False,'reason':'unexpected or unauthorized tool call'}
        if kind=='json':
            try: ok=typed_equal(strict_json(text),case['expected'])
            except ValueError: ok=False
        else: ok=text==str(case['expected'])
        return {'pass':ok,'reason':'exact visible answer' if ok else 'visible answer mismatch'}
    if kind=='tool':
        if r.get('finish_reason')!='tool_calls':return {'pass':False,'reason':'tool payload has wrong finish_reason'}
        expected=case['expected']; permitted={x['function']['name'] for x in case['body'].get('tools',[])}
        if len(calls)!=1: return {'pass':False,'reason':f'expected one tool; got {len(calls)}'}
        c=calls[0]['function']
        if c['name'] not in permitted: return {'pass':False,'reason':'unauthorized tool'}
        try: args=strict_json(c['arguments'])
        except ValueError: return {'pass':False,'reason':'invalid JSON arguments'}
        ok=c['name']==expected['name'] and typed_equal(args,expected['arguments'])
        return {'pass':ok,'reason':'tool schema + value match' if ok else 'tool name/arguments mismatch'}
    if kind=='java': return {'pass':None,'reason':'requires isolated javac execution','java_task':case['java_task']}
    raise ValueError(f'Unknown scorer kind {kind}')


def extract_java(text):
    blocks=re.findall(r'```(?:java)?\s*\n(.*?)```',text,re.S)
    code=blocks[0] if len(blocks)==1 else text
    if len(code)>100000 or 'class Solution' not in code: raise ValueError('Expected a bounded Java Solution class')
    return code
