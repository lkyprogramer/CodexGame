#!/usr/bin/env python3
"""Offline paired binary noninferiority gate. Standard library only; no release gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


ALPHA = 0.025  # Each marginal one-sided bound; Bonferroni joint coverage >= .95.
FAILURE_KINDS = {'none', 'model_oracle', 'task_budget_exhausted',
                 'infrastructure', 'infrastructure_timeout', 'oom', 'crash'}
PAIR_FIELDS = {'task_id', 'baseline_success', 'candidate_success', 'run_valid', 'failure_kind'}
CELL_NAMES = ('both_success', 'baseline_only_success', 'candidate_only_success', 'both_fail')


def _validate_binomial(k, n, p=None):
    if type(n) is not int or n < 1 or type(k) is not int:
        raise ValueError('Binomial counts must be integers with n >= 1')
    if p is not None and (type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1):
        raise ValueError('Probability must be finite in [0, 1]')


def _log_comb(n, k):
    small = min(k, n-k)
    if small <= 64:
        # Avoid cancellation between three large lgamma terms in rare-event tails.
        return math.fsum(math.log(n-small+i)-math.log(i) for i in range(1, small+1))
    return math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)


def binomial_cdf(k, n, p):
    """P[Binomial(n,p) <= k], summing the smaller tail relative to its largest term.

    This avoids beginning a central/upper tail with (1-p)**n, which may underflow.
    expm1 preserves accuracy when taking a complement near zero.
    """
    _validate_binomial(k, n, p)
    if k < 0:return 0.0
    if k >= n:return 1.0
    if p == 0:return 1.0
    if p == 1:return 0.0
    lower = k < n*p
    boundary = k if lower else k+1
    log_mass = _log_comb(n, boundary)+boundary*math.log(p)+(n-boundary)*math.log1p(-p)
    terms = [1.0];term = 1.0
    if lower:
        for j in range(boundary, 0, -1):
            term *= j/(n-j+1)*(1-p)/p
            if term == 0:break
            terms.append(term)
    else:
        for j in range(boundary, n):
            term *= (n-j)/(j+1)*p/(1-p)
            if term == 0:break
            terms.append(term)
    log_tail = min(0.0, log_mass+math.log(math.fsum(terms)))
    value = math.exp(log_tail) if lower else -math.expm1(log_tail)
    return min(1.0, max(0.0, value))


def _validate_cp(k, n, alpha):
    _validate_binomial(k, n, alpha)
    if not 0 <= k <= n or not 0 < alpha < .5:
        raise ValueError('CP needs 0 <= k <= n and 0 < alpha < .5')


def upper_cp(k, n, alpha=ALPHA):
    """One-sided Clopper-Pearson upper bound, with tail probability alpha."""
    _validate_cp(k, n, alpha)
    if k == n:return 1.0
    if k == 0:return math.nextafter(-math.expm1(math.log(alpha)/n), 1.0)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo+hi)/2
        if mid == lo or mid == hi:break
        if binomial_cdf(k, n, mid) > alpha:lo = mid
        else:hi = mid
    return math.nextafter(hi, 1.0)


def lower_cp(k, n, alpha=ALPHA):
    """One-sided Clopper-Pearson lower bound, with tail probability alpha."""
    _validate_cp(k, n, alpha)
    if k == 0:return 0.0
    if k == n:return math.nextafter(math.exp(math.log(alpha)/n), 0.0)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo+hi)/2
        if mid == lo or mid == hi:break
        if binomial_cdf(k-1, n, mid) > 1-alpha:lo = mid
        else:hi = mid
    return math.nextafter(lo, 0.0)


def _cell(baseline, candidate):
    return 'both_success' if baseline and candidate else 'baseline_only_success' if baseline else 'candidate_only_success' if candidate else 'both_fail'


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def evaluate(data):
    """Validate all preregistered task pairs, then evaluate relative success NI.

    Invalid/duplicate/infrastructure rows are visible but never salvage an NI claim.
    Multiple seeds must have been aggregated to ONE binary outcome per task per arm.
    """
    errors=[];hard=[];excluded=[];raw_table=dict.fromkeys(CELL_NAMES,0);table=dict.fromkeys(CELL_NAMES,0)
    if not isinstance(data,dict):data={};errors.append('Input must be an object')
    if type(data.get('schema_version')) is not int or data.get('schema_version')!=1:errors.append('schema_version must be 1')
    plan=data.get('preregistration')
    if not isinstance(plan,dict):plan={};errors.append('Missing preregistration object')
    if plan.get('unit')!='independent_task':errors.append('Inference unit must be independent_task')
    if plan.get('aggregation')!='one_pair_per_task':errors.append('Multiple seeds require preregistered aggregation to one_pair_per_task')
    expected=plan.get('task_ids')
    if not isinstance(expected,list) or not expected or any(not isinstance(x,str) or not x.strip() for x in expected):
        errors.append('Preregistered task_ids must be a nonempty list of identifiers');expected=[]
    if len(set(expected))!=len(expected):errors.append('Duplicate preregistered task IDs')
    expected_set=set(expected)
    margin=plan.get('margin',.02)
    if type(margin) not in (float,int) or not math.isfinite(margin) or not 0<=margin<1:
        errors.append('Preregistered margin must be finite in [0,1)');margin=None
    rows=data.get('pairs')
    if not isinstance(rows,list):rows=[];errors.append('pairs must be a list')
    id_counts=Counter(row.get('task_id') for row in rows if isinstance(row,dict) and isinstance(row.get('task_id'),str))
    missing=sorted(expected_set-set(id_counts));extra=sorted(set(id_counts)-expected_set)
    if missing:errors.append('Missing preregistered tasks: '+', '.join(missing))
    if extra:errors.append('Unexpected tasks: '+', '.join(extra))
    for task_id,count in id_counts.items():
        if count!=1:errors.append(f'Duplicate task_id {task_id}: {count} rows; seeds are not independent tasks')
    kinds=Counter();valid_ids=[]
    for index,row in enumerate(rows):
        reasons=[]
        if not isinstance(row,dict):
            errors.append(f'row {index}: expected object');excluded.append({'row':index,'reasons':['not an object']});continue
        task_id=row.get('task_id');kind=row.get('failure_kind')
        if isinstance(kind,str):kinds[kind]+=1
        if kind in ('oom','crash'):hard.append({'row':index,'task_id':task_id,'failure_kind':kind})
        if set(row)!=PAIR_FIELDS:reasons.append('exactly the five pair fields are required; raw seed/timing rows must be preaggregated')
        if not isinstance(task_id,str) or task_id not in expected_set:reasons.append('undeclared or malformed task_id')
        elif id_counts[task_id]!=1:reasons.append('duplicate task_id')
        booleans=all(type(row.get(key)) is bool for key in ('baseline_success','candidate_success','run_valid'))
        if not booleans:reasons.append('success and run_valid must be JSON booleans')
        if type(row.get('baseline_success')) is bool and type(row.get('candidate_success')) is bool:
            raw_table[_cell(row['baseline_success'],row['candidate_success'])]+=1
        if not isinstance(kind,str) or kind not in FAILURE_KINDS:reasons.append('unknown failure_kind')
        if row.get('run_valid') is not True:reasons.append('run_valid is not true')
        if kind in ('infrastructure','infrastructure_timeout'):reasons.append('infrastructure failure invalidates experiment qualification')
        if kind in ('oom','crash'):reasons.append('OOM/crash is a hard rejection')
        if booleans:
            both_success=row['baseline_success'] and row['candidate_success']
            if kind=='none' and not both_success:reasons.append('failed oracle requires an explicit failure_kind')
            if kind in ('model_oracle','task_budget_exhausted') and both_success:reasons.append('failure_kind contradicts two successful outcomes')
        if reasons:
            errors.extend(f'row {index} task {task_id}: {reason}' for reason in reasons)
            excluded.append({'row':index,'task_id':task_id,'reasons':reasons})
        else:
            table[_cell(row['baseline_success'],row['candidate_success'])]+=1
            valid_ids.append(task_id)
    n=sum(table.values());inference=None
    status='HARD_REJECT' if hard else 'INVALID_EXPERIMENT' if errors else 'NONINFERIORITY_NOT_ESTABLISHED'
    if not errors and not hard:
        if n!=len(expected) or n==0:
            errors.append('All preregistered independent pairs must be present and valid');status='INVALID_EXPERIMENT'
        else:
            b=table['baseline_only_success'];c=table['candidate_only_success']
            upper_loss=upper_cp(b,n);lower_gain=lower_cp(c,n);upper_harm=upper_loss-lower_gain
            inference={'n':n,'b_baseline_only_success':b,'c_candidate_only_success':c,
                       'estimated_harm':(b-c)/n,'upper_loss_probability':upper_loss,'lower_gain_probability':lower_gain,
                       'upper_harm':upper_harm,'margin':margin,'one_sided_alpha_each':ALPHA,
                       'joint_confidence_at_least':1-2*ALPHA,
                       'method':'upperCP(b,n,alpha=.025) - lowerCP(c,n,alpha=.025); Bonferroni marginal bounds'}
            if upper_harm<=margin:status='NONINFERIORITY_ESTABLISHED'
    try:plan_sha=_digest(plan)
    except (ValueError,TypeError):plan_sha=None
    return {'schema_version':1,'status':status,'scope':'relative paired binary-success noninferiority only',
            'n_preregistered_tasks':len(expected),'n_input_rows':len(rows),'n_valid_pairs':n,
            'paired_outcome_table':table,'raw_outcome_table_including_invalid_rows':raw_table,
            'baseline_success_rate':(table['both_success']+table['baseline_only_success'])/n if n else None,
            'candidate_success_rate':(table['both_success']+table['candidate_only_success'])/n if n else None,
            'inference':inference,'margin':margin,'errors':errors,'hard_failures':hard,'excluded_from_inference':excluded,
            'failure_kind_counts':dict(kinds),'preregistration_sha256':plan_sha,
            'independence':'declared independent tasks; unique IDs do not prove independence or prior registration',
            'absolute_quality_gate':'NOT_EVALUATED','performance_gate':'NOT_EVALUATED','restricted_time_gate':'NOT_IMPLEMENTED',
            'deployment_approved':False,
            'limitations':['Repeated seeds/turns from the same task cannot increase N; use a frozen aggregation rule before this input.',
                           'Any missing, duplicate, invalid, or infrastructure-failed task invalidates the entire experiment; no survivor-only NI claim.',
                           'Both arms can be equally poor. Relative NI does not establish an absolute success target, safety, speed, or release readiness.',
                           'The confidence guarantee assumes independent identically sampled task pairs from the preregistered target distribution; reused/adaptively selected tasks need separate analysis.']}


def strict_loads(text):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate JSON key: '+key)
            result[key]=value
        return result
    def constant(value):raise ValueError('Nonfinite JSON value: '+value)
    def finite_float(value):
        number=float(value)
        if not math.isfinite(number):raise ValueError('Nonfinite JSON numeric overflow: '+value)
        return number
    return json.loads(text,object_pairs_hook=pairs,parse_constant=constant,parse_float=finite_float)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,help='Preregistered task-pair JSON; no service or GPU is contacted')
    parser.add_argument('--output',help='Optional JSON report path')
    args=parser.parse_args(argv)
    try:
        raw=Path(args.input).read_bytes();report=evaluate(strict_loads(raw.decode('utf-8')))
        report['input_sha256']=hashlib.sha256(raw).hexdigest()
    except (OSError,UnicodeError,ValueError,TypeError) as error:
        report={'schema_version':1,'status':'INVALID_INPUT','errors':[str(error)],'deployment_approved':False}
    output=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if args.output:
        destination=Path(args.output);destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(output,encoding='utf-8')
    print(output,end='')
    return {'NONINFERIORITY_ESTABLISHED':0,'NONINFERIORITY_NOT_ESTABLISHED':1,'HARD_REJECT':3}.get(report['status'],2)


if __name__=='__main__':raise SystemExit(main())
