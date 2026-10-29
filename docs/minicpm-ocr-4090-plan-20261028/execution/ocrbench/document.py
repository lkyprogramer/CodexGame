"""Deterministic document assembly. Raw page outputs remain unchanged."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path, PurePosixPath

from .client import atomic_json


def _atomic_text(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(value, encoding='utf-8')
    temporary.replace(path)


def assemble_document(document_id: str, cases: list[dict], run_out: Path,
                      deadline: float) -> dict:
    """Assemble the exact frozen selected units, including failed page records.

    A selected PDF subset is labelled as such, never a complete source document.
    Only known, validated adapter asset references are rewritten in Markdown.
    """
    started = time.monotonic()
    run_out = Path(run_out)
    destination = run_out / 'documents' / document_id
    destination.mkdir(parents=True, exist_ok=False)
    errors, pages, markdown, text, raw_text, resources = [], [], [], [], [], []
    for case in cases:
        page_id = case['page_id']
        page_dir = run_out / 'pages' / page_id
        record_path = page_dir / 'result.json'
        if not record_path.is_file():
            errors.append(f'{page_id}:MISSING_PAGE_RESULT')
            pages.append({'page_id': page_id, 'status': 'FAIL'})
            continue
        record = json.loads(record_path.read_text())
        if record.get('page_id') != page_id or record.get('document_id') != document_id:
            errors.append(f'{page_id}:WRONG_PAGE_IDENTITY')
        if record.get('status') != 'PASS':
            errors.append(f'{page_id}:PAGE_{record.get("status", "MISSING_STATUS")}')
        pages.append({'page_id': page_id, 'page_index': case.get('page_index'),
                      'status': record.get('status'), 'result_reference': f'../../pages/{page_id}/result.json',
                      'input_pixel_hash': record.get('input_pixel_hash'),
                      'source_sha256': record.get('source_sha256'),
                      'unit_kind': record.get('unit_kind', case.get('unit_kind', 'page'))})
        page_md = record.get('markdown')
        if not isinstance(page_md, str) or not (page_dir/'markdown.md').is_file():
            errors.append(f'{page_id}:MISSING_PAGE_MARKDOWN')
            page_md = ''
        reference_owners = []
        for block in record.get('ordered_blocks', []):
            reference_owners.append(block)
            reference_owners.extend(block.get('embedded_images', []))
        for owner in reference_owners:
            reference = owner.get('image_reference')
            if not reference:
                continue
            relative = PurePosixPath(reference)
            if relative.is_absolute() or '..' in relative.parts:
                errors.append(f'{page_id}:INVALID_RESOURCE_REFERENCE')
                continue
            asset = page_dir / relative
            if not asset.is_file():
                errors.append(f'{page_id}:MISSING_RESOURCE:{reference}')
                continue
            relocated = f'../../pages/{page_id}/{relative}'
            page_md = page_md.replace(f']({reference})', f']({relocated})')
            pattern = r'(\bsrc\s*=\s*)([\"\x27]?)' + re.escape(reference) + r'\2(?=[\s/>])'
            page_md = re.sub(pattern, lambda match: match[1] + '"' + relocated + '"', page_md, flags=re.I)
            with asset.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            resources.append({'page_id': page_id, 'original_reference': reference,
                              'document_reference': relocated,
                              'sha256': digest})
        markdown.append(f'<!-- page_id: {page_id} -->\n\n{page_md}')
        text.append(record.get('text', ''))
        raw_text.append(record.get('raw_text', ''))
    scopes = []
    pdf_groups: dict[str, list[int]] = {}
    for case in cases:
        if case['kind'] == 'pdf':
            pdf_groups.setdefault(case['path'], []).append(case['page_index'])
    for path, indices in pdf_groups.items():
        import fitz
        try:
            with fitz.open(path) as source:
                total = len(source)
            scopes.append({'source_page_count': total, 'selected_page_indices': indices,
                           'complete_native_pdf': indices == list(range(total))})
        except (RuntimeError, ValueError, OSError) as exc:
            errors.append('SOURCE_PDF_METADATA_UNREADABLE:' + type(exc).__name__)
            scopes.append({'source_page_count': None, 'selected_page_indices': indices,
                           'complete_native_pdf': False})
    record = {'document_id': document_id, 'status': 'FAIL' if errors else 'PASS',
              'errors': errors, 'selected_unit_count': len(cases), 'pages': pages,
              'resources': resources, 'source_pdf_scopes': scopes,
              'scope': 'complete_native_pdf' if scopes and all(s['complete_native_pdf'] for s in scopes)
                       else 'selected_input_units',
              'cross_page_reconstruction': 'NOT_PERFORMED_PAGE_PRESERVING_ASSEMBLY',
              'outputs': {key: str((destination/name).relative_to(run_out)) for key, name in
                          [('markdown', 'document.md'), ('text', 'document.txt'),
                           ('raw_text', 'document.raw.txt'), ('ir', 'document.json')]}}
    _atomic_text(destination/'document.md', '\n\n---\n\n'.join(markdown) + '\n')
    _atomic_text(destination/'document.txt', '\n\f\n'.join(text))
    _atomic_text(destination/'document.raw.txt', '\n\f\n'.join(raw_text))
    if time.monotonic() >= deadline:
        record['status'] = 'FAIL'
        errors.append('DOCUMENT_DEADLINE_DURING_ASSEMBLY')
    atomic_json(destination/'document.json', record)
    if time.monotonic() >= deadline and 'DOCUMENT_DEADLINE_DURING_ASSEMBLY' not in errors:
        record['status'] = 'FAIL'
        errors.append('DOCUMENT_DEADLINE_DURING_ASSEMBLY')
        atomic_json(destination/'document.json', record)
    record.update(complete_monotonic=time.monotonic(), assembly_seconds=time.monotonic()-started)
    atomic_json(destination/'timing.json', {k: record[k] for k in ('complete_monotonic', 'assembly_seconds')})
    return record
