"""Verify every regular package file against a SHA256 manifest before ZIP creation."""
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
from common import guarded, require


def verify(root, manifest):
    root = Path(root).resolve(); manifest = Path(manifest).resolve()
    require(root.is_dir() and manifest.is_relative_to(root), 'Manifest must be inside package root')
    files = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Symlink is not a reproducible package file: ' + str(path))
        if path.is_file() and path.resolve() != manifest: files.add(path.relative_to(root).as_posix())
    entries = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([0-9a-fA-F]{64})  (.+)', line)
        require(match is not None, 'Malformed manifest line')
        digest, name = match.groups(); relative = PurePosixPath(name)
        require(not relative.is_absolute() and '..' not in relative.parts and '\\' not in name and relative.as_posix() == name, 'Unsafe manifest path')
        require(name not in entries, 'Duplicate manifest path'); entries[name] = digest.lower()
    require(set(entries) == files, 'Manifest file-set mismatch: missing=%r extra=%r' % (sorted(files - set(entries)), sorted(set(entries) - files)))
    for name, expected in entries.items():
        digest = hashlib.sha256()
        with (root / name).open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
        require(digest.hexdigest() == expected, 'SHA256 mismatch: ' + name)
    return {'status': 'MANIFEST_VALID', 'files_verified': len(entries), 'deployment_approved': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path); parser.add_argument('--output', type=Path)
    args = parser.parse_args(); raise SystemExit(guarded(lambda: verify(args.root, args.manifest), args.output))
