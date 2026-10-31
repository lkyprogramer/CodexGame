"""Conditional critical-path headroom, never a measured performance pass."""
from common import input_cli, number, require


def union(intervals, window):
    require(isinstance(intervals, list), 'Intervals must be a list')
    checked = []
    for interval in intervals:
        require(isinstance(interval, list) and len(interval) == 2, 'Interval must be [start_ms, end_ms]')
        start, end = [number(x, 'interval endpoint') for x in interval]
        require(start < end <= window, 'Interval must satisfy 0 <= start < end <= window_ms')
        checked.append([start, end])
    merged = []
    for start, end in sorted(checked):
        if merged and start <= merged[-1][1]: merged[-1][1] = max(end, merged[-1][1])
        else: merged.append([start, end])
    return merged


def evaluate(data):
    require(isinstance(data, dict) and type(data.get('schema_version')) is int and data['schema_version'] == 1 and type(data.get('synthetic')) is bool, 'integer schema_version=1 and boolean synthetic required')
    window = number(data['window_ms'], 'window_ms', positive=True)
    speedup = number(data['measured_kernel_speedup'], 'measured_kernel_speedup', positive=True)
    overhead = number(data['added_overhead_ms'], 'added_overhead_ms')
    require(type(data['dependency_verified']) is bool, 'dependency_verified must be boolean')
    merged = union(data['critical_exposed_intervals'], window)
    unknown = union(data['unknown_intervals'], window)
    exposed = sum(end - start for start, end in merged); fraction = exposed / window
    optimistic = 1 - fraction
    realistic = 1 - fraction + fraction / speedup + overhead / window
    status = 'RESEARCH_RESULT_ONLY'
    if fraction < 0.04 or 1 - realistic < 0.04: status = 'NO_QUALIFIED_CANDIDATE'
    if not data['dependency_verified'] or unknown: status = 'INSUFFICIENT'
    def bound(ratio):
        return {'time_ratio': ratio, 'time_improvement': 1 - ratio,
                'speedup': None if ratio == 0 else 1 / ratio}
    return {'status': status, 'synthetic': data['synthetic'], 'merged_intervals': merged,
            'exposed_ms': exposed, 'exposed_fraction': fraction, 'unknown_intervals': unknown,
            'optimistic': bound(optimistic), 'realistic': bound(realistic), 'conditional_only': True,
            'dependency_verified': data['dependency_verified'], 'preferred_fraction_0_08_met': fraction >= 0.08,
            'performance': 'NOT_EVALUATED', 'quality': 'NOT_EVALUATED', 'deployment_approved': False,
            'limitations': ['Manual causal review is declared, not proven by this calculator.',
                            'Constant other work, removable exposed cost and stated overhead are assumptions.']}


if __name__ == '__main__':
    raise SystemExit(input_cli(evaluate, __doc__))
