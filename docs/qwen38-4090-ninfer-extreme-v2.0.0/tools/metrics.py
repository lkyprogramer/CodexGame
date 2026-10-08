"""Strict weighted accounting and paired statistics. No fabricated backend metrics."""
import math,random,statistics

# Protected context capacity (input+output+template). Lowered from 262144 to 200192 by owner
# decision on 2026-09-09 to free ~1.6 GiB VRAM for the DFlash2 W8 companion; see docs/02 §3.
PROTECTED_CAPACITY=200192
# Gate-grade paired evidence: at least this many ABBA pairs (docs/02 §3). Percentile bootstrap on
# n=5 has only 3125 distinct resamples and understates the interval; n>=8 plus a t-interval is the floor.
MIN_GATE_PAIRS=8
# A/A (baseline vs baseline) |ratio-1| above this means the harness itself is too noisy to read a 3% gate.
MAX_AA_NOISE_ABS=0.03
# Two-sided 95% Student-t quantiles by degrees of freedom; the largest tabulated df <= actual df is used.
_T975={1:12.706,2:4.303,3:3.182,4:2.776,5:2.571,6:2.447,7:2.365,8:2.306,9:2.262,10:2.228,11:2.201,12:2.179,13:2.160,14:2.145,15:2.131,16:2.120,17:2.110,18:2.101,19:2.093,20:2.086,21:2.080,22:2.074,23:2.069,24:2.064,25:2.060,26:2.056,27:2.052,28:2.048,29:2.045,30:2.042,40:2.021,60:2.000,120:1.980}

def _t975(df):
    keys=[k for k in _T975 if k<=df]
    return _T975[max(keys)] if keys else 1.960

def aggregate_rounds(rows):
    if not rows: raise ValueError('no round records')
    total={k:0 for k in ['proposed','accepted','licensed','committed']}; elapsed=0.
    for r in rows:
        if r.get('profiled',False): raise ValueError('profiling samples cannot be throughput evidence')
        vals={k:r[k] for k in total}
        if any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in vals.values()): raise ValueError('integer counts required')
        if vals['accepted']>vals['proposed'] or vals['licensed']!=vals['accepted']+1 or vals['committed']>vals['licensed']:
            raise ValueError('count contract violated')
        t=float(r['round_ms'])
        if not math.isfinite(t) or t<=0: raise ValueError('positive end-to-end round_ms required')
        elapsed+=t
        for k in total: total[k]+=vals[k]
    return dict(total,rounds=len(rows),round_ms=elapsed,al_committed=total['committed']/len(rows),al_licensed=total['licensed']/len(rows),acceptance=total['accepted']/total['proposed'] if total['proposed'] else None,tps=total['committed']/(elapsed/1000.))

def paired_summary(base,candidate,draws=3000,min_pairs=MIN_GATE_PAIRS):
    """Paired log-ratio summary. ci95 is the more conservative of percentile bootstrap and Student-t.
    min_pairs<MIN_GATE_PAIRS is allowed for pilots only; the result then carries gate_grade=False."""
    if len(base)!=len(candidate) or len(base)<max(3,min_pairs): raise ValueError('at least %d aligned pairs required'%max(3,min_pairs))
    if any(not math.isfinite(float(x)) or x<=0 for x in list(base)+list(candidate)): raise ValueError('positive finite rates required')
    logs=[math.log(b/a) for a,b in zip(base,candidate)]
    rng=random.Random(4090); n=len(logs); mean=statistics.mean(logs)
    boot=sorted(math.exp(sum(logs[rng.randrange(n)] for _ in range(n))/n) for _ in range(draws))
    boot_low,boot_high=boot[int(.025*draws)],boot[min(draws-1,int(.975*draws))]
    sd=statistics.stdev(logs) if n>1 else 0.; half=_t975(n-1)*sd/math.sqrt(n)
    t_low,t_high=math.exp(mean-half),math.exp(mean+half)
    return dict(n=n,ratio=math.exp(mean),ci95_low=min(boot_low,t_low),ci95_high=max(boot_high,t_high),
                bootstrap_ci95=[boot_low,boot_high],t_ci95=[t_low,t_high],gate_grade=n>=MIN_GATE_PAIRS,seed=4090)

def candidate_gate(d):
    required=['quality_pass','state_pass','sampling_pass','artifact_pass','paired_gain_lcb','paired_n','aa_noise_abs','task_wall_ratio','capacity','headroom_mib','ooms','heldout_complete','measurement_complete']
    missing=[k for k in required if k not in d or d[k] is None]
    if missing: return dict(verdict='BLOCKED',reasons=['missing:'+','.join(missing)])
    numeric=['paired_gain_lcb','paired_n','aa_noise_abs','task_wall_ratio','capacity','headroom_mib','ooms']
    if any(isinstance(d[k],bool) or not isinstance(d[k],(int,float)) or not math.isfinite(d[k]) for k in numeric):
        return dict(verdict='BLOCKED',reasons=['invalid numeric evidence'])
    if any(type(d[k]) is not bool for k in ['quality_pass','state_pass','sampling_pass','artifact_pass','heldout_complete','measurement_complete']):
        return dict(verdict='BLOCKED',reasons=['invalid boolean evidence'])
    if d['capacity']<=0 or d['headroom_mib']<0 or d['ooms']<0 or d['task_wall_ratio']<=0 or d['paired_n']<0 or d['aa_noise_abs']<0:
        return dict(verdict='BLOCKED',reasons=['out-of-range evidence'])
    if d['paired_n']<MIN_GATE_PAIRS: return dict(verdict='BLOCKED',reasons=['insufficient paired samples (<%d)'%MIN_GATE_PAIRS])
    if d['aa_noise_abs']>MAX_AA_NOISE_ABS: return dict(verdict='BLOCKED',reasons=['A/A noise floor exceeds %.0f%%; measurement chain unreliable'%(MAX_AA_NOISE_ABS*100)])
    reasons=[]
    for k in ['quality_pass','state_pass','sampling_pass','artifact_pass']:
        if d[k] is not True: reasons.append(k)
    if not d['measurement_complete'] or not d['heldout_complete']: return dict(verdict='BLOCKED',reasons=['incomplete evidence'])
    if d['ooms']!=0 or d['headroom_mib']<512: reasons.append('memory/oom')
    if reasons: return dict(verdict='NO_GO',reasons=reasons)
    if d['capacity']<PROTECTED_CAPACITY: return dict(verdict='TRADEOFF_ONLY',reasons=['protected %d capacity not retained'%PROTECTED_CAPACITY])
    if d['paired_gain_lcb']<.03 or d['task_wall_ratio']>1.02:
        return dict(verdict='NO_MEASURABLE_PRODUCT_GAIN',reasons=['paired performance or task wall gate'])
    return dict(verdict='CANDIDATE_PASS_NOT_RELEASED',reasons=['requires soak, recovery evidence and explicit production approval'])
