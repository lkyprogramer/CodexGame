"""Verify locally fetched Git archives before placing the locked source trees."""
import hashlib
import json
import pathlib
import shutil
import subprocess

root = pathlib.Path('/work')
manifest = json.loads((root/'releases/transfer-manifest.json').read_text())
expected = {'minicpm-ocr': '62d5e649c32be2271f2c8c66ec8307f3d7373903',
            'vllm': '18343393b4da41a7e8027efbc4c7e77c28301bf0',
            'transformers': '549e5b410733fb50e8efbbe4aa585cb89f6478ea'}
for item in manifest['repositories']:
    assert item['commit'] == expected[item['repository']]
    archive = root/'releases'/pathlib.Path(item['archive']).name
    assert archive.stat().st_size == item['archive_bytes']
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['archive_sha256']
main = pathlib.Path('/opt/minicpm-ocr')
if (main/'.git').exists():
    # The first failed fetch is task-owned and remains available for diagnosis.
    saved = root/'evidence/failed-github-fetch-r1'
    saved.mkdir()
    shutil.move(str(main/'.git'), str(saved/'.git'))
result = []
for item in manifest['repositories']:
    name = item['repository']
    target = main if name == 'minicpm-ocr' else main/'sources'/name
    target.mkdir(parents=True, exist_ok=True)
    if name != 'minicpm-ocr' and any(target.iterdir()):
        raise RuntimeError(f'Existing source checkout is preserved: {target}')
    archive = root/'releases'/pathlib.Path(item['archive']).name
    subprocess.run(['tar', '--no-same-owner', '-xzf', str(archive), '--strip-components=1', '-C', str(target)], check=True)
    head = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    assert head == item['commit']
    subprocess.run(['git', '-C', str(target), 'fsck', '--connectivity-only', '--no-reflogs'], check=True)
    result.append({'repository': name, 'path': str(target), 'commit': head, 'archive_sha256': item['archive_sha256']})
(root/'evidence/prepared-git-sources.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
