#!/usr/bin/env python3
import csv,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]; RES=R/'results'
def loadj(name,default):
 p=RES/name
 try:return json.loads(p.read_text())
 except:return default
http=loadj('http_bench.json',[]); cache=loadj('cache_bench.json',[])
pi=[]
p=RES/'pi_cases.csv'
if p.exists():
 with p.open() as f: pi=list(csv.DictReader(f))
by={x.get('tag'):x for x in http}
deep=by.get('deep',{}); mid=by.get('mid',{})
cap=(deep.get('prompt_tokens') or 0)>=185000 and deep.get('ok') and deep.get('needle_ok')
speed=(deep.get('decode_tps') or 0)>=20 if deep else False
mid_speed=(mid.get('decode_tps') or 0)>=50 if mid else False
append=next((x for x in cache if x.get('tag')=='cache-append'),{})
cold=next((x for x in cache if x.get('tag')=='cache-cold'),{})
append_cache=False
if append:
 pt=append.get('prompt_tokens') or 0; c=append.get('cached_tokens') or 0
 if pt and c>=pt*0.5: append_cache=True
 if cold.get('ttft_s') and append.get('ttft_s') is not None and append['ttft_s'] <= cold['ttft_s']*0.5: append_cache=True
pi_pass=[]
for r in pi:
 ok=(r['pi_exit']=='0' and r['verify_exit']=='0' and r['protected_ok']=='true' and r['source_changed']=='true')
 pi_pass.append(ok)
java_ok=(len(pi_pass)>=3 and all(pi_pass))
mandatory=[cap,speed,append_cache,java_ok]
if all(mandatory): decision='GO'
elif cap and speed and sum(pi_pass)>=2: decision='GO_WITH_CAVEATS'
else: decision='NO_GO'
summary={'decision':decision,'capacity_gate':cap,'deep_speed_gate':speed,'mid_speed_gate':mid_speed,'append_cache_gate':append_cache,'java_gate':java_ok,'java_pass_count':sum(pi_pass),'java_case_count':len(pi_pass)}
(RES/'summary.json').write_text(json.dumps(summary,indent=2))
lines=['# Final Qualification Report','',f'**Decision: {decision}**','', '## Gates','', '| Gate | Result |','|---|---|',
 f"| >=185K actual occupied prompt | {'PASS' if cap else 'FAIL'} |",
 f"| >=20 tok/s at deep context | {'PASS' if speed else 'FAIL'} |",
 f"| >=50 tok/s at ~64K | {'PASS' if mid_speed else 'WARN/FAIL'} |",
 f"| Growing Agent prefix-cache reuse | {'PASS' if append_cache else 'FAIL'} |",
 f"| Pi Java cases | {sum(pi_pass)}/{len(pi_pass)} |",'', '## HTTP measurements','',
 '| tag | prompt tokens | completion | TTFT s | decode tok/s | needle |','|---|---:|---:|---:|---:|---|']
for x in http:
 lines.append(f"| {x.get('tag')} | {x.get('prompt_tokens')} | {x.get('completion_tokens')} | {x.get('ttft_s')} | {round(x.get('decode_tps') or 0,2)} | {x.get('needle_ok')} |")
lines += ['', '## Cache measurements','', '| tag | prompt | cached | TTFT s | wall s |','|---|---:|---:|---:|---:|']
for x in cache: lines.append(f"| {x.get('tag')} | {x.get('prompt_tokens')} | {x.get('cached_tokens')} | {x.get('ttft_s')} | {x.get('wall_s')} |")
lines += ['', '## Pi Java cases','', '| case | pass | elapsed s | tool calls |','|---|---|---:|---:|']
for r,ok in zip(pi,pi_pass): lines.append(f"| {r['case']} | {'PASS' if ok else 'FAIL'} | {r['elapsed_s']} | {r['tool_calls']} |")
lines += ['', '## Interpretation','',
 'Promote this profile only if the mandatory gates reflect the workload you actually care about. Raw short-context tok/s is not sufficient to replace the existing llama.cpp WORK profile. Keep raw JSON/JSONL logs for A/B comparison.']
(RES/'FINAL_REPORT.md').write_text('\n'.join(lines))
print(json.dumps(summary,indent=2)); print(f"Report: {RES/'FINAL_REPORT.md'}")
