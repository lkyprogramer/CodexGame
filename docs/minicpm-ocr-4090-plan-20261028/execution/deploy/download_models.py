"""Download ModelScope snapshots, admitting files only after SHA-256 checks."""
import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import time
import urllib.parse
import urllib.request


def read_url(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def download(repo, destination, expected, evidence):
    start = time.monotonic()
    metadata_url = f'https://modelscope.cn/api/v1/models/{repo}/repo/files?Revision=master&Recursive=true'
    metadata = json.loads(read_url(metadata_url))
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / (destination.name + '-modelscope-metadata.json')).write_text(json.dumps(metadata, indent=2))
    files = [f for f in metadata['Data']['Files'] if f.get('Type') == 'blob']
    paths = {f['Path'] for f in files}
    if not set(expected).issubset(paths):
        raise RuntimeError(f'Missing required files: {set(expected)-paths}')
    for item in files:
        if item['Path'] in expected and item['Sha256'] != expected[item['Path']]:
            raise RuntimeError(f'Upstream drift: {repo}/{item["Path"]}')
    destination.mkdir(parents=True, exist_ok=True)

    def transfer(item):
        relative = pathlib.PurePosixPath(item['Path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid repository path')
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        digest = item['Sha256']
        if target.exists() and hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() == digest:
            return {'path': str(relative), 'sha256': digest, 'bytes': target.stat().st_size, 'cached': True}
        url = f'https://modelscope.cn/models/{repo}/resolve/master/{urllib.parse.quote(str(relative))}'
        temporary = target.with_name(target.name + '.partial')
        for attempt in range(2):
            try:
                with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
                    while chunk := response.read(4 * 1024 * 1024):
                        output.write(chunk)
                actual = hashlib.file_digest(temporary.open('rb'), 'sha256').hexdigest()
                if actual != digest:
                    raise RuntimeError(f'SHA mismatch for {relative}: {actual}')
                temporary.replace(target)
                print(json.dumps({'repo': repo, 'file': str(relative), 'bytes': target.stat().st_size, 'verified': True}), flush=True)
                return {'path': str(relative), 'sha256': digest, 'bytes': target.stat().st_size, 'cached': False}
            except Exception:
                if attempt:
                    raise
                time.sleep(2)
        raise AssertionError('unreachable')

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        result = list(pool.map(transfer, files))
    report = {'repository': repo, 'files': result, 'elapsed_seconds': time.monotonic()-start, 'status': 'VERIFIED'}
    (evidence / (destination.name + '-download.json')).write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--locks', type=pathlib.Path, required=True)
    parser.add_argument('--candidate', choices=['mini', 'ovis', 'dspark'], required=True)
    args = parser.parse_args()
    if args.candidate == 'mini':
        lock = json.loads((args.locks / 'source-lock.json').read_text())
        download('OpenBMB/MiniCPM-OCR-1.0', args.root/'models/MiniCPM-OCR-1.0', lock['main_model']['files_sha256'], args.root/'evidence')
    elif args.candidate == 'ovis':
        lock = json.loads((args.locks / 'ovis-source-lock.json').read_text())
        expected = {f['path']: f['modelscope_sha256'] for f in lock['files']}
        download('ATH-MaaS/OvisOCR3', args.root/'models/OvisOCR3', expected, args.root/'evidence')
    else:
        lock = json.loads((args.locks / 'dspark-source-lock.json').read_text())
        expected = {f['path']: f['sha256'] for f in lock['modelscope']['files']}
        download(lock['modelscope']['repository'], args.root/'models/MiniCPM-OCR-1.0-DSpark', expected, args.root/'evidence')
