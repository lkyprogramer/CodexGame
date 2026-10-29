"""Offline metadata-only campaign composition. Never emits candidate text or quality winners."""
from __future__ import annotations
import argparse
from collections import Counter
import importlib
import json
import math
from pathlib import Path
import random
import re
import sys

SEED = 20261029
DRAWS = 10000

def read(path, fallback=None):
    return json.loads(path.read_text()) if path.is_file() else fallback

def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0

def bootstrap(pairs, quantile):
    # Resample complete paired run blocks, not individual pages or families.
    if not pairs:
        return None
    rng = random.Random(SEED)
    values = []
    for _ in range(DRAWS):
        sample = rng.choices(pairs, k=len(pairs))
        values.append(sum(p[0] for p in sample) / sum(p[1] for p in sample))
    return {'estimate_ratio_of_total_walls_mini_over_ovis': sum(p[0] for p in pairs) / sum(p[1] for p in pairs),
            'percentile_95_CI': [quantile(values, .025), quantile(values, .975)],
            'resampling_unit': 'paired_run_block', 'pair_count': len(pairs), 'draws': DRAWS, 'seed': SEED,
            'scope': 'conditional on these fixed inputs; not a source-family generalization CI'}

def window(summary, events):
    starts = [e.get('batch_start_monotonic') for e in events if e.get('event') == 'timed_workload_start']
    wall = summary.get('batch_wall_seconds')
    if len(starts) != 1 or not isinstance(starts[0], (int, float)) or not positive(wall):
        return None
    return starts[0], starts[0] + wall

def resource_windows(reporting, rows, record, timed, attempted):
    result = {'timed_window': list(timed) if timed else None,
              'end_basis': 'timed_workload_start.batch_start_monotonic + measured summary.batch_wall_seconds; core has no separate batch_end event',
              'pre_idle': None, 'post_idle': None, 'timed': None}
    idle = []
    for label in ('pre_idle', 'post_idle'):
        span = record.get(label, {})
        a, b = span.get('start_monotonic'), span.get('end_monotonic')
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b - a >= 10:
            measured = reporting.resources(rows, a, b, 0)
            measured['duration_seconds'] = b - a
            measured['mean_GPU_board_watts'] = measured['GPU_J_batch_raw'] / (b - a) if measured['GPU_J_batch_raw'] is not None else None
            result[label] = measured
            if measured['mean_GPU_board_watts'] is not None:
                idle.append((measured['GPU_J_batch_raw'], b - a))
    baseline = sum(p[0] for p in idle) / sum(p[1] for p in idle) if len(idle) == 2 else None
    result['idle_board_watts_both_10s_windows'] = baseline
    if timed:
        result['timed'] = reporting.resources(rows, *timed, attempted, idle_watts=baseline)
    result['CPU_energy_status'] = 'UNAVAILABLE_NO_CPU_POWER_METER'
    result['cost_status'] = 'UNAVAILABLE_NO_TARIFF_OR_WHOLE_SYSTEM_METER'
    return result

def api_histograms(directory):
    """Server request histograms span CPU-worker development warmup plus formal work."""
    before, after = directory / 'api-before-warmup.prom', directory / 'api-after-idle.prom'
    names = ('time_to_first_token_seconds', 'time_per_output_token_seconds', 'inter_token_latency_seconds',
             'request_prefill_time_seconds', 'request_decode_time_seconds')
    result = {'status': 'UNAVAILABLE_MISSING_SNAPSHOTS',
              'scope': 'API request layer including same-worker development warmup, recovery and formal requests; not formal-page TTFT',
              'formal_page_TTFT_seconds': None, 'nonstream_TTFT_status': 'UNAVAILABLE_NOT_MEASURED_BY_CLIENT', 'histograms': {}}
    if not before.is_file() or not after.is_file():
        return result
    def parse(path):
        values = {}
        for line in path.read_text().splitlines():
            match = re.match(r'^vllm:(' + '|'.join(names) + r')_(sum|count)(\{[^}]*\})?\s+(\S+)(?:\s+\S+)?$', line)
            if match:
                value = float(match[4])
                if not math.isfinite(value):
                    raise ValueError('nonfinite metric')
                values[(match[1], match[2], match[3] or '')] = value
        return values
    try:
        a, b = parse(before), parse(after)
        for name in names:
            keys = {key for key in a if key[0] == name}
            other = {key for key in b if key[0] == name}
            row = {'status': 'UNAVAILABLE_MISSING_SERIES', 'count_delta': None, 'sum_seconds_delta': None, 'mean_seconds': None}
            if keys and keys == other and {key[1] for key in keys} == {'sum', 'count'}:
                delta = {key: b[key] - a[key] for key in keys}
                if any(value < 0 for value in delta.values()):
                    row['status'] = 'UNAVAILABLE_COUNTER_RESET'
                else:
                    count = sum(value for key, value in delta.items() if key[1] == 'count')
                    total = sum(value for key, value in delta.items() if key[1] == 'sum')
                    row.update(status='AVAILABLE' if count > 0 else 'NO_REQUEST_OBSERVATIONS', count_delta=count,
                               sum_seconds_delta=total, mean_seconds=total / count if count > 0 else None)
            result['histograms'][name] = row
        result['status'] = 'AVAILABLE_PARTIAL_OR_COMPLETE_HISTOGRAMS' if any(row['status'] == 'AVAILABLE' for row in result['histograms'].values()) else 'UNAVAILABLE_NO_VALID_HISTOGRAM_DELTAS'
    except (OSError, ValueError):
        result['status'] = 'UNAVAILABLE_INVALID_SNAPSHOT'
    return result

