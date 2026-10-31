"""Validate this plan package offline; successful validation is not GPU qualification."""
import argparse
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from common import guarded, load, require

FIXED = {'schema_version': 1, 'initial_state': 'PLAN_ONLY', 'deployment_approved': False, 'live_adapter_included': False,
         'gpu_experiments_performed_by_package_author': False,
         'limits.context_ceiling_tokens': 131072, 'limits.context_safety_tokens': 4096,
         'limits.min_mem_available_mib': 4096, 'limits.gpu_temp_abort_c': 85,
         'limits.experiment_port': 18089, 'limits.max_concurrent_gpu_jobs': 1,
         'limits.max_initial_diagnostic_engine_starts': 1, 'limits.max_initial_diagnostic_work_requests': 3,
         'limits.max_initial_diagnostic_wall_seconds': 3600, 'limits.max_active_candidates': 1,
         'limits.diagnostic_cleanup_reserve_seconds': 120,
         'limits.diagnostic_request_deadline_seconds': 600, 'limits.diagnostic_output_tokens': 2048,
         'diagnostic.sequence': ['prime', 'append_1', 'append_2'],
         'diagnostic.prime_context_target_tokens': 102400, 'diagnostic.append_new_read_target_tokens': None,
         'diagnostic.append_new_read_policy': 'observe_actual_pi_followup',
         'diagnostic.new_read_includes_pt0_history_reread': True, 'diagnostic.preserve_actual_history': True,
         'diagnostic.short_output_status': 'INSUFFICIENT',
         'diagnostic.collection': 'existing_low_overhead_logs_single_arm',
         'diagnostic.allow_extra_control_or_profiler': False, 'diagnostic.causal_speedup_claim_allowed': False,
         'historical_quality_failures.count': 6, 'historical_quality_failures.status': 'UNRESOLVED', 'historical_quality_failures.may_delete_or_rescore': False,
         'numerical_classes': ['E0', 'E1', 'Q'],
         'formal_performance.initial_pairs': 6, 'formal_performance.minimum_time_improvement': 0.04,
         'formal_performance.primary_metric': 'decode_ms', 'formal_performance.calibration_max_pairs': 3,
         'formal_performance.order': ['AC', 'CA', 'CA', 'AC', 'AC', 'CA'],
         'formal_performance.unit': 'independent_fresh_engine_pair', 'formal_performance.confidence': 0.95,
         'formal_performance.ratio': 'candidate_time/baseline_time',
         'formal_performance.resampling': 'exact_paired_log_ratio_bootstrap',
         'formal_performance.primary_gate': 'ratio_ci_upper <= 1 - max(0.04, 2 * preregistered_aa_noise)',
         'formal_performance.noise_multiplier': 2.0, 'formal_performance.non_target_ratio_ci_upper_max': 1.02,
         'formal_performance.allow_optional_stopping': False, 'formal_performance.allow_replacement_of_failed_samples': False,
         'formal_performance.allows_deployment': False, 'qualification.requires_dependency_evidence': True,
         'qualification.hard_reject_optimistic_gain_lt': 0.04, 'qualification.required_realistic_gain_floor': 0.04,
         'qualification.preferred_exposed_fraction_floor': 0.08, 'qualification.requires_source_delta': True,
         'qualification.unknown_critical_path': 'INSUFFICIENT', 'quality.relative_ni_margin': 0.02,
         'quality.e1_q_initial_status': 'DEFERRED_QUALITY', 'quality.sampling_distribution_proof_required_for_speculation': True,
         'qualification.profiler_results_are_performance': False, 'quality.absolute_quality_separate': True,
         'quality.e0_parity_waives_task_quality': False}


def local(root, relative):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(), 'Relative path required')
    target = (root / relative).resolve()
    require(target.is_relative_to(root) and target.exists(), 'Missing or escaping relative path: ' + relative)
    return target


def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child; yield from walk(child)
    elif isinstance(value, list):
        for child in value: yield from walk(child)


def acyclic(graph):
    done, active = set(), set()
    def visit(node):
        require(node in graph, 'Missing dependency: ' + str(node)); require(node not in active, 'Dependency cycle at ' + node)
        if node in done: return
        active.add(node)
        for dep in graph[node]: visit(dep)
        active.remove(node); done.add(node)
    for node in graph: visit(node)


