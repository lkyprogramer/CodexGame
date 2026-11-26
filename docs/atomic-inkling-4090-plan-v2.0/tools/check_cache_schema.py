#!/usr/bin/env python3
"""CPU-only synthetic structural checks. Never runs or qualifies an engine.

Requires jsonschema in the selected Python environment. Does not install it.
All constructed published records and hashes are SYNTHETIC, NOT EVIDENCE.
Semantic probes intentionally show cases accepted by JSON Schema that L01's
future semantic validator must reject. They do not count as runtime PASS.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def artifact(label):
    return {'path': 'synthetic-schema-fixture://NOT-EVIDENCE/'+label,
            'sha256': digest('SYNTHETIC-NOT-EVIDENCE:'+label)}

def published(example):
    x=deepcopy(example)
    x.update(record_mode='observed',publication_state='PUBLISHED',
             object_id='SYNTHETIC-NOT-A-REAL-CHECKPOINT')
    x['continuation_binding']={
        'owner_session_id':'SYNTHETIC-session','logical_request_id':'SYNTHETIC-request',
        'resume_generation':0,'committed_output_tokens':0,'effect_journal_watermark':0,
        'authoritative_journal_ref':artifact('commit-journal')}
    for key in x['identity']:
        if key.endswith('sha256') or key.endswith('fingerprint'):
            if key!='draft_fingerprint':x['identity'][key]=digest(key)
    x['prefix'].update(token_count=4,token_ids_ref=artifact('token-ids'),
                       token_ids_sha256=digest('token-ids'),absolute_start_position=0,
                       checkpoint_boundary_complete=True)
    x['cursor'].update(committed_tokens=4,kv_consumed_tokens=4,
                       next_forward_position=4,last_emitted_in_kv=True,
                       pending_correction_or_bonus=False,
                       next_logits_recipe_ref=artifact('next-logits'),
                       quiescent_committed_boundary=True)
    x['state_inventory']=[{
        'member_id':'SYNTHETIC-global-k','source_symbols':['SYNTHETIC::state.k'],
        'scope':'per_logical_slot','disposition':'PERSIST','chunk_ids':['chunk-k'],
        'rebuild_or_absence_proof_ref':None}]
    x['chunks']=[{
        'chunk_id':'chunk-k','component':'global_k','logical_slot':0,
        'token_range':{'begin':0,'end_exclusive':4},
        'raw_format':{'dtype':'SYNTHETIC_BF16','layout_sha256':digest('layout'),
                      'quant_block_elements':None,'quant_block_bytes':None,
                      'byte_order':'little'},
        'raw_bytes':8,'raw_sha256':digest('raw'),
        'logical_layout':{'physical_layer':0,'loop_pass':0,'head_begin':0,
                          'head_end_exclusive':1,'shape':[4,1],
                          'strides_bytes':[2,2],'valid_bytes':8},
        'representations':[{'representation_id':'SYNTHETIC-repr','kind':'raw',
            'codec_profile_sha256':None,'location_domain':'host',
            'encoded_sha256':digest('raw'),'stored_bytes':8,'allocated_bytes':8,
            'output_upper_bound_bytes':8,'resource_id':'SYNTHETIC-resource',
            'physical_allocation':{'physical_store_id':'SYNTHETIC-host',
                'allocation_id':'SYNTHETIC-backing','allocation_generation':0,'medium':'host'},
            'view_generation':0,'arena_generation':None,'artifact_ref':artifact('record')}]}]
    x['resource_plan_ref']=artifact('resource-plan')
    x['operation_log_ref']=artifact('operations')
    return x

def set_at(x,path,value):
    for part in path[:-1]:x=x[part]
    x[path[-1]]=value

def cases(example):
    out=[]
    def add(name,base,category,expected,path=None,value=None,modify=None):
        x=deepcopy(base)
        if path is not None:set_at(x,path,value)
        if modify is not None:modify(x)
        out.append((name,category,expected,x))
    pub=published(example)
    add('planned_example',example,'positive_structure',True)
    add('building_unmeasured',example,'positive_structure',True,
        modify=lambda x:x.update(record_mode='observed',publication_state='BUILDING'))
    add('published_synthetic',pub,'positive_structure',True)
    add('validated_synthetic',pub,'positive_structure',True,('publication_state',),'VALIDATED')
    add('lossless_with_profile',pub,'positive_structure',True,
        modify=lambda x:x['chunks'][0]['representations'][0].update(
            kind='lossless_encoded',codec_profile_sha256=digest('codec')))
    add('rebuild_member_with_proof',pub,'positive_structure',True,
        modify=lambda x:x['state_inventory'].append({
            'member_id':'synthetic-rebuild','source_symbols':['SYNTHETIC::draft'],
            'scope':'per_sequence','disposition':'REBUILD','chunk_ids':[],
            'rebuild_or_absence_proof_ref':artifact('rebuild-proof')}))
    add('runtime_handle_not_persisted',pub,'positive_structure',True,
        modify=lambda x:x['state_inventory'].append({
            'member_id':'synthetic-handle','source_symbols':['SYNTHETIC::event'],
            'scope':'runtime_resource_only','disposition':'DO_NOT_SERIALIZE_RUNTIME_HANDLE',
            'chunk_ids':[],'rebuild_or_absence_proof_ref':None}))
    negatives=[
        ('qualification_cannot_self_grant',('qualification',),'PASS'),
        ('wrong_record_kind',('record_kind',),'gpu_result'),
        ('wrong_object_kind',('object_kind',),'arbitrary_bytes'),
        ('published_target_null',('identity','target_fingerprint'),None),
        ('published_inventory_hash_null',('identity','state_inventory_sha256'),None),
        ('published_permission_null',('identity','permission_scope_sha256'),None),
        ('incomplete_prefix',('prefix','checkpoint_boundary_complete'),False),
        ('token_count_null',('prefix','token_count'),None),
        ('token_artifact_null',('prefix','token_ids_ref'),None),
        ('cursor_count_null',('cursor','kv_consumed_tokens'),None),
        ('non_quiescent',('cursor','quiescent_committed_boundary'),False),
        ('pending_correction',('cursor','pending_correction_or_bonus'),True),
        ('no_next_logits_recipe',('cursor','next_logits_recipe_ref'),None),
        ('empty_inventory',('state_inventory',),[]),
        ('persist_missing_chunk',('state_inventory',0,'chunk_ids'),[]),
        ('empty_chunks',('chunks',),[]),
        ('bad_raw_hash',('chunks',0,'raw_sha256'),'bad'),
        ('missing_layout_hash',('chunks',0,'raw_format','layout_sha256'),None),
        ('missing_record_artifact',('chunks',0,'representations',0,'artifact_ref'),None),
        ('negative_stored_bytes',('chunks',0,'representations',0,'stored_bytes'),-1),
        ('null_view_generation',('chunks',0,'representations',0,'view_generation'),None),
        ('missing_physical_allocation',('chunks',0,'representations',0,'physical_allocation'),None),
        ('null_allocation_generation',('chunks',0,'representations',0,'physical_allocation','allocation_generation'),None),
        ('continuation_without_owner',('continuation_binding',),None),
        ('empty_logical_request',('continuation_binding','logical_request_id'),''),
        ('missing_journal_binding',('continuation_binding','authoritative_journal_ref'),None),
        ('negative_shape',('chunks',0,'logical_layout','shape'),[-1]),
        ('empty_shape',('chunks',0,'logical_layout','shape'),[]),
        ('missing_resource_plan',('resource_plan_ref',),None),
        ('missing_operation_log',('operation_log_ref',),None),
    ]
    for name,path,value in negatives:add(name,pub,'negative_structure',False,path,value)
    add('planned_cannot_publish',pub,'negative_structure',False,('record_mode',),'planned')
    add('lossless_missing_profile',pub,'negative_structure',False,
        ('chunks',0,'representations',0,'kind'),'lossless_encoded')
    add('rebuild_missing_proof',pub,'negative_structure',False,
        ('state_inventory',0,'disposition'),'REBUILD')
    add('runtime_handle_carries_bytes',pub,'negative_structure',False,
        ('state_inventory',0,'disposition'),'DO_NOT_SERIALIZE_RUNTIME_HANDLE')
    add('unknown_top_field',pub,'negative_structure',False,
        modify=lambda x:x.update(pretend_gate='PASS'))
    for component in ('sampler_rng','service_commit'):
        add('prefix_forbids_'+component,pub,'negative_structure',False,
            modify=lambda x,c=component:(x.update(object_kind='model_prefix_checkpoint',continuation_binding=None),
                                         x['chunks'][0].update(component=c)))
    add('prefix_with_private_owner',pub,'negative_structure',False,
        ('object_kind',),'model_prefix_checkpoint')
    add('published_model_prefix',pub,'positive_structure',True,
        modify=lambda x:x.update(object_kind='model_prefix_checkpoint',continuation_binding=None))
    probes=[
        ('reversed_token_range',('chunks',0,'token_range'),{'begin':4,'end_exclusive':1}),
        ('reversed_head_range',('chunks',0,'logical_layout','head_end_exclusive'),0),
        ('cursor_semantic_mismatch',('cursor','kv_consumed_tokens'),9000),
        ('missing_referenced_chunk',('state_inventory',0,'chunk_ids'),['NONEXISTENT']),
        ('shape_raw_bytes_mismatch',('chunks',0,'raw_bytes'),9000),
        ('allocated_less_than_stored',('chunks',0,'representations',0,'allocated_bytes'),1),
        ('undersized_decode_bound',('chunks',0,'representations',0,'output_upper_bound_bytes'),1),
        ('unverified_live_owner',('continuation_binding','logical_request_id'),'SYNTHETIC-other-request'),
        ('medium_mapping_mismatch',('chunks',0,'representations',0,'physical_allocation','medium'),'gpu'),
    ]
    for name,path,value in probes:add(name,pub,'semantic_limit_expected_acceptance',True,path,value)
    add('duplicate_chunk_identity',pub,'semantic_limit_expected_acceptance',True,
        modify=lambda x:x['chunks'].append(deepcopy(x['chunks'][0])))
    add('nonexistent_artifacts_and_fake_hashes',pub,'semantic_limit_expected_acceptance',True)
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        print('BLOCKED: jsonschema is unavailable; no installation attempted.',file=sys.stderr)
        return 2
    schema_path=args.package/'manifests/cache-object-contract.json'
    example_path=args.package/'manifests/cache-object-example.json'
    schema=json.loads(schema_path.read_text());example=json.loads(example_path.read_text())
    Draft202012Validator.check_schema(schema);v=Draft202012Validator(schema)
    results=[]
    for name,category,expected,x in cases(example):
        errors=list(v.iter_errors(x));actual=not errors
        results.append({'case_id':name,'category':category,'synthetic':True,
            'input_sha256':digest(json.dumps(x,sort_keys=True)),
            'expected_schema_acceptance':expected,'observed_schema_acceptance':actual,
            'matched':expected==actual,'error_count':len(errors),
            'error_paths':[list(e.absolute_path) for e in errors]})
    groups={cat:{'total':sum(r['category']==cat for r in results),
                 'matched':sum(r['category']==cat and r['matched'] for r in results)}
            for cat in sorted({r['category'] for r in results})}
    summary={'total_cases':len(results),'matched':sum(r['matched'] for r in results),
             'categories':groups,'mismatches':[r['case_id'] for r in results if not r['matched']]}
    report={'report_kind':'synthetic_cache_schema_checks','schema_sha256':hashlib.sha256(schema_path.read_bytes()).hexdigest(),
            'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'executed_gpu':False,'executed_engine':False,'grants_qualification':False,
            'semantic_validator_implemented':False,'summary':summary,'results':results}
    if args.output:
        target=args.output.resolve()
        if target in (schema_path.resolve(),example_path.resolve(),Path(__file__).resolve()):
            ap.error('output must not overwrite schema, example or harness')
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if not summary['mismatches'] else 1

if __name__=='__main__':raise SystemExit(main())
