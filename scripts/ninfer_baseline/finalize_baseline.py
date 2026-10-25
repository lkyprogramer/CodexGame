#!/usr/bin/env python3
"""Finish evidence delivery after the existing runner completes. No model calls."""
import csv
import datetime as dt
import fcntl
import hashlib
import gzip
import json
from pathlib import Path
import shutil

import backup_baseline as backup

REPO = Path('/Users/luo/Documents/github/CodexGame')
EVIDENCE = backup.EVIDENCE
OUT = REPO/'output/ninfer-baseline-29-20261020'
REMOTE_PREFIX = '/home/hhtele/ninfer-baseline-20261020/'
MANIFEST_SHA = '2a1679ad2f21d20a4348d1747f4b450687b0db7b6fdac3c4d841d003a136f76e'


def metric_row(observation):
    r = observation['record']
    result = {k:r.get(k) for k in ['id','group','cache','http_status','prompt_tokens',
        'completion_tokens','requested_output_tokens','effective_output_cap_by_source_contract',
        'elapsed_s','decode_tokens_per_s','first_payload_s','first_content_s','first_reasoning_s',
        'first_tool_s','finish_reason','content_chars','reasoning_chars','sse_done','request_sha256','raw_sha256']}
    result.update(logical_id=observation['logical_id'], source_mode=observation['evidence']['mode'],
                  source_root=observation['evidence']['source_root'], failures=json.dumps(r['failures']))
    for prefix, values in [('timing',r.get('timings_seconds')),('speculative',r.get('speculative')),
                            ('cache',r.get('continuation_cache')),('result',r.get('result')),
                            ('prepare',r.get('prepare_detail')),('extra',r.get('extra')),
                            ('behavior',r.get('behavior_outcomes'))]:
        for k,v in (values or {}).items():
            result[prefix+'_'+k] = json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v
    return result


def verify_observation(snapshot, observation):
    ref = observation['evidence']
    source = ref['source_root']
    if not source.startswith(REMOTE_PREFIX):
        raise RuntimeError('unexpected evidence source root')
    root = snapshot/'remote'/source[len(REMOTE_PREFIX):]
    record = json.loads((root/'requests'/ref['source_id']/'record.json').read_text())
    canonical = lambda value: json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
    if record != observation['record'] or hashlib.sha256(canonical(record)).hexdigest()!=ref['record_sha256']:
        raise RuntimeError('logical record identity mismatch: '+observation['logical_id'])
    directory = root/'requests'/ref['source_id']
    if backup.digest(directory/'raw.json.gz')!=ref['raw_sha256']:
        raise RuntimeError('logical raw hash mismatch')
    body = json.loads((directory/'request.json').read_text())
    if hashlib.sha256(canonical(body)).hexdigest()!=ref['request_sha256']:
        raise RuntimeError('logical request hash mismatch')


