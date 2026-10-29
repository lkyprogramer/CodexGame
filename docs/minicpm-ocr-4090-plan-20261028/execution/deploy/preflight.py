"""Capture bounded host evidence without changing existing services."""
import datetime
import json
import pathlib
import subprocess

commands = {
    'identity': ['id'],
    'os': ['uname', '-a'],
    'gpu': ['nvidia-smi', '--query-gpu=name,driver_version,memory.total,memory.used,memory.free,temperature.gpu,power.limit', '--format=csv'],
    'gpu_processes': ['nvidia-smi', '--query-compute-apps=pid,process_name,used_memory', '--format=csv'],
    'memory': ['free', '-b'],
    'disk': ['df', '-B1', '/data/ocr'],
    'cpu': ['lscpu'],
    'containers': ['docker', 'ps', '--format', '{{.Names}} {{.Status}}'],
    'base_image': ['docker', 'image', 'inspect', 'nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04', '--format', '{{.Id}} {{json .RepoDigests}}'],
    'ports': ['ss', '-ltn'],
    'historical_units': ['systemctl', 'is-active', 'qwen3-235b.service', 'ninfer.service'],
}
result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
for name, command in commands.items():
    run = subprocess.run(command, capture_output=True, text=True, timeout=30)
    result[name] = {'command': command, 'exit_code': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr}
output = pathlib.Path('/data/ocr/dual-ocr-20261028/evidence') / ('preflight-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '.json')
output.write_text(json.dumps(result, indent=2))
print(output)
