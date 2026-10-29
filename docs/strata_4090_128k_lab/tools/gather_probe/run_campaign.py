"""Execute the fixed paired order after one interactive root authentication."""
import argparse
import json
import os
import signal
import subprocess
from types import SimpleNamespace

import root_perf

TASK = root_perf.TASK
ORDERS = (('off', 'on'), ('on', 'off'), ('on', 'off'), ('off', 'on'), ('off', 'on'), ('on', 'off'))


def mkdir_owned(path):
    subprocess.run(['runuser', '-u', 'hhtele', '--', 'mkdir', '--', str(path)], check=True)


def run(scope):
    if os.geteuid() != 0:
        raise RuntimeError('ROOT_REQUIRED_FOR_CAMPAIGN_MSR_READ')
    if scope not in ('bench', 'micro'):
        raise ValueError('CAMPAIGN_SCOPE')
    parent = TASK / scope
    mkdir_owned(parent)
    completed = []
    try:
        for round_id, order in enumerate(ORDERS[:3] if scope == 'micro' else ORDERS):
            for mode in order:
                out = parent / f'r{round_id}-{mode}'
                mkdir_owned(out)
                args = SimpleNamespace(out=str(out), scope='row-bench' if scope == 'micro' else 'bench',
                                       mode=mode, warm=2 if scope == 'micro' else 30,
                                       seconds=10 if scope == 'micro' else 60)
                code = root_perf.run(args)
                if code:
                    raise RuntimeError(f'ARM_FAILED round={round_id} mode={mode} exit={code}')
                completed.append({'round': round_id, 'mode': mode, 'folder': str(out), 'exit_code': code})
                (parent / 'progress.json').write_text(json.dumps(completed, indent=2) + '\n')
                print(json.dumps(completed[-1]), flush=True)
    except BaseException as exc:
        (parent / 'FAILURE.json').write_text(json.dumps({'error': str(exc) or type(exc).__name__, 'completed': completed}, indent=2) + '\n')
        raise
    (parent / 'COMPLETE.json').write_text(json.dumps({'state': 'COMPLETE', 'arms': completed}, indent=2) + '\n')
    return completed


def terminated(*_):
    raise KeyboardInterrupt('CAMPAIGN_TERMINATED')


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminated)
    parser = argparse.ArgumentParser()
    parser.add_argument('scope', choices=['bench', 'micro'])
    run(parser.parse_args().scope)
