from __future__ import annotations
import math, random, statistics, json, csv, re
from pathlib import Path
from .core import dump


def percentile(values,q):
    s=sorted(values); p=(len(s)-1)*q; lo=int(p); hi=min(lo+1,len(s)-1)
    return s[lo]+(s[hi]-s[lo])*(p-lo)


def paired(a,b,seed=20261023,draws=5000):
    if len(a)!=len(b) or not a: raise ValueError('Matched nonempty paired observations required')
    if any(x is None or not math.isfinite(x) or x<=0 for x in list(a)+list(b)): raise ValueError('Positive finite times required')
    ratios=[math.log(y/x) for x,y in zip(a,b)]
    estimate=100*(1-math.exp(statistics.mean(ratios)))
    rng=random.Random(seed)
    boot=[100*(1-math.exp(statistics.mean(rng.choices(ratios,k=len(ratios))))) for _ in range(draws)]
    return {'pairs':len(a),'improvement_pct':estimate,'ci95':[percentile(boot,.025),percentile(boot,.975)],
            'sufficient':len(a)>=5,'a_median':statistics.median(a),'b_median':statistics.median(b),
            'method':'paired run-level log-ratio bootstrap; lower time is better; no token-level resampling'}


STRATUM_FIELDS = ('group', 'cache_state', 'scenario', 'context_bucket')
TIME_METRICS = ('wall_s', 'ttft_s', 'visible_ttft_s', 'reasoning_ttft_s',
                'tool_ttft_s', 'prompt_ms', 'decode_ms')


def _stratum(item):
    return tuple(str(item.get(key, 'unspecified')) for key in STRATUM_FIELDS)


