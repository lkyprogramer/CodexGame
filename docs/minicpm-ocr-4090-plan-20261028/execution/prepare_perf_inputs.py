#!/usr/bin/env python3
"""Prepare offline, paired D0/P0/R0 performance inputs from existing frozen assets."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path

import fitz
import PIL

from ocrbench.core import _decode_page, load_manifest


TEXT_QUOTAS = {'handwrite': 30, 'name': 20, 'printed_pdf': 25, 'icdar': 15}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def ordered(pages: list[dict]) -> list[dict]:
    # The executor assembles consecutive documents: preserve that boundary in every manifest.
    return sorted(pages, key=lambda p: (p['document_id'], p.get('page_index', 0), p['page_id']))


def read_manifest(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    raw = data if isinstance(data, list) else data['pages']
    clean = {p['page_id']: p for p in load_manifest(path)}
    # Keep frozen provenance fields; use the runner's validated/resolved source path.
    return [{**p, 'path': clean[p['page_id']]['path']} for p in raw]


def decode(case: dict):
    image, transform = _decode_page(case)
    digest = hashlib.sha256(image.tobytes()).hexdigest()
    if case.get('expected_pixel_hash') and digest != case['expected_pixel_hash']:
        raise ValueError(f'INPUT_PIXEL_HASH_MISMATCH:{case["page_id"]}')
    return image, digest, transform


def materialize(pages: list[dict], destination: Path, split: str | None, require_expected: bool) -> list[dict]:
    destination.mkdir()
    result = []
    for case in ordered(pages):
        if require_expected and not case.get('expected_pixel_hash'):
            raise ValueError(f'MISSING_FROZEN_PIXEL_HASH:{case["page_id"]}')
        source = Path(case['path'])
        source_hash = sha(source)
        if case.get('source_asset_sha256') and case['source_asset_sha256'] != source_hash:
            raise ValueError(f'SOURCE_ASSET_HASH_MISMATCH:{case["page_id"]}')
        image, digest, transform = decode(case)
        target = destination / (case['page_id'] + '.png')
        image.save(target, format='PNG')
        entry = {**case, 'path': str(target.resolve()), 'kind': 'image',
                 'expected_pixel_hash': digest, 'rgb_dimensions': list(image.size),
                 'prepared_png_sha256': sha(target),
                 'input_lineage': {'page_id': case['page_id'], 'document_id': case['document_id'],
                                   'source_family_id': case.get('source_family_id'),
                                   'path': str(source.resolve()), 'kind': case['kind'],
                                   'page_index': case.get('page_index'), 'source_sha256': source_hash,
                                   'frozen_expected_pixel_hash': case.get('expected_pixel_hash'),
                                   'actual_input_pixel_hash': digest, 'orientation_transform': transform}}
        if split is not None:
            entry['split'] = split
        # A PDF source hash refers to lineage, not to the newly saved PNG asset.
        entry.pop('source_asset_sha256', None)
        result.append(entry)
    return result


def choose_regions(pages: list[dict]) -> tuple[list[dict], list[dict]]:
    selected, seen = [], set()
    for tag, quota in TEXT_QUOTAS.items():
        candidates = ordered([p for p in pages if p.get('task') == 'text' and tag in p.get('scene_tags', [])])
        count = 0
        for case in candidates:
            digest = case.get('expected_pixel_hash')
            if not digest:
                raise ValueError(f'MISSING_REGION_PIXEL_HASH:{case["page_id"]}')
            if digest in seen:
                continue
            selected.append(case)
            seen.add(digest)
            count += 1
            if count == quota:
                break
        if count != quota:
            raise ValueError(f'INSUFFICIENT_REGION_CATEGORY:{tag}:{count}/{quota}')
    for task, quota in [('formula', 6), ('seal', 2), ('table', 2)]:
        candidates = ordered([p for p in pages if p.get('task') == task])
        if len(candidates) != quota:
            raise ValueError(f'EXPECTED_FIXED_REGION_COUNT:{task}:{len(candidates)}/{quota}')
        for case in candidates:
            digest = case.get('expected_pixel_hash')
            if not digest or digest in seen:
                raise ValueError(f'MISSING_OR_DUPLICATE_REGION_PIXELS:{case["page_id"]}')
            selected.append(case)
            seen.add(digest)
    selected_ids = {p['page_id'] for p in selected}
    warmups = []
    for tag in TEXT_QUOTAS:
        remaining = ordered([p for p in pages if p.get('task') == 'text'
                             and tag in p.get('scene_tags', []) and p['page_id'] not in selected_ids
                             and p.get('expected_pixel_hash') not in seen])
        if not remaining:
            raise ValueError(f'NO_DISTINCT_REGION_WARMUP:{tag}')
        case = remaining[0]
        if not case.get('expected_pixel_hash'):
            raise ValueError(f'MISSING_REGION_PIXEL_HASH:{case["page_id"]}')
        warmups.append({**case, 'split': 'development'})
        seen.add(case['expected_pixel_hash'])
    if len(selected) != 100 or len(warmups) != 4:
        raise ValueError('WRONG_FIXED_REGION_SELECTION_SIZE')
    return ordered(selected), ordered(warmups)


def prepare(root: Path, out: Path, region_manifest: Path) -> dict:
    perf_manifest = root / 'corpus-extra/perf40/manifest.json'
    dev_manifest = root / 'corpus/development-manifest.json'
    main_manifest = root / 'corpus/manifest.json'
    formal, dev, main, regions = [read_manifest(p) for p in
                                [perf_manifest, dev_manifest, main_manifest, region_manifest]]
    if len(formal) != 40 or len(dev) != 4:
        raise ValueError(f'EXPECTED_FORMAL40_DEV4:{len(formal)}:{len(dev)}')
    complete = ordered([p for p in main if p['document_id'] in {'PDF-001', 'PDF-002', 'PDF-003'}])
    if len(complete) != 49:
        raise ValueError(f'EXPECTED_COMPLETE3_49_PAGES:{len(complete)}')
    for docid in ['PDF-001', 'PDF-002', 'PDF-003']:
        group = [p for p in complete if p['document_id'] == docid]
        if not group or any(p['kind'] != 'pdf' for p in group) or len({p['path'] for p in group}) != 1:
            raise ValueError(f'INVALID_NATIVE_PDF_GROUP:{docid}')
        with fitz.open(group[0]['path']) as document:
            if [p['page_index'] for p in group] != list(range(len(document))):
                raise ValueError(f'INCOMPLETE_NATIVE_PDF:{docid}')
        source_hash = sha(Path(group[0]['path']))
        for case in group:
            previous_expected = case.get('expected_pixel_hash')
            image, digest, transform = decode(case)
            case['expected_pixel_hash'] = digest
            case['rgb_dimensions'] = list(image.size)
            case['d0_input_identity'] = {'page_id': case['page_id'], 'document_id': case['document_id'],
                                          'source_family_id': case.get('source_family_id'),
                                          'path': case['path'], 'kind': 'pdf', 'page_index': case['page_index'],
                                          'source_sha256': source_hash,
                                          'previous_expected_pixel_hash': previous_expected}
            case['d0_preparation_audit'] = {'decoder': 'ocrbench.core._decode_page',
                                            'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz,
                                            'orientation_transform': transform, 'color_mode': 'RGB',
                                            'alpha': False, 'actual_input_pixel_hash': digest,
                                            'raster_retained': False}
            del image  # D0 keeps the original PDF entry; this audit does not materialize P0 pixels.
    mixed, warmups = choose_regions(regions)
    out.mkdir(parents=True, exist_ok=False)
    os.chmod(out, 0o700)
    p0_formal = materialize(formal, out / 'p0-formal40', None, True)
    p0_dev = materialize(dev, out / 'p0-dev4', 'development', False)
    if {p['expected_pixel_hash'] for p in p0_formal} & {p['expected_pixel_hash'] for p in p0_dev}:
        raise ValueError('P0_DEVELOPMENT_FORMAL_PIXEL_OVERLAP')
    r0_mixed = materialize(mixed, out / 'r0-mixed100', None, True)
    r0_warmup = materialize(warmups, out / 'r0-warmup4', 'development', True)
    for case in r0_mixed + r0_warmup:
        if 'name' in case.get('scene_tags', []):
            case['derived_task_policy'] = {'source_task': case['task'], 'source_region_task': case.get('region_task'),
                                           'source_output_task_cap': case.get('output_task_cap'),
                                           'reason': 'name crop uses official Text task with short-field token cap'}
            case.update(task='name', region_task='name', output_task_cap=2048)
    formal_pixels = {p['expected_pixel_hash'] for p in r0_mixed}
    warmup_pixels = {p['expected_pixel_hash'] for p in r0_warmup}
    if len(formal_pixels) != 100 or len(warmup_pixels) != 4 or formal_pixels & warmup_pixels:
        raise ValueError('R0_WARMUP_FORMAL_RGB_DUPLICATE')
    manifests = {'p0-formal40-manifest.json': ('P0', p0_formal),
                 'p0-dev4-manifest.json': ('P0', p0_dev),
                 'd0-complete3-49-manifest.json': ('D0', complete),
                 'r0-mixed100-manifest.json': ('R0', r0_mixed),
                 'r0-warmup4-manifest.json': ('R0', r0_warmup)}
    for name, (scope, pages) in manifests.items():
        write(out / name, {'profile_id': name.removesuffix('-manifest.json'), 'timing_scope': scope,
                          'reference_status': 'NO_GT_CREATED_PERFORMANCE_INPUTS_ONLY', 'pages': pages})
        # Validate persisted runner contracts and assert each document occupies one consecutive run.
        persisted = load_manifest(out / name)
        groups = []
        for page in persisted:
            if not groups or groups[-1] != page['document_id']:
                groups.append(page['document_id'])
        if len(groups) != len(set(groups)):
            raise ValueError(f'NONCONTIGUOUS_DOCUMENT:{name}')
        if scope != 'D0' and any(p['kind'] != 'image' for p in persisted):
            raise ValueError(f'NON_IMAGE_PIXEL_INPUT:{name}')
    profile = {'status': 'COMPLETE_INPUT_PREPARATION_NOT_MODEL_ACCEPTANCE',
               'versions': {'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz, 'pillow': PIL.__version__},
               'generator_sha256': sha(Path(__file__)),
               'input_manifests': {str(p.resolve()): sha(p) for p in
                                   [perf_manifest, dev_manifest, main_manifest, region_manifest]},
               'output_manifests': {name: {'sha256': sha(out / name), 'timing_scope': scope, 'count': len(pages)}
                                    for name, (scope, pages) in manifests.items()},
               'r0_task_counts': dict(Counter(p['task'] for p in r0_mixed)),
               'r0_text_quotas': TEXT_QUOTAS,
               'r0_derived_task_policy': {'selection': 'unchanged source task=text and scene_tags=name',
                                          'name_formal_count': 20, 'name_warmup_count': 1,
                                          'output_task': 'name', 'output_region_task': 'name',
                                          'model_native_task': 'Text Recognition', 'output_task_cap': 2048,
                                          'source_manifest_modified': False},
               'r0_selection': 'per category ordered by document_id/page_index/page_id; first unique frozen RGB hashes',
               'r0_warmup': 'first remaining unique text crop from each category; development; disjoint RGB hashes',
               'documents_contiguous': True, 'D0_P0_separate': True,
               'D0_original_assets_moved': False, 'GT_created': False,
               'D0_preparation_audit': {'pages': len(complete), 'decoder': 'ocrbench.core._decode_page',
                                         'dpi': 300, 'colorspace': 'RGB', 'alpha': False,
                                         'existing_expected_hash_policy': 'strict_verify_fail_on_mismatch',
                                         'raster_retained': False, 'formal_D0_must_rerender_PDF': True,
                                         'source_storage_page_cache_preaccessed': True},
               'notes': ['P0/R0 decode and PNG creation occur before measured runs',
                         'P0 records original D0 page identity and validates perf40 frozen pixel hashes',
                         'D0 retains original PDF paths and all native page indices, without PNG substitution',
                         'D0 preparation audited 49 RGB hashes and discarded rasters; formal D0 renders PDF again',
                         'PDF source storage/page cache was preaccessed during preparation; no cold-cache claim',
                         'P0 development inputs have actual hashes but no claim of preexisting expected hashes',
                         'R0 crops retain existing family, original ids/bboxes and task; no inferred golden references']}
    write(out / 'profile.json', profile)
    return profile


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--r0-manifest', type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    root = args.root.resolve()
    out = (args.out or root / 'corpus-extra/perf-prepared').resolve()
    region_manifest = (args.r0_manifest or root / 'corpus-extra/r0-300/manifest.json').resolve()
    result = prepare(root, out, region_manifest)
    print(json.dumps({'out': str(out), 'status': result['status'], 'manifests': result['output_manifests']}))
