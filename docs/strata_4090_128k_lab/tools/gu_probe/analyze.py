"""Paired-round inference and phase-aligned frequency/memory for the one-format probe."""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
import statistics


def quantile(xs,q):
    xs=sorted(xs);i=(len(xs)-1)*q;lo=int(i);hi=min(lo+1,len(xs)-1)
    return xs[lo]+(i-lo)*(xs[hi]-xs[lo])


def paired_stats(ratios):
    if not 2<=len(ratios)<=6 or any(not math.isfinite(r) or r<=0 for r in ratios):raise ValueError('PAIRED_RATIOS')
    logs=[math.log(x) for x in ratios];n=len(logs);point=math.exp(statistics.mean(logs))
    # Enumerate all n^n paired-round bootstrap samples; do not resample rows/sweeps as independent trials.
    boot=[math.exp(sum(logs[i] for i in indices)/n) for indices in itertools.product(range(n),repeat=n)]
    lower,upper=quantile(boot,.025),quantile(boot,.975)
    return {'n_pairs':n,'time_ratio':point,'time_ratio_ci95':[lower,upper],
            'improvement_percent':100*(1-point),'improvement_ci95_percent':[100*(1-upper),100*(1-lower)],
            'expansion_gate':point<=.97 and upper<1.0,'bootstrap_samples':len(boot)}


def load(p):return json.loads(p.read_text())


def frequency(folder,result):
    root=load(folder/'root-perf-start.json');started=result.get('start_epoch_s');duration=result.get('seconds')
    events={};points={}
    for row in csv.reader((folder/'aperf-mperf.csv').read_text().splitlines()):
        if len(row)<6 or row[0].strip().startswith('#'):continue
        try:t=float(row[0]);value=float(row[1]);running=float(row[5])
        except ValueError:continue
        if running<99.0:raise ValueError('MSR_COUNTER_NOT_FULLY_SCHEDULED')
        if started is not None and not started+2<=root['epoch']+t<=started+duration-2:continue
        events[row[3]]=events.get(row[3],0)+value;points.setdefault(t,{})[row[3]]=value
    aperf,mperf=events.get('msr/aperf/',0),events.get('msr/mperf/',0)
    if not aperf or not mperf:raise ValueError('MSR_COUNTER_EVIDENCE_MISSING')
    owner={}
    for row in csv.reader((folder/'owner-perf.csv').read_text().splitlines()):
        if len(row)<3 or row[0].strip().startswith('#'):continue
        try:owner[row[2]]={'value':float(row[0]),'unit':row[1]}
        except ValueError:continue
    clk=owner['task-clock'];clock_ns=clk['value']*(1e6 if clk['unit']=='msec' else 1e9)
    return {'aperf':aperf,'mperf':mperf,'aperf_mperf_ratio':aperf/mperf,'intervals':len(points),
            'window':'measurement with first/last2s discarded; root-perf epoch anchor may differ by a small exec startup delay' if started else 'entire diagnostic arm, includes load/warmup',
            'owner_effective_ghz_whole_arm':owner['cycles']['value']/clock_ns,
            'owner_counters_whole_arm':owner}


