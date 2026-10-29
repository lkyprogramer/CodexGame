"""Read effective service argv and Docker limits for a task-owned candidate."""
import argparse
import json
import pathlib
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--container', required=True)
parser.add_argument('--out', type=pathlib.Path, required=True)
args = parser.parse_args()
container = json.loads(subprocess.check_output(['docker', 'inspect', args.container]))[0]
argv = subprocess.check_output(['docker', 'exec', args.container, 'cat', '/proc/1/cmdline']).decode().strip('\0').split('\0')


def option(name):
    return argv[argv.index(name)+1]


limits = container['HostConfig']
policy = {'dtype': option('--dtype'), 'max_model_len': int(option('--max-model-len')),
          'gpu_memory_utilization': float(option('--gpu-memory-utilization')),
          'max_num_seqs': int(option('--max-num-seqs')),
          'max_num_batched_tokens': int(option('--max-num-batched-tokens')),
          'cpu_cores': limits['NanoCpus']/1e9, 'ram_gib': limits['Memory']/(1024**3)}
assert policy == {'dtype': 'bfloat16', 'max_model_len': 16384, 'gpu_memory_utilization': .65,
                  'max_num_seqs': 4, 'max_num_batched_tokens': 8192, 'cpu_cores': 8, 'ram_gib': 32}, policy
assert '--no-enable-prefix-caching' in argv and float(option('--mm-processor-cache-gb')) == 0
args.out.write_text(json.dumps({'policy': policy, 'container': args.container,
                               'container_id': container['Id'], 'image_id': container['Image'],
                               'cpuset': limits['CpusetCpus'], 'argv': argv}, indent=2))
print(json.dumps(policy))
