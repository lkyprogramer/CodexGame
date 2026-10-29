"""Read-only P11 decode accounting. Conditional deletion model, not critical-path proof."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sqlite3
import analyze_dequant as base

TYPES = {'IQ4XSTraits':23, 'Q3KTraits':11, 'Q4KTraits':12, 'Q5KTraits':13, 'Q6KTraits':14,
         'IlIQ4XS':23, 'IlQ3K':11, 'IlQ4K':12, 'IlQ5K':13, 'IlQ6K':14}


def decode_shape(name, grid_x):
    """Recover output rows from pinned launch formula; input width remains unknown."""
    dtype = next((v for k,v in TYPES.items() if k in name), None)
    if dtype is None:
        return None
    if 'native_mmvq_il_kernel<' in name or 'native_mmvq_il_pf_kernel<' in name:
        ints = [int(x) for x in re.findall(r'\(int\)(\d+)', name)]
        if len(ints) < 2:
            return None
        cols, rows = ints[:2]
        return {'type_id':dtype, 'ncols':cols, 'n_out_nominal':grid_x*rows*4,
                'rows':rows, 'kind':'IL', 'n_out_uncertainty':rows*4-1}
    if 'native_mmvq_multi_kernel<' in name:
        ints = [int(x) for x in re.findall(r'\(int\)(\d+)', name)]
        if len(ints) < 3 or '(bool)1>' in name.split('>(')[0]:
            return None
        cols, _, rows = ints[:3]
        return {'type_id':dtype,'ncols':cols,'n_out_nominal':grid_x*rows,
                'rows':0,'kind':'MULTI','n_out_uncertainty':rows-1}
    if 'b6_mmvq_rows_kernel<' in name:
        ints = [int(x) for x in re.findall(r'\(int\)(\d+)',name)]
        if len(ints)!=2:return None
        return {'type_id':dtype,'ncols':ints[0],'n_out_nominal':grid_x*ints[1],
                'rows':0,'kind':'B6','n_out_uncertainty':ints[1]-1}
    return None


def match_cells(shape, cells):
    if shape is None:return []
    return [c for c in cells if c['type_id']==shape['type_id'] and c['ncols']==shape['ncols']
            and 0 <= shape['n_out_nominal']-c['n_out'] <= shape['n_out_uncertainty']]


def mmvq_exclusion(name, shape):
    """Pinned Ada dispatch accepts only types 11/12/13/14/23 (native_mmvq_il switch)."""
    if shape is not None and shape['ncols'] not in (2,3,4):
        return 'PARSED_T_OUTSIDE_CHANGED_ADA_2_4'
    if re.search(r'native_(?:iq4_xs|q[3456]_k)_mmvq_kernel<',name):
        return 'PLAIN_SINGLE_COLUMN_T1'
    if 'Q20Traits' in name or 'Q20Block' in name:
        return 'Q2_0_TYPE42_NOT_SUPPORTED_BY_ADA_IL'
    if 'IQ4NLBlock' in name:
        return 'IQ4_NL_TYPE20_NOT_SUPPORTED_BY_ADA_IL'
    if 'Q80Block' in name:
        return 'Q8_0_TYPE8_NOT_SUPPORTED_BY_ADA_IL'
    m=re.search(r'(?<!native_)mmvq_multi_kernel<\(int\)(\d+),',name)
    if m and int(m.group(1)) not in (11,12,13,14,23):
        return 'EXPLICIT_IQ_TYPE_'+m.group(1)+'_NOT_SUPPORTED_BY_ADA_IL'
    return None


def qsa_family(name):
    if re.search(r'block_scores_(?:multi|rows|tc|tail)_kernel',name):return 'QSA_BLOCK_SCORING'
    if re.search(r'block_topk_(?:reg|multi|long|kernel)',name):return 'QSA_BLOCK_SELECTION'
    if 'QsaAttnPools' in name or 'attn_merge_v2_kernel' in name:return 'QSA_ATTENTION_SUPERSET'
    if 'QsaIndexerLayers' in name:return 'QSA_INDEXER_SUPERSET'
    if 'qsa_' in name:return 'QSA_NAMED_SUPERSET'
    return None


def accounting(kernels, start, end, cells, runtime):
    groups={};selected=[];changed=[];novel=[];support=[];qsa=[];wait=[];unknown=[];mismatch=[];correlations=Counter()
    for k in kernels:
        interval=base._clip(k,start,end)
        if not interval:continue
        selected.append(interval);name=k['name']
        key=(name,k['gridX'],k['gridY'],k['gridZ'])
        g=groups.get(key)
        if g is None:
            shape=decode_shape(name,k['gridX'])
            matched=match_cells(shape,cells)
            g={'name':name,'grid':[k['gridX'],k['gridY'],k['gridZ']], 'count':0,'cumulative_ns':0,
               'shape':shape,'matched_inventory_cells':matched,
               'actual_rows_match_all_base_cells':None if not matched else all(shape['rows']==c['base_rows'] for c in matched),
               'mmvq_exclusion_reason':mmvq_exclusion(name,shape) if 'mmvq' in name.lower() else None,
               'qsa_family':qsa_family(name)}
            groups[key]=g
        else:
            shape=g['shape'];matched=g['matched_inventory_cells']
        g['count']+=1;g['cumulative_ns']+=interval[1]-interval[0]
        any_changed=any(c['base_rows']!=c['new_rows'] for c in matched)
        any_novel=any(c['classification']=='changed_not_covered_by_old_override' for c in matched)
        if any_changed:changed.append(interval)
        if any_novel:novel.append(interval)
        if 'quantize' in name or 'interleave' in name:support.append(interval)
        if g['qsa_family']:qsa.append(interval)
        if 'wait_flag' in name:wait.append(interval)
        rows_mismatch=bool(matched) and any(shape['rows']!=c['base_rows'] for c in matched)
        if rows_mismatch:mismatch.append(interval)
        unresolved='mmvq' in name.lower() and (not shape or not matched or rows_mismatch)
        if unresolved and g['mmvq_exclusion_reason'] is None:unknown.append(interval)
        if any_changed:
            matches=runtime.get(k['correlationId'],[])
            if len(matches)!=1:correlations['missing_or_ambiguous']+=1
            elif matches[0]['returnValue']!=0:correlations['failed_api']+=1
            elif 'GraphLaunch' in matches[0]['name']:correlations['graph_launch_same_correlation_not_per_node_dependency']+=1
            elif 'Launch' in matches[0]['name']:correlations['launch_api']+=1
            else:correlations['nonlaunch_api']+=1
    union=lambda rows:base.interval_length(rows)
    whole=end-start
    return {'start_ns':start,'end_ns':end,'wall_ns':whole,'kernel_union_ns':union(selected),
            'changed_candidate_union_ns':union(changed),'novel_candidate_union_ns':union(novel),
            'all_quant_interleave_superset_union_ns':union(support),
            'novel_plus_all_support_union_ns':union(novel+support),
            'novel_plus_all_support_fraction':union(novel+support)/whole,
            'changed_plus_all_support_union_ns':union(changed+support),
            'novel_plus_support_plus_unknown_union_ns':union(novel+support+unknown),
            'novel_plus_support_plus_unknown_fraction':union(novel+support+unknown)/whole,
            'actual_rows_base_mismatch_union_ns':union(mismatch),
            'qsa_union_ns':union(qsa),'gpu_wait_union_ns':union(wait),'unparsed_mmvq_union_ns':union(unknown),
            'candidate_runtime_attribution':dict(correlations),'kernel_groups':list(groups.values()),
            'mmvq_excluded_groups':[g for g in groups.values() if g['mmvq_exclusion_reason']],
            'unknown_mmvq_groups':[g for g in groups.values() if 'mmvq' in g['name'].lower() and not g['mmvq_exclusion_reason'] and (not g['shape'] or not g['matched_inventory_cells'] or g['actual_rows_match_all_base_cells'] is False)],
            'state':('BASE_ROWS_MISMATCH' if mismatch else 'OBSERVED_CANDIDATE_SUPERSET') if selected else 'NO_KERNEL_TRACE',
            'limits':['n_in not inferred; all matching weight shapes retained as candidate superset',
                      'unknown MMVQ included unless exact kernel type or T proves outside changed Ada dispatch; exclusion reasons retained',
                      'all quant/interleave is deliberately overinclusive, not attributed per projection',
                      'client first-to-last output is an observation window, not complete verify windows',
                      'graph launch correlation does not reconstruct per-node dependencies',
                      'deletion model assumes other work durations fixed; not strict unprofiled upper bound']}


def analyze_trace(path, inventory, run_folder=None, expected_pid=None):
    path=Path(path).resolve();out={'trace':str(path),'state':'NO_TRACE','requests':[],
        'exact_critical_path_reconstructed':False,'drop_free_trace_established':False,
        'original_six_status':'FAIL_UNCHANGED','scoring_changed':False}
    if not path.is_file():return out
    c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        schema=base._schema(c);out['actual_schema']=schema
        required={'StringIds':['id','value'],'PROCESSES':['globalPid','pid','name'],
          'CUPTI_ACTIVITY_KIND_KERNEL':['start','end','deviceId','contextId','streamId','correlationId','globalPid','demangledName','gridX','gridY','gridZ'],
          'NVTX_EVENTS':['start','end','text','textId']}
        missing={t:base._require(schema,t,f) for t,f in required.items() if base._require(schema,t,f)}
        if missing:out['missing_schema']=missing;return out
        strings=dict(c.execute('select id,value from StringIds'))
        pid=expected_pid if expected_pid is not None else base.expected_pid_from_folder(run_folder)
        if pid is None:out.update(state='UNATTRIBUTED',error='EXPECTED_PID_REQUIRED');return out
        owners=[p for p in base._read(c,'PROCESSES',required['PROCESSES']) if p['pid']==pid]
        if len(owners)!=1 or owners[0]['globalPid'] is None or owners[0]['globalPid']%(1<<24):
            out.update(state='UNATTRIBUTED',error='OWNER_NOT_UNIQUE_OR_ALIGNED');return out
        owner=owners[0];gpid=owner['globalPid'];out['engine_process']=owner
        kernels=[k for k in base._read(c,'CUPTI_ACTIVITY_KIND_KERNEL',required['CUPTI_ACTIVITY_KIND_KERNEL']) if k['globalPid']==gpid]
        for k in kernels:
            k['name']=strings.get(k['demangledName'],'<UNKNOWN>')
            if k['end']<k['start']:raise ValueError('NEGATIVE_KERNEL_INTERVAL')
        runtime=defaultdict(list);fields=['start','end','globalTid','correlationId','nameId','returnValue']
        if not base._require(schema,'CUPTI_ACTIVITY_KIND_RUNTIME',fields):
            for values in c.execute('SELECT '+','.join(fields)+' FROM CUPTI_ACTIVITY_KIND_RUNTIME WHERE globalTid >= ? AND globalTid < ?', (gpid,gpid+(1<<24))):
                r=dict(zip(fields,values))
                if r['globalTid'] is not None and gpid<=r['globalTid']<gpid+(1<<24):
                    r['name']=strings.get(r['nameId'],'<UNKNOWN>');runtime[r['correlationId']].append(r)
        markers=base._read(c,'NVTX_EVENTS',required['NVTX_EVENTS'])
        for r in markers:r['label']=r['text'] or strings.get(r['textId'],'')
        cells=inventory['all_cells']
        for req in sorted((r for r in markers if r['label'].startswith('P11_REQUEST/')),key=lambda r:r['start']):
            name=req['label'].split('/',1)[1];a,b=req['start'],req['end']
            if b is None:out['requests'].append({'name':name,'state':'INVALID_MARKERS'});continue
            outputs=[r['start'] for r in markers if r['label']=='P11_OUTPUT/'+name and r['end'] is None and a<=r['start']<=b]
            first=[r['start'] for r in markers if r['label']=='P11_FIRST/'+name and r['end'] is None and a<=r['start']<=b]
            if len(first)!=1 or len(outputs)<2 or max(outputs)<=first[0]:
                out['requests'].append({'name':name,'state':'INVALID_MARKERS','outputs':len(outputs)});continue
            row={'name':name,'output_event_marks':len(outputs),'first_marker_ns':first[0],
                 'last_output_ns':max(outputs),'state':'OBSERVED',
                 'request':accounting(kernels,a,b,cells,runtime),
                 'decode_observed':accounting(kernels,first[0],max(outputs),cells,runtime),
                 'tail_after_last_output':accounting(kernels,max(outputs),b,cells,runtime)}
            if any(row[w]['state']=='BASE_ROWS_MISMATCH' for w in ['request','decode_observed','tail_after_last_output']):
                row['state']='BASE_ROWS_MISMATCH'
            out['requests'].append(row)
        out['state']='OBSERVED' if out['requests'] and all(r['state']=='OBSERVED' and r['request']['state']!='NO_KERNEL_TRACE' and r['decode_observed']['state']!='NO_KERNEL_TRACE' for r in out['requests']) else ('BASE_ROWS_MISMATCH' if any(r['state']=='BASE_ROWS_MISMATCH' for r in out['requests']) else 'UNATTRIBUTED')
        return out
    except (ValueError,sqlite3.Error) as e:out.update(state='INVALID_TRACE',error=str(e));return out
    finally:c.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True);p.add_argument('--run-folder',type=Path)
    p.add_argument('--expected-pid',type=int);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('preserve existing output')
    result=analyze_trace(a.trace,json.loads(a.inventory.read_text()),a.run_folder,a.expected_pid)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'state':result['state'],'requests':len(result['requests'])}))
