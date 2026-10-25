from __future__ import annotations
import math, random, statistics, json, csv
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


def summarize(folder):
    folder=Path(folder)
    rows=[json.loads(x) for x in (folder/'requests.jsonl').read_text().splitlines() if x.strip()]
    by={}
    for r in rows:
        if r.get('phase')!='measured': continue
        by.setdefault((r['round'],r['arm']),[]).append(r)
    arms=sorted({k[1] for k in by}); rounds=sorted({k[0] for k in by})
    totals=[]
    for (rnd,arm),rr in sorted(by.items()):
        totals.append({'round':rnd,'arm':arm,'requests':len(rr),'wall_s':sum(x['metrics']['wall_s'] for x in rr),
                       'failures':sum(x['score'].get('pass') is False for x in rr),
                       'unscored':sum(x['score'].get('pass') is None for x in rr),
                       'case_ids':[x['case_id'] for x in rr],
                       'request_hashes':[x.get('request_sha256') for x in rr],
                       'fixed_output_comparable':all(x.get('fixed_output_comparable',True) for x in rr),
                       'prompt_tokens':[x['metrics'].get('prompt_tokens') for x in rr]})
    checks={}; invalid=[]
    for a,b in [('base','off'),('off','on')]:
        pairs=[]
        for rnd in rounds:
            aa=next((r for r in totals if r['round']==rnd and r['arm']==a),None)
            bb=next((r for r in totals if r['round']==rnd and r['arm']==b),None)
            if not aa or not bb: invalid.append(f'round {rnd}: missing {a}/{b}'); continue
            if aa['case_ids']!=bb['case_ids']: invalid.append(f'round {rnd}: case set/order differs'); continue
            if aa['request_hashes']!=bb['request_hashes']: invalid.append(f'round {rnd}: frozen request hashes differ'); continue
            if not aa['fixed_output_comparable'] or not bb['fixed_output_comparable']: invalid.append(f'round {rnd}: fixed output length not reached'); continue
            if aa['failures'] or bb['failures'] or aa['unscored'] or bb['unscored']:
                invalid.append(f'round {rnd}: failed/unscored requests in {a}/{b}'); continue
            pairs.append((aa['wall_s'],bb['wall_s']))
        checks[a+'_vs_'+b]=paired([x[0] for x in pairs],[x[1] for x in pairs]) if pairs else None
    safety=[r for r in rows if r.get('score',{}).get('pass') is False]
    upgrade=(checks.get('off_vs_on') or {})
    parity=(checks.get('base_vs_off') or {})
    decision='INCONCLUSIVE'
    if safety: decision='REJECT_OR_FIX'
    elif upgrade.get('sufficient') and parity.get('sufficient') and not invalid:
        if parity['ci95'][0] < -3 or parity['ci95'][1] > 3: decision='OFF_PATH_NOT_QUALIFIED'
        elif upgrade['improvement_pct']>=5 and upgrade['ci95'][0]>0: decision='CANDIDATE_FOR_HOLDOUT_NOT_PRODUCTION'
        else: decision='NO_ESTABLISHED_NET_BENEFIT'
    group_reports={}
    for group in sorted({r.get('group','unknown') for r in rows}):
        pairs=[]
        for rnd in rounds:
            aa=[r for r in by.get((rnd,'off'),[]) if r.get('group')==group]
            bb=[r for r in by.get((rnd,'on'),[]) if r.get('group')==group]
            if not aa or not bb: continue
            if [r.get('request_sha256') for r in aa]!=[r.get('request_sha256') for r in bb]:continue
            if any(r['score'].get('pass') is not True or not r.get('fixed_output_comparable',True) for r in aa+bb):continue
            pairs.append((sum(r['metrics']['wall_s'] for r in aa),sum(r['metrics']['wall_s'] for r in bb)))
        group_reports[group]=paired([a for a,b in pairs],[b for a,b in pairs]) if pairs else None
    campaign_file=folder/'campaign.json'
    if campaign_file.exists() and json.loads(campaign_file.read_text()).get('mode')=='AA_NOISE':decision='NOISE_CONTROL_ONLY'
    report={'group_comparisons_off_on':group_reports,'decision':decision,'comparisons':checks,'invalid_pairs':invalid,'failures':len(safety),'runs':totals,
            'warning':'A screening result is not proof of quality equivalence or production readiness. Run held-out tasks and PR-specific gates.'}
    dump(folder/'summary.json',report)
    flat=[]
    for r in rows: flat.append({k:v for k,v in r.items() if k in ('round','arm','case_id','phase')} | r.get('metrics',{}) | {'pass':r['score'].get('pass'),'reason':r['score'].get('reason')})
    if flat:
        with (folder/'requests.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    lines=['# 实验统计报告','',f"判定：**{decision}**",'', '| 对照 | 配对轮数 | 耗时改善 | 95% CI |','|---|---:|---:|---:|']
    for name,x in checks.items():
        if x: lines.append(f"| {name} | {x['pairs']} | {x['improvement_pct']:.2f}% | {x['ci95'][0]:.2f}% ～ {x['ci95'][1]:.2f}% |")
        else: lines.append(f'| {name} | 0 | 未形成有效配对 | — |')
    lines+=['','## 分场景耗时（off → on）','','| 分组 | 配对数 | 改善 | 95% CI |','|---|---:|---:|---:|']
    for name,x in group_reports.items():
        if x:lines.append(f"| {name} | {x['pairs']} | {x['improvement_pct']:.2f}% | {x['ci95'][0]:.2f}% ～ {x['ci95'][1]:.2f}% |")
        else:lines.append(f'| {name} | 0 | 不可比较 | — |')
    lines+=['','失败请求：'+str(len(safety)), '', '## 不可比较 / 缺失',*['- '+x for x in invalid], '',
            '本报告以整轮为抽样单位，保留失败记录；不以流式 chunk 数代替 token，不混合冷读与热缓存速度。',
            '通过此筛选仍需独立留出集、长时稳定性和 PR 专项验收，不能自动覆盖生产。']
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report