def expected_trials(group):
    # Used only when a campaign plan was never written. Preserve the frozen plan's denominator.
    orders = [('mini', 'ovis'), ('ovis', 'mini'), ('mini', 'ovis')] if group['pairs'] == 3 else [
        ('mini', 'ovis'), ('ovis', 'mini'), ('ovis', 'mini'), ('mini', 'ovis'), ('mini', 'ovis'), ('ovis', 'mini')]
    return [{'trial_id': f"{group['name']}-p{i+1:02d}-{j+1}-{candidate}", 'pair': i+1, 'candidate': candidate}
            for i, order in enumerate(orders) for j, candidate in enumerate(order)]

def summarize(root, sequence_name, reporting):
    sequence_dir = root / 'evidence' / f'sequence-{sequence_name}'
    sequence_plan = read(sequence_dir / 'plan.json')
    if sequence_plan is None:
        raise ValueError('sequence plan missing: cannot establish the frozen planned denominator')
    sequence_state = read(sequence_dir / 'state.json', {})
    output = {'version': 'offline-campaign-summary-v1', 'sequence_name': sequence_name,
              'sequence_status': sequence_state.get('status', 'MISSING'), 'planned_trials': sequence_plan['paired_trial_count'],
              'quality_status': 'UNAVAILABLE_NO_INJECTED_QUALITY_ANNOTATION', 'groups': [], 'endurance': [],
              'scope': 'Profiles, timing scopes and concurrency settings remain separate; no pooled main comparison'}
    for group in sequence_plan['campaigns']:
        directory = root / 'evidence' / f"campaign-{group['name']}"
        plan = read(directory / 'plan.json', {})
        state = read(directory / 'state.json', {})
        planned = expected_trials(group)
        observed = {t['trial_id']: t for t in state.get('trials', [])}
        denominator = plan.get('fixed_denominator_per_trial', {'R0': 100, 'D0': 49, 'P0': 40}[group['timing_scope']])
        profile = plan.get('profile', 'C0-S0')
        report = dict(name=group['name'], profile=profile, timing_scope=group['timing_scope'],
                      page_admission=group['page_admission'], region_limit=group['region_limit'],
                      campaign_status=state.get('status', 'MISSING'), planned_trials=group['trials'],
                      fixed_denominator_per_trial=denominator, trials=[], pairs=[], candidates={},
                      source_scope='three fixed original documents only; no document-family generalization' if group['timing_scope'] == 'D0' else 'fixed selected inputs only')
        loaded = {}
        identity = {'page': set(), 'family': set(), 'pixel': set()}
        for trial in planned:
            trial_id = trial['trial_id']
            record = observed.get(trial_id, {})
            result_dir = root / 'results' / trial_id
            summary = read(result_dir / 'summary.json', {})
            row = dict(trial_id=trial_id, candidate=trial['candidate'], pair=trial['pair'], status=record.get('status', 'MISSING'),
                       expected_units=denominator, submitted_units=summary.get('submitted_pages'), terminal_units=summary.get('terminal_pages'),
                       complete_return_units=summary.get('pass_pages'), actual_batch_wall_seconds=summary.get('batch_wall_seconds'),
                       full_fixed_workload_wall_seconds=None,
                       load_to_api_ready_seconds=record.get('load_to_api_ready_seconds'), report_status='UNAVAILABLE', resources=None)
            row['API_histograms_including_warmup'] = api_histograms(directory / trial_id)
            events = reporting.read_lines(result_dir / 'events.jsonl')
            samples = reporting.read_lines(directory / trial_id / 'resources.jsonl')
            row['resources'] = resource_windows(reporting, samples, record, window(summary, events), summary.get('submitted_pages', 0))
            try:
                data = reporting.load_run(result_dir)
                loaded[trial_id] = data
                row['latency'] = data['overall']['latency']
                row['document_latency'] = data['documents']['latency']
                row['report_status'] = 'AVAILABLE'
                # Inspect only result metadata; never emit text, Markdown, blocks, prompts or request content.
                artifact_status = Counter()
                for page_id, item in data['input_evidence'].items():
                    identity['page'].add(page_id)
                    if item.get('source_family_id') not in (None, '', 'UNKNOWN'):
                        identity['family'].add(item['source_family_id'])
                    if item.get('pixel_hash'):
                        identity['pixel'].add(item['pixel_hash'])
                    artifact = read(result_dir / 'pages' / page_id / 'result.json', {})
                    artifact_status[artifact.get('status', 'MISSING')] += 1
                row['page_artifact_status_counts'] = dict(artifact_status)
                row['full_denominator_verified'] = (data['fixed_workload_integrity'] and summary.get('planned_pages') == denominator
                    and summary.get('submitted_pages') == denominator and summary.get('terminal_pages') == denominator
                    and sum(artifact_status.values()) == denominator and artifact_status.get('MISSING', 0) == 0
                    and (data['config'].get('profile') or data['config'].get('options', {}).get('profile')) == profile and data['timing_scope'] == group['timing_scope']
                    and data['config'].get('page_admission') == group['page_admission']
                    and data['config'].get('region_limit') == group['region_limit'])
            except (OSError, ValueError, KeyError, TypeError) as error:
                row['report_status'] = 'UNAVAILABLE_' + type(error).__name__
                row['full_denominator_verified'] = False
            wall = row['actual_batch_wall_seconds']
            row['full_fixed_workload_wall_seconds'] = wall if row['full_denominator_verified'] else None
            row['diagnostic_attempted_units_per_second'] = row['submitted_units'] / wall if positive(wall) and type(row['submitted_units']) is int else None
            row['diagnostic_completed_units_per_second'] = row['complete_return_units'] / wall if positive(wall) and type(row['complete_return_units']) is int else None
            report['trials'].append(row)
        # Never collapse missing/failed trials into a successful-only aggregate.
        for candidate in ('mini', 'ovis'):
            rows = [t for t in report['trials'] if t['candidate'] == candidate]
            complete = len(rows) == group['pairs'] and all(t['status'] == 'PASS' and t['full_denominator_verified'] and positive(t['full_fixed_workload_wall_seconds']) for t in rows)
            walls = sum(t['full_fixed_workload_wall_seconds'] for t in rows) if complete else None
            report['candidates'][candidate] = {'planned_trials': group['pairs'], 'status_counts': dict(Counter(t['status'] for t in rows)),
                'planned_unit_observations': denominator * group['pairs'], 'full_fixed_workload_wall_seconds': walls,
                'attempted_units_per_second': denominator * group['pairs'] / walls if walls else None,
                'completed_units_per_second': sum(t['complete_return_units'] for t in rows) / walls if walls else None,
                'aggregate_status': 'AVAILABLE_ALL_PLANNED_TRIALS' if complete else 'UNAVAILABLE_INCOMPLETE_OR_FAILED_PLANNED_TRIALS'}
        valid_pairs = []
        for number in range(1, group['pairs'] + 1):
            pair = [t for t in report['trials'] if t['pair'] == number]
            by_candidate = {t['candidate']: t for t in pair}
            a, b = by_candidate.get('mini', {}), by_candidate.get('ovis', {})
            aw, bw = a.get('full_fixed_workload_wall_seconds'), b.get('full_fixed_workload_wall_seconds')
            comparison = reporting.compare(loaded[a['trial_id']], loaded[b['trial_id']]) if a.get('trial_id') in loaded and b.get('trial_id') in loaded else {'status': 'NOT_COMPARABLE_MISSING_RUN'}
            comparison.pop('quality_winner', None)
            comparison.pop('formal_speed_winner', None)
            available = (len(pair) == 2 and all(t['status'] == 'PASS' and t['full_denominator_verified'] for t in pair)
                         and comparison['status'] == 'COMPARABLE_COMPLETE_SYSTEM_DESCRIPTIVE' and positive(aw) and positive(bw))
            report['pairs'].append({'pair': number, 'status': 'AVAILABLE' if available else 'NOT_COMPARABLE',
                                   'diagnostic_wall_ratio_mini_over_ovis': a['actual_batch_wall_seconds'] / b['actual_batch_wall_seconds'] if positive(a.get('actual_batch_wall_seconds')) and positive(b.get('actual_batch_wall_seconds')) else None,
                                   'comparison': comparison})
            if available:
                valid_pairs.append((aw, bw))
        all_pairs = len(valid_pairs) == group['pairs'] and len(report['trials']) == group['trials'] and state.get('status') == 'PASS'
        report['paired_wall_ratio_bootstrap'] = bootstrap(valid_pairs, reporting.quantile) if all_pairs else None
        report['formal_comparison_status'] = 'AVAILABLE_FIXED_INPUT_DESCRIPTIVE_ONLY' if all_pairs else 'UNAVAILABLE_FAILED_MISSING_OR_NOT_COMPARABLE_PAIR'
        report['unit_observations_planned_both_candidates'] = denominator * group['trials']
        report['unique_input_page_ids'] = len(identity['page'])
        report['unique_source_family_ids'] = len(identity['family'])
        report['unique_pixel_hashes'] = len(identity['pixel'])
        report['identity_coverage_status'] = 'COMPLETE' if len(loaded) == group['trials'] else 'PARTIAL_OBSERVED_ONLY'
        output['groups'].append(report)
    for step in sequence_plan['endurance']:
        record = next((r for r in sequence_state.get('steps', []) if r.get('name') == step['name']), {})
        directory = sequence_dir / step['name']
        if not record:
            record = read(directory / 'state.json', {})
        result_dir = root / 'results' / step['name']
        summary = read(result_dir / 'summary.json', {})
        source_state = read(result_dir.with_name(result_dir.name + '-state') / 'state.json', {})
        metadata = source_state.get('metadata', source_state)
        events = reporting.read_lines(result_dir / 'events.jsonl')
        samples = reporting.read_lines(directory / 'resources.jsonl')
        timed = window(summary, events)
        admitted = summary.get('submitted_pages', 0)
        keys = ('endurance_status', 'run_status', 'candidate_pool_pages', 'submitted_pages', 'terminal_pages', 'pass_pages',
                'not_admitted_pages', 'admission_window_seconds', 'admission_stop_reason', 'admission_elapsed_seconds',
                'drain_seconds', 'minimum_completed_pages', 'minimum_completed_pages_met', 'admitted_workload_drained', 'batch_wall_seconds')
        item = {'name': step['name'], 'candidate': step['candidate'], 'entry_state_status': source_state.get('status', 'MISSING'),
                'wrapper_status': record.get('status', 'MISSING'), 'primary_performance_eligible': False,
                'summary': {key: summary.get(key) for key in keys}, 'load_to_api_ready_seconds': record.get('load_to_api_ready_seconds'),
                'quality_samples_added_by_repetition': 0, 'unique_base_page_count': metadata.get('unique_base_page_count'),
                'resources': resource_windows(reporting, samples, record, timed, admitted), 'resource_segments_300s': [],
                'API_histograms_including_warmup': api_histograms(directory),
                'latency_admitted_terminals_only': reporting.latency([r.get('latency_seconds') for r in summary.get('results', [])]),
                'not_admitted_scope': 'candidate pool remainder; never failures and never a submitted denominator'}
        manifest = read(result_dir / 'input-manifest.json', {}).get('pages', [])
        admitted_ids = {r.get('page_id') for r in summary.get('results', [])}
        admitted_cases = [case for case in manifest if case.get('page_id') in admitted_ids]
        item['observed_unique_source_pages'] = len({case.get('source_id', case.get('page_id')) for case in admitted_cases})
        item['observed_unique_source_families'] = len({case['source_family_id'] for case in admitted_cases if case.get('source_family_id')})
        item['admitted_identity_coverage_status'] = 'COMPLETE' if len(admitted_cases) == admitted else 'PARTIAL_OBSERVED_ONLY'
        if timed:
            a = timed[0]
            while a < timed[1]:
                b = min(a + 300, timed[1])
                terminals = [r for r in summary.get('results', []) if isinstance(r.get('complete_monotonic'), (int, float)) and a <= r['complete_monotonic'] < b]
                item['resource_segments_300s'].append({'start': a, 'stop': b, 'terminal_pages_observed': len(terminals),
                    'resources': reporting.resources(samples, a, b, 0)})
                a = b
        output['endurance'].append(item)
    output['trial_records'] = sum(len(g['trials']) for g in output['groups'])
    output['all_planned_trials_retained'] = output['trial_records'] == output['planned_trials'] == 66
    return output

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--sequence-name', default='g3g4-e0-r1')
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--execution-path', type=Path, default=Path('/Users/luo/Documents/github/CodexGame/docs/minicpm-ocr-4090-plan-20261028/execution'))
    args = parser.parse_args(argv)
    sys.path.insert(0, str(args.execution_path))
    reporting = importlib.import_module('ocrbench.reporting')
    result = summarize(args.root, args.sequence_name, reporting)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
