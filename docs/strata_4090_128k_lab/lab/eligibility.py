from __future__ import annotations
import json
from pathlib import Path
from .core import flag_value,available_mib,dump
from .workspace import experiment,state_dir


def qualify(c,pr):
    e=experiment(pr);cfg=json.loads(Path(c['deployed_config']).read_text(encoding='utf-8-sig'))
    a=cfg.get('args',[]);u=cfg.get('user_args',[]);env=cfg.get('env',{})
    def value(f):return flag_value(u,f) if flag_value(u,f) is not None else flag_value(a,f)
    blocks=[];probes=[]
    if pr in (2253,3584,3711,2822) and c['conversation_cache_mib']<=0:
        blocks.append('Selected experiment needs actual conversation parking; lab cache budget is explicitly 0. Do not enable a large cache automatically.')
    if pr in (3307,3281) and cfg.get('mtp') is False:blocks.append('MTP is explicitly disabled')
    if pr==2964:
        if value('--pcie-frac') in ('0','0.0','0.00'):blocks.append('PCIe share is zero: no admissible fetches')
        if value('--resident-budget-gib') not in (None,'0','0.0'):blocks.append('Original PR rejects resident-RAM mode')
        if value('--adapt-async') not in (None,'0'):blocks.append('Original PR rejects async adaptation')
        if env.get('STRATA_ADAPT_OVERLAP')=='1':blocks.append('Original PR rejects adaptive overlap')
        probes.append('Measure actual PCIe-routed misses/admissions; historical share 0.022 is weak evidence of benefit')
    if pr==3453:probes+=['Read the P0-T6 CFG-IL0 (STRATA_MMVQ_IL=0, issue #1842) result first; it sets the target','Profile dense projections and run mmvq_il_parity --bench --emit-table on this 4090']
    if pr==1536:probes+=['Measure generated-reply token divergence and re-read count; high prefix-hit rate alone is not enough']
    if pr==3517:probes+=['Capture actual system+tools root length and confirm it exceeds the first periodic checkpoint']
    if pr in (3307,3281):probes+=['Show prefill ring/chunk is VRAM-limited; count NEW unread tokens, not whole context']
    if pr==2253:probes+=['Reproduce a RAM-gate refusal after evictions (or with an empty cache) on A0; raise --conversation-cache-min-free-mib instead of lowering min_available_mib','Sample [heap] Rss from /proc/PID/smaps and MemAvailable per request; also run CFG-MMAP (MALLOC_MMAP_THRESHOLD_=8388608) as a config control']
    if pr==3711:probes+=['Show superseded snapshot captures or slot shuttle events; a solo cache-off service is not a target']
    if pr==2822:probes+=['Two clients must really overlap while native parallel stays 1; prove paused-state memory fits']
    if pr==3322:probes+=['Audit existing main CLI implementation versus PR; service support is not assumed','Explicitly pin draft weights; do not auto-download or replace target quantization']
    if pr in (2253,3584,3711,2822):probes+=['Measure loaded baseline MemAvailable and reserve at least 4096 MiB; start with 512 MiB cache at most']
    out={'pr':pr,'status':'NOT_APPLICABLE_UNDER_CURRENT_PROFILE' if blocks else 'NEEDS_MECHANISM_PROBE',
         'blocks':blocks,'required_probes':probes,'environment_is_historical_until_inventory':True,
         'max_context':131072,'note':'This is a screening rule, not permission to mutate production or a guarantee of speed.'}
    dump(state_dir(c,pr)/'eligibility.json',out);return out