def validate_diagnostic_template(plan):
    """Check the unbound offline template; never certify a live plan or actual reads."""
    fixed = {'template_only': True, 'state': 'UNBOUND_NOT_EXECUTED',
             'max_engine_starts': 1, 'max_work_requests': 3, 'wall_budget_seconds': 3600,
             'cleanup_reserve_seconds': 120, 'request_deadline_seconds': 600,
             'target_output_tokens_per_request': 2048, 'max_output_tokens_per_request': 2048,
             'short_output_status': 'INSUFFICIENT', 'context_total_ceiling': 131072,
             'context_safety_tokens': 4096, 'collection': 'existing_low_overhead_logs_single_arm',
             'allow_extra_control_or_profiler': False, 'retry_or_replace_failed_sample': False}
    for key, expected in fixed.items():
        require(type(plan.get(key)) is type(expected) and plan[key] == expected,
                'Diagnostic template hard value changed: ' + key)
    matrix = plan['matrix']
    require(isinstance(matrix, list) and len(matrix) == 1, 'Diagnostic requires one engine')
    engine = matrix[0]
    require(engine['engine_label'] == 'D1' and engine['collection'] == fixed['collection'],
            'Unexpected diagnostic engine/collection')
    require(engine['append_new_read_includes_pt0_history_reread'] is True, 'New read must include PT0 reread')
    requests = engine['requests']
    require(isinstance(requests, list) and [q['request_label'] for q in requests] == ['prime', 'append_1', 'append_2'],
            'Diagnostic requires prime and two ordered appends')
    for index, request in enumerate(requests):
        for key, expected in [('request_deadline_seconds', 600), ('target_output_tokens', 2048), ('max_output_tokens', 2048)]:
            require(type(request.get(key)) is int and request[key] == expected, 'Diagnostic request budget changed: ' + key)
        require(request['actual_history_hash_policy'] == 'own_generated_history_no_rewrite', 'Actual history must be preserved')
        require(request['validate_before_send'] == 'rendered_input_plus_2048_plus_4096_le_131072', 'Missing actual context budget check')
        require(request['validate_after_response'] == 'output_2048_and_record_actual_read_reuse_preserve_history', 'Missing output/read/reuse check')
        require(request['context_target_tokens'] == (102400 if index == 0 else None), 'Unexpected context target')
        require(request['new_read_target_tokens'] is None, 'New-read target forbidden')
        if index:
            require(request.get('new_read_policy') == 'observe_actual_pi_followup', 'Actual Pi followup policy required')
            require('new_read_allowed_range_tokens' in request and request['new_read_allowed_range_tokens'] is None,
                    'New-read range gate forbidden')
            require(request.get('append_padding_allowed') is False, 'Followup padding forbidden')
            require(type(request.get('append_user_tokens_upper_bound')) is int and request['append_user_tokens_upper_bound'] == 256,
                    'Freeze conservative user-message budget')
            require(request.get('append_user_message_sha256') is None and request.get('append_user_message_source_reference') is None,
                    'Unbound template must not invent real Pi message identities')


def evaluate(root):
    root = Path(root).resolve(); documents = {}
    for path in root.rglob('*.json'):
        data = load(path); documents[path.relative_to(root).as_posix()] = data
        for key, value in walk(data):
            if key in {'deployment_approved', 'allows_deployment', 'automatic_deployment', 'auto_deploy'}:
                require(value is False, 'Automatic deployment is forbidden: ' + str(path))
    policy = documents['config/policy.json']; lock = documents['sources/LOCK.json']
    validate_diagnostic_template(documents['templates/PREREGISTRATION.json'])
    for path, expected in FIXED.items():
        value = policy
        for key in path.split('.'): value = value[key]
        require(type(value) is type(expected) and value == expected, 'Policy hard value changed: ' + path)
    require(policy['forbidden_env'] == ['STRATA_STAGE_PIN', 'STRATA_ROUTE_RESIDENT'], 'Forbidden env list changed')
    for record in [lock.get(name) for name in ('user_repository', 'production_record', 'research_baseline')] + lock['donors']:
        require(isinstance(record, dict) and 'sha' in record, 'LOCK missing required full SHA')
    require('binary_sha256_reported' in lock['research_baseline'], 'LOCK missing reported binary SHA256')
    for key, value in walk(lock):
        size = 64 if 'sha256' in key else 40 if key == 'sha' or key.endswith('_sha') else None
        if size: require(isinstance(value, str) and re.fullmatch(r'[0-9a-fA-F]{%d}' % size, value), 'LOCK needs full hash: ' + key)
        if key == 'automatic_upgrade': require(value is False, 'Automatic baseline upgrade forbidden')
    phases = documents['config/task_dag.json']['phases']; phase_graph = {}; tasks = {}; owner = {}
    require(isinstance(phases, list) and phases, 'Nonempty phases required')
    for phase in phases:
        pid = phase['id']; require(isinstance(pid, str) and pid and pid not in phase_graph, 'Duplicate/invalid phase ID')
        require(isinstance(phase['depends_on'], list) and phase['tasks'], 'Phase dependencies/tasks required')
        phase_graph[pid] = phase['depends_on']
        for task in phase['tasks']:
            tid = task['id']; require(isinstance(tid, str) and tid and tid not in tasks, 'Duplicate/invalid task ID')
            require(isinstance(task['depends_on'], list), 'Task dependencies must be a list')
            require(local(root, task['doc']).is_file(), 'Task doc must be file'); tasks[tid] = task; owner[tid] = pid
    require(not set(phase_graph) & set(tasks), 'Phase/task IDs collide'); acyclic(phase_graph)
    def expand(dep):
        return [tid for tid in tasks if owner[tid] == dep] if dep in phase_graph else [dep]
    graph = {tid: [x for dep in task['depends_on'] + phase_graph[owner[tid]] for x in expand(dep)] for tid, task in tasks.items()}
    acyclic(graph)
    seen = set()
    for candidate in documents['config/candidates.json']['candidates']:
        cid = candidate['id']; require(isinstance(cid, str) and cid and cid not in seen, 'Duplicate/invalid candidate ID'); seen.add(cid)
        require(candidate['title'] and candidate['status'], 'Candidate title/status required')
        require(candidate['numerical_class'] in policy['numerical_classes'], 'Unknown numerical class')
        require(local(root, candidate['doc']).is_file(), 'Candidate doc must be file')
    links = 0
    for path in root.rglob('*.md'):
        for target in re.findall(r'!?\[[^\]]*\]\(<?([^\s)>]+)>?(?:\s+[^)]*)?\)', path.read_text(encoding='utf-8')):
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path: continue
            local(root, (path.parent.relative_to(root) / unquote(parsed.path)).as_posix()); links += 1
    return {'status': 'PACKAGE_VALID', 'json_files': len(documents), 'relative_links': links,
            'tasks': len(tasks), 'candidates': len(seen), 'deployment_approved': False, 'gpu_validation': 'NOT_RUN'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--output', type=Path); args = parser.parse_args()
    raise SystemExit(guarded(lambda: evaluate(args.root), args.output))