def memory(folder,measurement):
    samples=[json.loads(s) for s in (folder/'memory.jsonl').read_text().splitlines()]
    process=[p for s in samples for p in s['processes'] if '(lab_gu_probe)' in p.get('stat','') and 'smaps_rollup' in p]
    if not process:raise ValueError('ACTUAL_BENCH_PROCESS_NOT_SAMPLED')
    result={'process_pids':sorted(set(p['pid'] for p in process)),'process_samples':len(process)}
    for key in ['VmHWM_kib','VmRSS_kib','VmSwap_kib','VmLck_kib','VmPin_kib']:
        result['max_'+key]=max(p['status'].get(key,0) for p in process)
    for key in ['Rss_kib','Pss_kib','Pss_Anon_kib','Pss_File_kib','Pss_Shmem_kib','Locked_kib']:
        result['max_'+key]=max(p['smaps_rollup'].get(key,0) for p in process)
    result['min_MemAvailable_kib']=min(s['system']['meminfo']['MemAvailable_kib'] for s in samples)
    first,last=samples[0]['system']['vmstat'],samples[-1]['system']['vmstat']
    result['system_vmstat_delta']={k:last[k]-first[k] for k in ['pswpin','pswpout','pgmajfault']}
    start=measurement['start_epoch_s']+2;end=measurement['start_epoch_s']+measurement['seconds']-2
    window=[s for s in samples if start<=s['ts']<=end]
    live=[p for s in window for p in s['processes'] if '(lab_gu_probe)' in p.get('stat','')]
    if len(live)<2 or len({p['pid'] for p in live})!=1:raise ValueError('MEASUREMENT_MEMORY_WINDOW')
    # /proc/PID/stat fields after comm: state is field 3; minflt/majflt are 10/12.
    before,after=[p['stat'].rsplit(')',1)[1].split() for p in (live[0],live[-1])]
    result['measurement_window']={'samples':len(live),'minor_fault_delta':int(after[7])-int(before[7]),
        'major_fault_delta':int(after[9])-int(before[9]),
        'VmRSS_kib_range':[min(p['status']['VmRSS_kib'] for p in live),max(p['status']['VmRSS_kib'] for p in live)]}
    return result


def analyze(task):
    task=Path(task);arms={}
    for r in range(6):
        for mode in ['off','on']:
            folder=task/'bench'/f'r{r}-{mode}';result=load(folder/'result.json')
            if result['mode']!=mode or result['workers']!=15 or result['seconds']<60 or result['sweeps']<=0:raise ValueError('ARM_IDENTITY_OR_COMPLETENESS')
            if (mode=='on') != (result['candidate_row_calls']>0):raise ValueError('CANDIDATE_HIT_EVIDENCE')
            arms[f'r{r}-{mode}']={'result':result,'frequency':frequency(folder,result),'memory':memory(folder,result)}
    hashes={v['result']['output_hash'] for v in arms.values()}
    if len(hashes)!=1:raise ValueError('PAIRED_OUTPUT_HASH_MISMATCH')
    metrics={}
    for metric in ['ns_per_sweep','gu_ns_per_sweep','quant_ns_per_sweep','down_ns_per_sweep','p95_sweep_ns']:
        ratios=[arms[f'r{r}-on']['result'][metric]/arms[f'r{r}-off']['result'][metric] for r in range(6)]
        metrics[metric]=dict(paired_stats(ratios),paired_ratios=ratios,
                             mean_off=statistics.mean(arms[f'r{r}-off']['result'][metric] for r in range(6)),
                             mean_on=statistics.mean(arms[f'r{r}-on']['result'][metric] for r in range(6)))
    micro=[]
    for r in range(3):
        off=load(task/'micro'/f'r{r}-off'/'result.json');on=load(task/'micro'/f'r{r}-on'/'result.json')
        if off['output_hash']!=on['output_hash']:raise ValueError('MICRO_OUTPUT_HASH')
        micro.append(on['ns_per_call']/off['ns_per_call'])
    gate=metrics['ns_per_sweep']['expansion_gate']
    report={'state':'COMPLETE','scope':'captured single-format complete ExpertPool replay, not request performance/task quality',
            'expansion_gate':'PASS' if gate else 'NOT_MET','whole_machine_allowed':gate,'metrics':metrics,
            'micro_diagnostic':paired_stats(micro),'arms':arms,'output_hash':next(iter(hashes))}
    (task/'ANALYSIS.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('task');a=p.parse_args();r=analyze(a.task)
    print(json.dumps({'state':r['state'],'expansion_gate':r['expansion_gate'],'complete_expert':r['metrics']['ns_per_sweep'],'micro':r['micro_diagnostic']},indent=2))
