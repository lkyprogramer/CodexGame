"""Bounded P01B host capture adapter; the legacy P01 runner remains strict."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.frontier import warm_run as legacy
from tools.frontier.identity import prepared_env, source_changes

PHASE = 'frontier/P01B'
TRACE_ENV = 'STRATA_LAB_P01B_TRACE'
FORBIDDEN = {'STRATA_VERIFY_PROFILE', 'STRATA_STAGE_PIN', 'STRATA_ROUTE_RESIDENT'}
NATIVE_SCOPE = 'host_only_no_cuda_or_graph_changes'
GAP_SCOPE = 'serial_host_after_verify_sync_before_commit_launch'


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def verified_json(path, expected, reason):
    path = Path(path)
    require(path.is_file() and legacy.sha256(path) == expected, reason)
    return legacy.load(path)


def validate_plan(plan, policy):
    """Reuse P01 budget checks without changing its fixed-output contract."""
    require(plan.get('output_policy') == 'natural_eos_up_to_2048', 'P01B_OUTPUT_POLICY')
    require(plan.get('collection') == 'host_only_bounded_trace', 'P01B_COLLECTION_POLICY')
    require(plan.get('target_output_tokens_per_request') is None, 'P01B_NATURAL_EOS_REQUIRED')
    normalized = copy.deepcopy(plan)
    normalized['target_output_tokens_per_request'] = 2048
    normalized['collection'] = 'existing_low_overhead_logs_single_arm'
    for engine in normalized.get('matrix', []):
        require(engine.get('collection') == 'host_only_bounded_trace', 'P01B_COLLECTION_POLICY')
        engine['collection'] = normalized['collection']
        for request in engine.get('requests', []):
            require(request.get('target_output_tokens') is None, 'P01B_NATURAL_EOS_REQUIRED')
            request['target_output_tokens'] = 2048
    ref = normalized.get('execution_instruction_reference')
    receipt = normalized.get('reference_evidence', {}).get(ref, {})
    require(receipt.get('scope') == 'p01b_diagnostic', 'P01B_AUTHORIZATION_SCOPE')
    receipt['scope'] = 'p01_diagnostic'
    require(normalized.get('planning_only') is False, 'EXECUTION_SCOPE_NOT_BOUND')
    return legacy.validate_warm_plan(normalized, policy)


def request_outcome(response, count, config, index):
    require(not response.get('error') and response.get('done') is True, 'INCOMPLETE_RESPONSE')
    require(not response.get('tools'), 'UNAUTHORIZED_TOOL_OUTPUT')
    require(response.get('finish_reason') in ('stop', 'length'), 'UNEXPECTED_FINISH_REASON')
    legacy.boundary.audit_usage({'max_tokens': 2048}, response, count, config)
    m = legacy.http.measurements(response)
    require(type(m['read_tokens']) is int and type(m['reused_tokens']) is int
            and min(m['read_tokens'], m['reused_tokens']) >= 0, 'MISSING_READ_REUSE')
    require(m['read_tokens'] + m['reused_tokens'] == m['prompt_tokens'], 'READ_REUSE_ACCOUNTING')
    require(index != 0 or m['reused_tokens'] == 0, 'PRIME_NOT_COLD')
    if m['generated_tokens'] == 0:
        return 'INSUFFICIENT_ZERO_OUTPUT'
    if index and m['reused_tokens'] <= 0:
        return 'INSUFFICIENT_NO_WARM_REUSE'
    return 'REQUEST_COMPLETE'


def capture_identity(identity):
    capture = identity['capture']
    base = verified_json(capture['base_identity_path'], capture['base_identity_sha256'], 'BASE_IDENTITY_DRIFT')
    require({k: v for k, v in identity.items() if k != 'capture'} == base, 'BASE_IDENTITY_FIELDS_DRIFT')
    require(base['config']['source_sha256'] == capture['base_runtime_config_sha256'], 'BASE_CONFIG_IDENTITY_DRIFT')
    config = verified_json(capture['base_runtime_config_path'], capture['base_runtime_config_sha256'], 'BASE_CONFIG_DRIFT')
    build = verified_json(capture['build_receipt_path'], capture['build_receipt_sha256'], 'CAPTURE_BUILD_RECEIPT_DRIFT')
    gate = verified_json(capture['collection_gate_path'], capture['collection_gate_sha256'], 'COLLECTION_GATE_DRIFT')
    require(all(gate.get(key) == 'PASS' for key in ('status', 'source_review', 'cpu_tests', 'clock_check', 'observer_cpu_cost'))
            and gate.get('native_scope') == NATIVE_SCOPE
            and gate.get('graph_gap_scope') == GAP_SCOPE
            and type(gate.get('max_windows_per_request')) is int
            and gate['max_windows_per_request'] == 2048, 'COLLECTION_GATE_NOT_PASS')
    require(build.get('source_head') == base['source']['head'], 'CAPTURE_SOURCE_HEAD_DRIFT')
    require(isinstance(build.get('native_files'), list)
            and len(build['native_files']) == 2
            and set(build['native_files']) == {'src/program/generate.cpp', 'include/strata/core/lab_p01b_trace.hpp'},
            'CAPTURE_NATIVE_FILE_SCOPE')
    require(build.get('source_files') == capture['source_files'], 'CAPTURE_SOURCE_MANIFEST_DRIFT')
    return capture, base, config, build


def verify_native(tree, capture, base, build):
    tree = Path(tree)
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tree, text=True).strip()
    require(head == build['source_head'], 'CAPTURE_SOURCE_HEAD_DRIFT')
    tracked = subprocess.check_output(['git', 'ls-files'], cwd=tree, text=True).splitlines()
    expected = capture['source_files']
    require(set(expected) == set(tracked) | set(build['native_files']), 'CAPTURE_SOURCE_SET_DRIFT')
    for name, digest in expected.items():
        path = tree / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and path.is_file() and legacy.sha256(path) == digest, 'CAPTURE_SOURCE_DRIFT: ' + name)
    dirty, patch = source_changes(tree)
    # The added header is untracked until archived; tracked delta still has an exact hash.
    require(set(dirty) == set(base['source']['port_files']) | (set(build['native_files']) & set(tracked)),
            'CAPTURE_SOURCE_DELTA_DRIFT')
    import hashlib
    require(hashlib.sha256(patch).hexdigest() == build['patch_sha256'], 'CAPTURE_PATCH_DRIFT')
    for name, digest in base['source']['port_files'].items():
        require(expected.get(name) == digest, 'PORT_DRIFT')
    require(Path(build['binary_path']).resolve() == (tree / 'build-lab/strata').resolve(), 'CAPTURE_BINARY_PATH_DRIFT')
    require(legacy.sha256(Path(build['binary_path'])) == build['binary_sha256'], 'CAPTURE_BINARY_DRIFT')


def preflight(config, identity, plan, inputs, policy):
    capture, base, original, build = capture_identity(identity)
    require(Path(plan['runtime_config_path']).is_file(), 'DERIVED_CONFIG_MISSING')
    raw_config = legacy.load(plan['runtime_config_path'])
    allowed = capture['allowed_config_changes']
    require(set(allowed) <= {'deployed_repo', 'workspace', 'extra_frozen_env'}, 'CONFIG_CHANGE_SCOPE')
    expected = dict(original, **allowed)
    require(raw_config == expected, 'DERIVED_CONFIG_DRIFT')
    require(Path(expected['deployed_repo']).resolve() != Path(original['deployed_repo']).resolve(), 'CAPTURE_TREE_NOT_ISOLATED')
    require(Path(expected['workspace']).resolve() != Path(original['workspace']).resolve(), 'CAPTURE_WORKSPACE_NOT_ISOLATED')
    base_extra = original.get('extra_frozen_env', {})
    changed_extra = expected.get('extra_frozen_env', {})
    require({k: v for k, v in changed_extra.items() if k != TRACE_ENV} == base_extra, 'CAPTURE_ENV_DELTA')
    require(not FORBIDDEN.intersection(base['config']['env'])
            and not FORBIDDEN.intersection(changed_extra), 'FORBIDDEN_ENV_PRESENT')
    require(config['port'] == 18089 and config['max_context'] == 131072
            and config['safety_tokens'] == 4096, 'ISOLATION_DRIFT')
    require(config['min_available_mib'] >= 4096 and config['gpu_temp_abort_c'] <= 85, 'RESOURCE_GUARD_WEAKENED')
    tree = Path(config['deployed_repo'])
    verify_native(tree, capture, base, build)
    require(legacy.sha256(Path(config['deployed_config'])) == base['config']['engine_config_sha256'], 'ENGINE_CONFIG_DRIFT')
    prepared = legacy.make_run_config(config, tree, 'cfg', {}, Path(config['workspace']) / 'p01b-preflight-not-created')
    actual = prepared_env(prepared['env'])
    require(not FORBIDDEN.intersection(actual), 'FORBIDDEN_ENV_PRESENT')
    require({k: v for k, v in actual.items() if k != TRACE_ENV} == base['config']['env'], 'PREPARED_ENV_DRIFT')
    legacy.verify_assets(config)
    require(legacy.sha256(Path(config['workspace']) / 'assets.json') == base['assets']['manifest_sha256'], 'ASSET_MANIFEST_DRIFT')
    validate_plan(plan, policy)
    for field in ('execution_instruction_reference', 'baseline_identity_path', 'gpu_handoff_reference'):
        ref = plan[field]
        require(legacy.sha256(Path(inputs) / ref) == plan['reference_evidence'][ref]['sha256'], 'REFERENCE_HASH_DRIFT')
    for req in plan['matrix'][0]['requests']:
        require(legacy.hash_obj(legacy.load(Path(inputs) / req['input_reference'])) == req['body_or_recipe_sha256'], 'INPUT_DRIFT')
    return tree


def configure(config, identity, out):
    prefix = str(Path(out).resolve() / 'native-trace')
    require(identity['capture']['trace_prefix'] == prefix, 'TRACE_PREFIX_DRIFT')
    extra = dict(config.get('extra_frozen_env', {}))
    require(not FORBIDDEN.intersection(extra), 'FORBIDDEN_ENV_PRESENT')
    require(TRACE_ENV not in extra or extra[TRACE_ENV] == prefix, 'TRACE_PREFIX_DRIFT')
    extra[TRACE_ENV] = prefix
    return dict(config, extra_frozen_env=extra)


def activation(server, identity, lock):
    receipt = legacy.baseline.activation_receipt(server)
    require(receipt['expert_cache_slots'] == lock['research_baseline']['reported_expert_slots'], 'ACTUAL_SLOT_DRIFT')
    capture, base, _, build = capture_identity(identity)
    pid = server.engine_audit[0]['pid']
    env = dict(x.decode().split('=', 1) for x in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if x.startswith(b'STRATA_'))
    expected = dict(base['config']['env'], **{TRACE_ENV: capture['trace_prefix']})
    require(env == expected and not FORBIDDEN.intersection(env), 'ACTUAL_ENV_DRIFT')
    actual_binary = Path(f'/proc/{pid}/exe').resolve()
    require(actual_binary == Path(build['binary_path']).resolve()
            and legacy.sha256(actual_binary) == build['binary_sha256']
            and legacy.sha256(Path(server.cfg['exe'])) == build['binary_sha256'], 'ACTUAL_BINARY_DRIFT')
    receipt.update(native_pid=pid, native_identity=server.engine_audit[0], actual_strata_env=env,
                   binary_sha256=build['binary_sha256'], clock_domain='host CLOCK_MONOTONIC')
    return receipt


def finalize(out, identity, rows, reason):
    try:
        from tools.frontier.p01b_analysis import summarize_capture
        result = summarize_capture(out, identity, rows)
        require(all(key in result for key in ('ANALYSIS', 'DEPENDENCIES', 'WINDOWS', 'QUALIFICATION')), 'ANALYSIS_CONTRACT')
        if reason:
            result['QUALIFICATION'] = {'status': 'INSUFFICIENT', 'reason': reason,
                                       'new_candidate_qualified': False, 'causal_speedup_claim': False}
        return result
    except Exception as error:
        return {'ANALYSIS': {'status': 'INSUFFICIENT', 'error': str(error)},
                'DEPENDENCIES': {'status': 'UNKNOWN', 'reason': str(error)}, 'WINDOWS': [],
                'QUALIFICATION': {'status': 'INSUFFICIENT', 'reason': reason or str(error),
                                  'new_candidate_qualified': False, 'causal_speedup_claim': False}}


class Adapter:
    phase = PHASE
    preflight = staticmethod(preflight)
    configure = staticmethod(configure)
    activation = staticmethod(activation)
    request_outcome = staticmethod(request_outcome)
    finalize = staticmethod(finalize)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'identity', 'out'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('--execute required; this starts an authorized GPU engine')
    print(legacy.run_diagnostic(args.plan, args.identity, args.out, adapter=Adapter()))


if __name__ == '__main__':
    main()
