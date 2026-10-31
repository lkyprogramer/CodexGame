"""Offline JSON/I/O helpers. No existing output file is ever overwritten."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def require(ok, message):
    if not ok: raise ValueError(message)


def number(value, name, minimum=0, positive=False):
    require(type(value) in (int, float) and math.isfinite(value), name + ': finite number required')
    require(value > minimum if positive else value >= minimum, name + ': outside allowed range')
    return value


def load(path):
    def pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, 'Duplicate JSON key: ' + key); obj[key] = value
        return obj
    def finite(text):
        value = float(text); require(math.isfinite(value), 'Nonfinite JSON number'); return value
    def constant(text): raise ValueError('Invalid JSON constant: ' + text)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_float=finite, parse_constant=constant)


def emit(result, output=None):
    text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    if output:
        with Path(output).open('x', encoding='utf-8') as stream: stream.write(text)
    else: print(text, end='')


def guarded(action, output=None):
    try:
        result = action(); emit(result, output)
        return 1 if result['status'] in {'INSUFFICIENT', 'NO_QUALIFIED_CANDIDATE', 'PERFORMANCE_GATE_NOT_MET'} else 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError) as error:
        emit({'status': 'INVALID_INPUT_OR_EXPERIMENT', 'error': str(error), 'inference': None,
              'deployment_approved': False, 'quality': 'NOT_EVALUATED'})
        return 2


def input_cli(evaluate, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, help='New output file; default stdout; never overwrite')
    args = parser.parse_args()
    def action():
        data = load(args.input); result = evaluate(data)
        result['input_sha256'] = hashlib.sha256(args.input.read_bytes()).hexdigest()
        return result
    return guarded(action, args.output)