def _positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def summarize(folder, comparisons=None, metric=None):
    """Audit a planned experiment before computing paired, stratified time ratios.

    Old JSONL files remain readable. Without an a-priori plan and final audit
    receipt they are descriptive evidence only, never a complete campaign.
    Strata are never pooled; each fresh-engine round is one bootstrap unit.
    """
    folder = Path(folder)
    rows = [json.loads(line) for line in (folder/'requests.jsonl').read_text().splitlines() if line.strip()]
    measured = [row for row in rows if row.get('phase') == 'measured']
    plan_file = folder/'campaign.json'
    plan = json.loads(plan_file.read_text()) if plan_file.exists() else {}
    invalid = []
    if not plan:
        invalid.append('Missing campaign plan: observed rows cannot prove expected completeness')
    metric = metric or plan.get('primary_metric', 'wall_s')
    if metric not in TIME_METRICS:
        raise ValueError('Unsupported time metric: ' + str(metric))
    mode = plan.get('mode', 'LEGACY')
    default_arms = ['p', 'base'] if mode == 'MIGRATION' else ['base', 'cfg'] if mode == 'CONFIG' else ['base', 'off', 'on']
    arms = plan.get('arms', default_arms)
    if not isinstance(arms, list) or not arms or any(not isinstance(x,str) or not x for x in arms) or len(set(arms)) != len(arms):
        raise ValueError('Campaign arms must be unique nonempty strings')
    declared_pairs = plan.get('comparisons')
    if declared_pairs is None:
        declared_pairs = [['p','base']] if mode == 'MIGRATION' else [['base','cfg']] if mode == 'CONFIG' else [['base','off'],['off','on']]
    pairs = comparisons if comparisons is not None else declared_pairs
    if not isinstance(pairs,(list,tuple)) or any(not isinstance(p,(list,tuple)) or len(p)!=2 or p[0]==p[1] or any(a not in arms for a in p) for p in pairs):
        raise ValueError('Each comparison must name two distinct declared arms')
    if len({tuple(p) for p in pairs}) != len(pairs):
        raise ValueError('Duplicate comparison')
    exploratory = comparisons is not None and [list(p) for p in pairs] != declared_pairs
    exploratory = exploratory or metric != plan.get('primary_metric', 'wall_s')
    nrounds = plan.get('rounds')
    if type(nrounds) is not int or nrounds <= 0:
        invalid.append('Missing or invalid planned rounds')
        observed = [row.get('round') for row in measured if type(row.get('round')) is int and row['round'] >= 0]
        nrounds = max(observed, default=-1) + 1
    expected_rounds = list(range(nrounds))
    cases = plan.get('cases')
    if not cases:
        seen = {}
        for row in measured:
            if row.get('case_id') not in seen:
                seen[row.get('case_id')] = dict(id=row.get('case_id'), **{k:row.get(k,'unspecified') for k in STRATUM_FIELDS})
        ids = plan.get('case_ids', list(seen))
        cases = [seen.get(cid, {'id':cid}) for cid in ids]
        invalid.append('Missing planned case descriptors/request hashes; legacy rows are descriptive only')
    case_ids = [case.get('id') for case in cases]
    if not case_ids or any(not isinstance(x,str) or not x for x in case_ids) or len(set(case_ids)) != len(case_ids):
        raise ValueError('Planned case IDs must be unique nonempty strings')
    if plan.get('case_ids',case_ids) != case_ids:
        invalid.append('Campaign case_ids disagree with case descriptors')
    case_map = {case['id']:case for case in cases}
    if plan.get('schema_version') == 2:
        for case in cases:
            digest = case.get('request_sha256')
            if not isinstance(digest, str) or re.fullmatch(r'[0-9a-fA-F]{64}', digest) is None:
                invalid.append(f"case {case['id']!r}: missing or invalid planned request_sha256 (expected 64 hexadecimal characters)")
        receipt_file = folder/'COMPLETION.json'
        receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
        if receipt.get('state') != 'COMPLETE' or receipt.get('final_audit') != 'PASS':
            invalid.append('Missing or unsuccessful completion/final audit receipt')
    else:
        invalid.append('Legacy campaign lacks schema_version=2 completion contract')
    if (folder/'FAILURE.json').exists():
        invalid.append('Campaign FAILURE.json exists')

    indexed = {}
    by_run = {}
    for row in measured:
        key = (row.get('round'), row.get('arm'), row.get('case_id'))
        if type(key[0]) is not int or key[0] not in expected_rounds or key[1] not in arms or key[2] not in case_map:
            invalid.append('Unexpected round/arm/case: ' + repr(key))
            continue
        indexed.setdefault(key, []).append(row)
        by_run.setdefault(key[:2], []).append(row)
    valid = {}
    totals = []
    for rnd in expected_rounds:
        for arm in arms:
            rr = by_run.get((rnd,arm), [])
            actual_ids = [r['case_id'] for r in rr]
            if actual_ids != case_ids:
                invalid.append(f'round {rnd} arm {arm}: missing/duplicate/reordered planned cases')
            wall = [r.get('metrics',{}).get('wall_s') for r in rr]
            totals.append({'round':rnd,'arm':arm,'requests':len(rr),'wall_s':sum(wall) if all(_positive(x) for x in wall) else None,
                           'failures':sum(r.get('score',{}).get('pass') is False for r in rr),
                           'unscored':sum(r.get('score',{}).get('pass') is None for r in rr),'case_ids':actual_ids})
            for cid in case_ids:
                key = (rnd,arm,cid); matches = indexed.get(key,[]); reasons = []
                if len(matches) != 1:
                    invalid.append(f'{key}: expected one record, got {len(matches)} (missing/duplicate)')
                    valid[key] = False
                    continue
                row = matches[0]; case = case_map[cid]
                if row.get('score',{}).get('pass') is not True:reasons.append('failed or unscored')
                if not _positive(row.get('metrics',{}).get(metric)):reasons.append('missing/nonpositive/nonfinite metric '+metric)
                if not row.get('request_sha256'):reasons.append('missing request hash')
                if case.get('request_sha256') and case['request_sha256'] != row.get('request_sha256'):reasons.append('request hash differs from plan')
                if row.get('fixed_output_comparable') is False:reasons.append('fixed output not reached')
                if case.get('fixed_output') is not None:
                    if row.get('fixed_output_comparable') is not True or row.get('metrics',{}).get('generated_tokens') != case['fixed_output']:
                        reasons.append('fixed output length is not auditable/equal')
                if _stratum(row) != _stratum(case):reasons.append('workload stratum differs from plan')
                valid[key] = not reasons
                invalid.extend(f'{key}: {reason}' for reason in reasons)

    strata = {}
    for case in cases:strata.setdefault(_stratum(case), []).append(case['id'])
    stratum_reports = {}
    for stratum, ids in sorted(strata.items()):
        label = json.dumps(dict(zip(STRATUM_FIELDS,stratum)), ensure_ascii=False, sort_keys=True)
        results = {}
        for a,b in pairs:
            observations = []
            for rnd in expected_rounds:
                if not all(valid.get((rnd,arm,cid),False) for arm in (a,b) for cid in ids):continue
                aa = [indexed[(rnd,a,cid)][0] for cid in ids]
                bb = [indexed[(rnd,b,cid)][0] for cid in ids]
                if [r['request_sha256'] for r in aa] != [r['request_sha256'] for r in bb]:
                    invalid.append(f'round {rnd} {a}/{b}: frozen request hashes differ');continue
                observations.append((sum(r['metrics'][metric] for r in aa),sum(r['metrics'][metric] for r in bb)))
            results[a+'_vs_'+b] = paired([a for a,b in observations],[b for a,b in observations]) if observations else None
        stratum_reports[label] = results
    # The compatibility field is intentionally null for multi-stratum data.
    checks = {a+'_vs_'+b:None for a,b in pairs}
    if len(stratum_reports) == 1:checks.update(next(iter(stratum_reports.values())))
    failures = sum(row.get('score',{}).get('pass') is False for row in rows)
    unscored = sum(row.get('score',{}).get('pass') is None for row in rows)
    invalid = sorted(set(invalid))
    classified = all('unspecified' not in stratum for stratum in strata)
    decision = 'PAIRED_SCREEN_ONLY'
    if failures:decision = 'REJECT_OR_FIX'
    elif invalid or unscored:decision = 'INCOMPLETE_OR_INVALID'
    elif not pairs:decision = 'RECORD_ONLY'
    elif not classified:decision = 'DESCRIPTIVE_UNCLASSIFIED'
    elif exploratory:decision = 'EXPLORATORY_ONLY'
    elif mode == 'AA_NOISE':decision = 'NOISE_CONTROL_ONLY'
    elif len(strata)>1:decision = 'STRATIFIED_SCREEN_ONLY'
    elif mode == 'PR_EXPERIMENT':
        parity = checks.get('base_vs_off') or {}; upgrade = checks.get('off_vs_on') or {}
        if not parity.get('sufficient') or not upgrade.get('sufficient'):decision='INCONCLUSIVE'
        elif parity['ci95'][0] < -3 or parity['ci95'][1] > 3:decision='OFF_PATH_NOT_QUALIFIED'
        elif upgrade['improvement_pct']>=5 and upgrade['ci95'][0]>0:decision='CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION'
        else:decision='NO_ESTABLISHED_NET_BENEFIT'
    report = {'schema_version':2,'metric':metric,'decision':decision,'comparisons':checks,'strata_comparisons':stratum_reports,
              'group_comparisons_off_on':{label:values.get('off_vs_on') for label,values in stratum_reports.items()},
              'invalid_pairs':invalid,'failures':failures,'unscored':unscored,'runs':totals,'exploratory':exploratory,
              'warning':'No pooling across group/cache_state/scenario/context_bucket. SSE events are not tokens. Screening is not quality equivalence or deployment approval.'}
    dump(folder/'summary.json',report)
    flat=[]
    for row in rows:
        flat.append({k:row.get(k) for k in ('round','arm','case_id','phase',*STRATUM_FIELDS)} |
                    row.get('metrics',{}) | {'pass':row.get('score',{}).get('pass'),'reason':row.get('score',{}).get('reason')})
    if flat:
        with (folder/'requests.csv').open('w',newline='',encoding='utf-8-sig') as f:
            fields=list(dict.fromkeys(key for row in flat for key in row))
            writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(flat)
    lines=['# 实验统计报告','',f'判定：**{decision}**','',f'时间指标：`{metric}`。每一整轮为抽样单位；正值表示时间减少。',
           '', '冷暖、场景、上下文与分组分别报告；不生成混池的总体提速。']
    for label,values in stratum_reports.items():
        lines += ['', '## '+label, '', '| 对照 | 配对轮数 | 时间改善 | bootstrap 95% CI |','|---|---:|---:|---:|']
        for name,value in values.items():
            lines.append(f"| {name} | {value['pairs']} | {value['improvement_pct']:.2f}% | {value['ci95'][0]:.2f}% ～ {value['ci95'][1]:.2f}% |" if value else f'| {name} | 0 | 不可比较 | — |')
    lines += ['', '## 完整性审计', '', f'失败：{failures}；未评分：{unscored}。', '', *['- '+s for s in invalid], '', report['warning']]
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report
