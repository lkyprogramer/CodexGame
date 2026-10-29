"""Restore the exact CUDA dependency Git objects without network access."""
import hashlib
import json
import pathlib
import subprocess

archives = pathlib.Path('/work/releases/cmake-archives')
manifest = json.loads((archives/'cmake-dependency-transfer-manifest.json').read_text())
destination = pathlib.Path('/work/releases/cmake-src')
destination.mkdir(exist_ok=False)
verified = []
for item in manifest['repositories']:
    archive = archives/pathlib.Path(item['archive']).name
    assert archive.stat().st_size == item['archive_bytes']
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['archive_sha256']
    subprocess.run(['tar', '--no-same-owner', '-xzf', str(archive), '-C', str(destination)], check=True)
    repo = destination/item['name']
    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == item['actual_head']
    subprocess.run(['git', '-C', str(repo), 'checkout', '--force', 'HEAD'], check=True)
    for module in item['required_cuda_submodules_prepared']:
        path = module['path'] if isinstance(module, dict) else module
        subprocess.run(['git', '-C', str(repo), '-c', 'protocol.allow=never',
                        'submodule', 'update', '--init', '--checkout', '--no-fetch', '--', path], check=True)
    subprocess.run(['git', '-C', str(repo), 'fsck', '--connectivity-only', '--no-reflogs'], check=True)
    verified.append({'name': item['name'], 'head': head, 'archive_sha256': item['archive_sha256'],
                     'official_override_env': item['override_env'],
                     'required_submodules': item['required_cuda_submodules_prepared']})
pathlib.Path('/work/evidence/prepared-cmake-sources.json').write_text(json.dumps(verified, indent=2))
print(json.dumps(verified))