def coding_metrics(snapshot, audit):
    root = snapshot/'remote/slim-v1/closed-loop-collector'
    records_bytes = (root/'records.jsonl').read_bytes()
    if hashlib.sha256(records_bytes).hexdigest()!=audit['records_sha256']:
        raise RuntimeError('coding records differ from frozen recovery audit')
    records = [json.loads(line) for line in records_bytes.splitlines()]
    if len({r['id'] for r in records})!=len(records):
        raise RuntimeError('duplicate coding request IDs')
    grouped = {}
    for row in records:
        ref = {'source_root':REMOTE_PREFIX+'slim-v1/closed-loop-collector', 'source_id':row['id'],
               'record_sha256':hashlib.sha256(json.dumps(row,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
               'request_sha256':row['request_sha256'],'raw_sha256':row['raw_sha256']}
        verify_observation(snapshot, {'logical_id':row['id'],'record':row,'evidence':ref})
        header = row['extra']['local_case_header']
        with gzip.open(root/'requests'/row['id']/'raw.json.gz','rb') as stream:
            raw = json.load(stream)
        grouped.setdefault(header,[]).append((row,raw))
    audit_groups = {g['header']:g for g in audit.get('groups',[])}
    if set(grouped)!=set(audit_groups):
        raise RuntimeError('coding wire groups differ from recovery audit')
    if any(len(entries)!=audit_groups[header]['requests'] for header,entries in grouped.items()):
        raise RuntimeError('coding request counts differ from recovery audit')
    results = []
    for header, entries in grouped.items():
        rows = [r for r,_ in entries]
        total = lambda key: sum(r[key] for r in rows) if all(type(r.get(key)) is int for r in rows) else None
        p,o = total('prompt_tokens'),total('completion_tokens')
        cache = [r.get('result',{}).get('prefix_cache_hit_tokens') for r in rows]
        tools = [raw.get('parsed',{}).get('tool_count') for _,raw in entries]
        results.append({'header':header,'case_id':header.split('/')[0],
                        'model_http_rounds':len(rows),'proposed_tool_calls':sum(tools) if all(type(x) is int for x in tools) else None,
                        'prompt_tokens_sum':p,'completion_tokens_sum':o,
                        'total_tokens_sum':p+o if p is not None and o is not None else None,
                        'prefix_cache_hit_tokens_sum':sum(cache) if all(type(x) is int for x in cache) else None,
                        'request_wall_s_sum':sum(r['elapsed_s'] for r in rows),
                        'unapplied_or_failed_tools':audit_groups[header].get('unapplied_or_failed_tools',[]),
                        'request_ids':[r['id'] for r in rows], 'raw_request_integrity':'PASS',
                        'turn_definition':'HTTP model response count; original Pi CLI turns unavailable',
                        'token_definition':'Actual server P/O summed across all requests, including repeated cached prompt tokens; no reasoning split'})
    return results


def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True,mode=0o700)
    status_path = EVIDENCE/'finalization-status.json'
    report_path = OUT/'FINAL-REPORT.md'
    with (EVIDENCE/'finalization.lock').open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
        def state(value, **fields):
            status_path.write_text(json.dumps({'state':value,'utc':dt.datetime.now(dt.timezone.utc).isoformat(),**fields},indent=2)+'\n')
        if status_path.exists():
            prior = json.loads(status_path.read_text())
            if prior.get('state')=='REPORT_READY_WITH_DISCLOSED_LIMITATIONS':
                artifacts=prior.get('artifact_hashes',{})
                if not artifacts or any(not Path(p).is_file() or backup.digest(p)!=h for p,h in artifacts.items()):
                    state('FINALIZATION_NEEDS_ATTENTION',error='previous delivery artifact missing or changed')
                    raise RuntimeError('previous delivery integrity check failed')
                print(json.dumps(prior));return prior
        state('FINAL_BACKUP_RUNNING')
        try:
            backup.REPO = REPO
            receipt = backup.main(final=True)
            snapshot = Path(receipt['root'])
            report = json.loads((snapshot/'remote/slim-v1/reference-report.json').read_text())
            manifest = json.loads((snapshot/'remote/slim-v1/manifest.json').read_text())
            expected_ids = {p['id']+'-'+cache for p in manifest['pairs'] for cache in ['cold','warm']}
            expected_ids |= {'pi-'+p['id'] for p in manifest['pi_cases']} | set(manifest['state_case_ids'])
            if (report['planned']!=278 or report['resolved']!=278 or report['pending']
                    or len(report['observations'])!=278
                    or len(expected_ids)!=278
                    or {o['logical_id'] for o in report['observations']}!=expected_ids
                    or backup.digest(snapshot/'remote/slim-v1/manifest.json')!=MANIFEST_SHA
                    or report['manifest_sha256']!=MANIFEST_SHA):
                raise RuntimeError('incomplete or changed logical reference coverage')
            for name, expected_hash in manifest['scripts_sha256'].items():
                if backup.digest(snapshot/'remote/slim-bin-v1'/name)!=expected_hash:
                    raise RuntimeError('frozen collector source hash mismatch: '+name)
            for observation in report['observations']:
                verify_observation(snapshot,observation)
            transition = OUT/'slim-transition-20261021'
            old8 = json.loads((transition/'heartbeat-20261021T0246.json').read_text())['coding_results']
            external = json.loads((transition/'r3-execution-verified.json').read_text())['external_scores']
            if len(old8)!=8 or len(external)!=2:
                raise RuntimeError('coding score evidence incomplete')
            audit_path = EVIDENCE/'recovered-derived-20261021/recovery-audit.json'
            audit = json.loads(audit_path.read_text()) if audit_path.exists() else {
                'status':'MISSING_LOCAL_ARTIFACT','reason':'Recovery audit is not yet available; original local CLI/patch/grader files absent.'}
            coding_attempts = coding_metrics(snapshot,audit)
            priority_pi = [o for o in report['observations'] if o['logical_id'] in manifest['priority_ids']]
            outcomes = {}
            for overlay in ['capacity_outcomes','fixture_rejections']:
                for logical_id, value in report.get(overlay,{}).get('outcomes',{}).items():
                    if logical_id in outcomes and outcomes[logical_id]!=value:
                        raise RuntimeError('conflicting rejection outcome: '+logical_id)
                    outcomes[logical_id] = value
            capacity = {k:v for k,v in outcomes.items() if v['outcome']=='EXPECTED_PRE_ADMISSION_CONTEXT_CAPACITY_REJECTION'}
            invalid = {k:v for k,v in outcomes.items() if v['outcome']=='INVALID_FROZEN_TOOL_ARGUMENTS'}
            if len(capacity)+len(invalid)!=len(outcomes):
                raise RuntimeError('unknown rejection outcome classification')
            protocol = report.get('protocol_reconciliation', {})
            protocol_options = report.get('protocol_option_rejections', {})
            for overlay,filename in [(protocol,'protocol-reconciliation-v4.json'),
                                     (protocol_options,'protocol-option-rejections-v5.json')]:
                if not overlay:
                    continue
                if overlay != json.loads((snapshot/'remote/slim-v1'/filename).read_text()):
                    raise RuntimeError('protocol outcome report mismatch')
                by_id = {o['logical_id']:o for o in report['observations']}
                for ident, proof in overlay['outcomes'].items():
                    ref = by_id[ident]['evidence']
                    if (proof.get('request_resent') is not False or proof.get('performance_sample_eligible') is not False
                            or any(proof[k]!=ref[k] for k in ['record_sha256','request_sha256','raw_sha256'])):
                        raise RuntimeError('protocol reconciliation changed original evidence')
            pi_accepted = sum(o['record']['group']=='pi_teacher_forced' and o['record']['http_status']==200
                              for o in report['observations'])
            rows = [metric_row(o) for o in report['observations']]
            columns = sorted(set().union(*(row.keys() for row in rows)))
            with (OUT/'reference-metrics.csv').open('w',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
            groups={}
            for observation in report['observations']:
                row=observation['record'];g=groups.setdefault(row['group'],{'observations':0,'request_wall_s':0,'http_200':0,'http_400':0})
                g['observations']+=1;g['request_wall_s']+=row['elapsed_s'];g['http_200']+=row['http_status']==200;g['http_400']+=row['http_status']==400
            summary={'schema_version':1,'status':'REFERENCE_COVERAGE_COMPLETE_WITH_DISCLOSED_LIMITATIONS',
                     'optimization_qualification':False,'p95':None,'manifest_sha256':report['manifest_sha256'],
                     'planned':278,'resolved':278,'reused':report['reused'],'collected':report['collected'],
                     'original_observations_with_gaps':report['observations_with_gaps'],
                     'capacity_rejections':capacity,'invalid_frozen_fixtures':invalid,
                     'protocol_reconciliation':protocol,
                     'protocol_option_rejections':protocol_options,
                     'groups':groups,'coding_results':old8,'external_scores':external,
                     'coding_attempt_metrics':coding_attempts,'priority_pi':priority_pi,
                     'local_artifact_recovery_audit':audit,'backup_receipt':receipt,
                     'unavailable_metrics':report['unavailable_metrics'],
                     'resource_and_raw_metrics':'Private final snapshot contains original request/raw SSE/schema20 metrics, GPU/host sampling and deployment fingerprints.',
                     'new_model_or_grader_runs':False}
            (OUT/'final-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
            gap_ids=report['observations_with_gaps']
            lines=['# 29 / Qwen3.8-27B 精简 Baseline 结果','',
                '278 项参考覆盖和 8+2 个编程任务已完成记账。本次仅测量现有部署，未实施引擎优化；不代表优化或未来 sampling 资格通过。','',
                f"参考单元：278/278；复用 {report['reused']}，新采集 {report['collected']}；保留原始 gap {len(gap_ids)} 个。",
                f"Pi 输入拒绝：容量 {len(capacity)} 条，非法冻结工具参数 {len(invalid)} 条；均不属于有效性能样本。{pi_accepted} 条 HTTP200 回放也不等于任务质量通过。",'',
                '| 编程任务 | 结果 |','|---|---|']
            lines += [f"| {r['id']} | {r['status']} |" for r in old8]
            lines += [f"| {r['id']} | {r['status']}，{r['tests_passed']}/{r['tests_total']} |" for r in external]
            lines += ['', '| 编程 attempt（原请求组） | 模型请求轮数 | 提议工具调用 | 实际 P / O / cache hit | 总 token |',
                      '|---|---:|---:|---:|---:|']
            lines += [f"| {r['header']} | {r['model_http_rounds']} | {r['proposed_tool_calls']} | {r['prompt_tokens_sum']} / {r['completion_tokens_sum']} / {r['prefix_cache_hit_tokens_sum']} | {r['total_tokens_sum']} |" for r in coding_attempts]
            lines += ['', '轮数是实际 HTTP 模型请求数，工具数是响应中提议的调用数；原 CLI turn 及执行器原生统计无法等价恢复。P 包含重复及缓存输入，不等于独立输入或计费金额。Gson r2 ordinal-9 中止与 r3 attempt-2 单独列项，成本未删除。','', '两条历史 Pi 异常：','']
            lines += [f"- {o['logical_id']}：P={o['record']['prompt_tokens']}，O={o['record']['completion_tokens']}，请求上限={o['record']['requested_output_tokens']}，finish={o['record']['finish_reason']}，reasoning_only={o['record']['behavior_outcomes']['reasoning_only']}，output_budget_exhausted={o['record']['behavior_outcomes']['output_budget_exhausted']}。" for o in priority_pi]
            lines += ['', 'Gson r2 的工具策略中止及 8/10 部分评分另行保留，未被 r3 完整评分覆盖。完成失败仍计入结果和成本；未为提高成绩重跑任务。','',
                      '| 测量组 | 记录数 | 请求耗时合计（秒） | HTTP200 / HTTP400 |', '|---|---:|---:|---:|']
            lines += [f"| {k} | {v['observations']} | {v['request_wall_s']:.2f} | {v['http_200']} / {v['http_400']} |" for k,v in groups.items()]
            lines += ['', '上述耗时是请求耗时合计，包含复用结果；不能当作本次运行的总墙钟时间或候选性能收益。分组聚合也不构成 p95 或 A/B 置信区间。','',
                '原始指标与完整性：','',f"- [最终备份回执]({snapshot}/BACKUP-RECEIPT.json)",
                '- [完整汇总及证据缺口](final-summary.json)','- [278 项逐记录指标](reference-metrics.csv)',
                '- 逐项 record/request/raw 哈希和原 manifest 已核验。旧矩阵 513 条记录保留，原 3 个损坏 raw 不计入有效统计；历史游标副本不是独立样本。',
                '- 本机原始 CLI、部分补丁和 grader 附件目录已缺失。恢复审计区分历史 SHA 相同字节、仅派生内容和无法恢复附件；未补造原始日志。',
                f'- 恢复审计：{audit_path}。',
                '- token IDs、真实逐 token ITL、可靠 reasoning token 拆分、round wall、allocator 高水位不可观测，保持 null 和原因。p95=null。',
                '- 生产采样参数及 Pi medium/32768 预算保持原值；greedy 参考仅为原计划中的独立诊断样本。',
                '- 运行期间发生过采集/接续修复和证据备份，时间与副作用由各回执记录；不从本次单参考推导优化收益。','']
            if protocol:
                lines += ['协议证据补充：18343 非流式代理丢弃响应请求 ID，原采集器记下两项关联失败并停测。完整 HTTP200 JSON 与冻结服务日志中唯一时间窗的 start/done、usage 和 timing 相符，已后验核对完成；原 row/raw、失败和 null 指标均保留，未重发，该条不计入有效性能样本。详见 final-summary.json 的 protocol_reconciliation。','']
            if protocol_options:
                lines += [f"Responses 接口覆盖缺口：{len(protocol_options['outcomes'])} 条原样请求被完整 HTTP400 拒绝，服务不支持 chat_template_kwargs.enable_thinking。未删除该参数、未重发已完成请求；原失败/null 指标保留，不计有效性能样本或模型质量失败，也不宣称 Responses 成功覆盖。详见 protocol_option_rejections。",'']
            report_path.write_text('\n'.join(lines))
            delivery=snapshot/'final-delivery';delivery.mkdir()
            for name in ['FINAL-REPORT.md','final-summary.json','reference-metrics.csv']:
                shutil.copy2(OUT/name,delivery/name)
            if audit_path.exists():shutil.copytree(audit_path.parent,snapshot/'recovered-derived')
            hashes={str(f.relative_to(snapshot)):backup.digest(f) for folder in [delivery,snapshot/'recovered-derived']
                    if folder.exists() for f in folder.rglob('*') if f.is_file()}
            (snapshot/'DELIVERY-MANIFEST.json').write_text(json.dumps(hashes,indent=2)+'\n')
            artifacts={str(OUT/name):backup.digest(OUT/name) for name in ['FINAL-REPORT.md','final-summary.json','reference-metrics.csv']}
            artifacts.update({str(snapshot/path):digest for path,digest in hashes.items()})
            for name in ['DELIVERY-MANIFEST.json','BACKUP-RECEIPT.json','remote-evidence.tar.gz']:
                artifacts[str(snapshot/name)]=backup.digest(snapshot/name)
            state('REPORT_READY_WITH_DISCLOSED_LIMITATIONS',report=str(report_path),report_sha256=backup.digest(report_path),
                  final_backup=str(snapshot),resolved=278,model_requests_allowed=False,artifact_hashes=artifacts)
            print(status_path.read_text());return json.loads(status_path.read_text())
        except BaseException as error:
            state('FINALIZATION_NEEDS_ATTENTION',error=type(error).__name__+': '+str(error))
            raise


if __name__=='__main__':
    main()
