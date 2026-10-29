"""Run an explicitly supplied deployment command with durable terminal status."""
import argparse
import datetime
import json
import pathlib
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=pathlib.Path, required=True)
parser.add_argument('--name', required=True)
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
command = args.command[1:] if args.command[:1] == ['--'] else args.command
if not command or not args.name.replace('-', '').replace('_', '').isalnum():
    raise SystemExit('A command and safe job name are required')
status = args.root/'evidence'/f'{args.name}-job.json'
log = args.root/'logs'/f'{args.name}.log'
if status.exists() or log.exists():
    raise SystemExit('Use a fresh job name; existing evidence is preserved')
started = time.monotonic()
record = {'name': args.name, 'command': command, 'utc_start': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'status': 'RUNNING'}
status.write_text(json.dumps(record, indent=2))
with log.open('xb') as output:
    exit_code = subprocess.call(command, stdout=output, stderr=subprocess.STDOUT)
record.update(exit_code=exit_code, status='PASS' if exit_code == 0 else 'FAIL', wall_seconds=time.monotonic()-started,
              utc_end=datetime.datetime.now(datetime.timezone.utc).isoformat())
temporary = status.with_suffix('.tmp')
temporary.write_text(json.dumps(record, indent=2))
temporary.replace(status)
raise SystemExit(exit_code)
