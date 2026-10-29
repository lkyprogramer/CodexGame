"""Whole-round gather-probe statistics; micro results cannot satisfy the gate."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics

spec = importlib.util.spec_from_file_location('prior_gu_analysis', Path(__file__).parents[1] / 'gu_probe/analyze.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
paired_stats = prior.paired_stats


def load(path):
    return json.loads(path.read_text())


def analyze(task):
    task = Path(task)
    arms = {}
    for round_id in range(6):
        for mode in ('off', 'on'):
            folder = task / 'bench' / f'r{round_id}-{mode}'
            result = load(folder / 'result.json')
            if result['mode'] != mode or result['workers'] != 15 or result['seconds'] < 60 or result['sweeps'] <= 0:
                raise ValueError('ARM_IDENTITY_OR_COMPLETENESS')
            if (mode == 'on') != (result['candidate_row_calls'] > 0):
                raise ValueError('CANDIDATE_HIT_EVIDENCE')
            if load(folder / 'completion.json')['state'] != 'COMPLETE':
                raise ValueError('ARM_PROTECTION_OR_COMPLETION')
            resources = load(folder / 'resources.json')
            if not resources or any(s['MemAvailable_mib'] < 4096 or float(s['gpu']['temperature_c']) >= 85 or s['gpu']['compute_processes'] for s in resources):
                raise ValueError('RESOURCE_GATE')
            arms[f'r{round_id}-{mode}'] = {'result': result, 'frequency': prior.frequency(folder, result),
                                         'memory': prior.memory(folder, result), 'resource_samples': len(resources)}
    hashes = {arm['result']['output_hash'] for arm in arms.values()}
    if len(hashes) != 1:
        raise ValueError('PAIRED_OUTPUT_HASH_MISMATCH')
    metrics = {}
    for metric in ('ns_per_sweep', 'gu_ns_per_sweep', 'quant_ns_per_sweep', 'down_ns_per_sweep', 'p95_sweep_ns'):
        ratios = [arms[f'r{r}-on']['result'][metric] / arms[f'r{r}-off']['result'][metric] for r in range(6)]
        metrics[metric] = dict(paired_stats(ratios), paired_ratios=ratios,
                              mean_off=statistics.mean(arms[f'r{r}-off']['result'][metric] for r in range(6)),
                              mean_on=statistics.mean(arms[f'r{r}-on']['result'][metric] for r in range(6)))
    micro = {'state': 'NOT_RUN', 'gate': False}
    if (task / 'micro').exists():
        ratios = []
        for round_id in range(3):
            off = load(task / 'micro' / f'r{round_id}-off/result.json')
            on = load(task / 'micro' / f'r{round_id}-on/result.json')
            if off['output_hash'] != on['output_hash']:
                raise ValueError('MICRO_OUTPUT_HASH')
            ratios.append(on['ns_per_call'] / off['ns_per_call'])
        micro = {'state': 'COMPLETE', 'gate': False, 'statistics': paired_stats(ratios)}
    passed = metrics['ns_per_sweep']['expansion_gate']
    report = {'state': 'COMPLETE', 'scope': 'single-format captured complete ExpertPool replay; request and task-quality gates remain separate',
              'expansion_gate': 'PASS' if passed else 'NOT_MET', 'whole_machine_allowed': passed,
              'metrics': metrics, 'arms': arms, 'output_hash': next(iter(hashes)), 'micro_diagnostic': micro,
              'original_six_status': 'FAIL_UNCHANGED', 'scoring_changed': False}
    (task / 'ANALYSIS.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('task')
    report = analyze(parser.parse_args().task)
    print(json.dumps({'state': report['state'], 'expansion_gate': report['expansion_gate'],
                      'complete_expert': report['metrics']['ns_per_sweep'], 'micro': report['micro_diagnostic']}, indent=2))
