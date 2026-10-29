"""Strict, provenance-aware offline OCR scoring. Never imports model/runtime code."""
from __future__ import annotations

import argparse
import json
import math
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

SCORER_VERSION = 'ocrbench-scoring-v1'
LIMITS = {
    'printed_chinese': .01, 'printed_english': .005, 'technical_zh_en': .01,
    'handwritten': .05, 'handwritten_name': .03, 'seal_text': .05,
}
STRUCTURES = ('text_blocks', 'table', 'formula', 'reading_order', 'style', 'resources')


def distance(reference: Sequence, prediction: Sequence) -> int:
    """Levenshtein edit distance, O(min(n,m)) space; no semantic normalization."""
    if len(reference) < len(prediction):
        reference, prediction = prediction, reference
    previous = list(range(len(prediction) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(prediction, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                               previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def normalized(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).split())


def text_metrics(reference: str, prediction: str) -> dict[str, Any]:
    if not isinstance(reference, str) or not isinstance(prediction, str):
        raise ValueError('text scoring requires strings')
    edits = distance(reference, prediction)
    ref_n, pred_n = normalized(reference), normalized(prediction)
    words = reference.split()
    word_edits = distance(words, prediction.split())
    return {
        'gt_characters': len(reference), 'prediction_characters': len(prediction),
        'edit_count': edits, 'strict_CER': edits / len(reference) if reference else None,
        'normalized_edit_count': distance(ref_n, pred_n),
        'NFC_whitespace_CER': distance(ref_n, pred_n) / len(ref_n) if ref_n else None,
        'gt_words': len(words), 'word_edit_count': word_edits,
        'WER': word_edits / len(words) if words else None,
        'hallucinated_characters': len(prediction) if not reference else None,
        'exact_match': reference == prediction,
    }




def ai_provenance_errors(provenance: dict) -> list[str]:
    """Validate explicit AI review evidence without impersonating a human reference."""
    import re
    errors = []
    for field in ('judge_id',):
        if not isinstance(provenance.get(field), str) or not provenance[field].strip():
            errors.append('AI_missing_' + field)
    if not re.fullmatch('[0-9a-f]{64}', str(provenance.get('source_image_sha256', ''))):
        errors.append('AI_invalid_source_image_sha256')
    if provenance.get('review_status') != 'accepted':
        errors.append('AI_review_not_accepted')
    evidence = provenance.get('review_evidence')
    if not isinstance(evidence, list) or not evidence or any(
        not isinstance(e, dict) or not isinstance(e.get('path'), str) or not e['path'].strip()
        or not re.fullmatch('[0-9a-f]{64}', str(e.get('sha256', ''))) for e in evidence):
        errors.append('AI_review_evidence_missing_or_invalid')
    return errors

def prediction_digest(prediction: dict) -> str:
    """Bind human offline correspondence to exact predictions, never model-supplied GT IDs."""
    import hashlib
    return hashlib.sha256(json.dumps(prediction, sort_keys=True, ensure_ascii=False,
                                      separators=(',', ':')).encode()).hexdigest()



def _parse_table_html(value: str):
    """Strict HTML5 fragment syntax: optional cell ends are valid, truncated table is not."""
    import copy
    import html5lib
    parser = html5lib.HTMLParser(tree=html5lib.getTreeBuilder('lxml'),
                                strict=True, namespaceHTMLElements=False)
    try:
        fragment = parser.parseFragment(value)
    except html5lib.html5parser.ParseError as error:
        raise ValueError('invalid or truncated HTML table: ' + str(error)) from error
    # Comments are invisible, but their following text remains visible HTML content.
    visible_fragment = []
    for node in fragment:
        if isinstance(node,str) or isinstance(node.tag,str):
            visible_fragment.append(node)
        elif node.tail:
            visible_fragment.append(node.tail)
    fragment = visible_fragment
    tables = [node for node in fragment if not isinstance(node,str) and node.tag == 'table']
    if len(tables) != 1 or any(isinstance(node,str) and node.strip() for node in fragment):
        raise ValueError('exactly one HTML table fragment required')
    if any(not isinstance(node,str) and node is not tables[0] for node in fragment):
        raise ValueError('content outside table')
    table = copy.deepcopy(tables[0])  # Detach HTML5 fragment's synthetic parent for serialization.
    from lxml import etree
    etree.strip_elements(table, etree.Comment, with_tail=False)
    if table.tail and table.tail.strip():
        raise ValueError('content after table')
    if table.findall('.//table'):
        raise ValueError('nested table unsupported')
    for cell in table.xpath('.//td|.//th'):
        if any(int(cell.get(key,'1')) < 1 for key in ('rowspan','colspan')):
            raise ValueError('nonpositive cell span')
    return table

def _raw_table_metrics(reference: str, prediction: str) -> dict:
    """TEDS with span-aware nodes and normalized cell edit costs (PubTabNet definition).

    Strict HTML5 fragments are accepted, including optional cell closing tags.
    td/th are cells; th is retained as a distinct structural node. No repair is performed.
    """
    from apted import APTED, Config
    from lxml import etree

    class Node:
        def __init__(self, element, structure_only=False):
            self.tag = element.tag
            self.span = (int(element.get('rowspan', '1')), int(element.get('colspan', '1'))) if element.tag in ('td', 'th') else None
            self.content = []
            if element.tag in ('td', 'th') and not structure_only:
                def tokens(el):
                    result = list(el.text or '')
                    for child in el:
                        result += ['<' + child.tag + '>'] + tokens(child) + ['</' + child.tag + '>'] + list(child.tail or '')
                    return result
                self.content = tokens(element)
            self.children = [] if element.tag in ('td', 'th') else [Node(child, structure_only) for child in element]

    class Costs(Config):
        def rename(self, a, b):
            if a.tag != b.tag or a.span != b.span:
                return 1
            if a.tag in ('td', 'th'):
                return distance(a.content, b.content) / max(len(a.content), len(b.content), 1)
            return 0

    def parse(value):
        return _parse_table_html(value)

    true = parse(reference)  # Invalid GT is an annotation error, not model failure.
    try:
        pred = parse(prediction)
    except (ValueError, etree.XMLSyntaxError):
        return {'status': 'AVAILABLE', 'HTML_valid': False, 'TEDS': 0., 'TEDS_struct': 0.,
                'cell_edit_count': len(''.join(true.itertext())),
                'cell_gt_characters': len(''.join(true.itertext())), 'cell_CER': 1. if ''.join(true.itertext()) else None}
    denominator = max(len(list(true.iterdescendants())), len(list(pred.iterdescendants())), 1)
    scores = [max(0., 1. - APTED(Node(true, structural), Node(pred, structural), Costs()).compute_edit_distance() / denominator)
              for structural in (False, True)]

    def grid(root):
        occupied, result = set(), {}
        rows = root.xpath('./tr|./thead/tr|./tbody/tr|./tfoot/tr')
        for row_index, row in enumerate(rows):
            col = 0
            for cell in row:
                if cell.tag not in ('td', 'th'):
                    raise ValueError('unexpected row child')
                while (row_index, col) in occupied:
                    col += 1
                rs, cs = int(cell.get('rowspan', '1')), int(cell.get('colspan', '1'))
                if rs * cs > 100000 or row_index + rs > len(rows):
                    raise ValueError('cell span outside table')
                for rr in range(row_index, row_index + rs):
                    for cc in range(col, col + cs):
                        if (rr, cc) in occupied:
                            raise ValueError('overlapping spans')
                        occupied.add((rr, cc))
                result[(row_index, col, rs, cs)] = ''.join(cell.itertext())
                col += cs
        return result
    true_cells = grid(true)
    try:
        pred_cells = grid(pred)
    except ValueError:
        return {'status': 'AVAILABLE', 'HTML_valid': False, 'TEDS': scores[0], 'TEDS_struct': scores[1],
                'cell_edit_count': None, 'cell_gt_characters': sum(map(len, true_cells.values())), 'cell_CER': None}
    chars = sum(map(len, true_cells.values()))
    edits = sum(distance(true_cells.get(k, ''), pred_cells.get(k, '')) for k in true_cells.keys() | pred_cells.keys())
    return {'status': 'AVAILABLE', 'HTML_valid': True, 'TEDS': scores[0], 'TEDS_struct': scores[1],
            'cell_edit_count': edits, 'cell_gt_characters': chars, 'cell_CER': edits / chars if chars else None,
            'empty_gt_cell_insertions': edits if not chars else None}


def table_score_view(value: str) -> tuple[str, int]:
    """table-score-view-v1: remove display-only cell markup, retaining semantic trees."""
    from lxml import etree
    import html5lib
    root = _parse_table_html(value)
    images = len(root.findall('.//img'))
    wrappers = ('span', 'b', 'strong', 'i', 'em', 'font', 'small', 'big')
    for cell in root.xpath('.//td|.//th'):
        # Removing an element must retain its following text, including OCR supplement text.
        for element in list(cell.findall('.//br')) + list(cell.findall('.//img')):
            parent = element.getparent()
            previous = element.getprevious()
            tail = ('\n' if element.tag == 'br' else '') + (element.tail or '')
            if previous is None:
                parent.text = (parent.text or '') + tail
            else:
                previous.tail = (previous.tail or '') + tail
            parent.remove(element)
        etree.strip_tags(cell, *wrappers)
        if cell.text is not None:
            cell.text = cell.text.lstrip()
            if not len(cell):
                cell.text = cell.text.rstrip()
        if len(cell) and cell[-1].tail is not None:
            cell[-1].tail = cell[-1].tail.rstrip()
    return html5lib.serialize(root, tree='lxml', omit_optional_tags=False,
                              quote_attr_values='always', use_trailing_solidus=True), images


def table_metrics(reference: str, prediction: str) -> dict:
    """Score canonical visible text/structure, with untouched product HTML diagnostics."""
    raw = _raw_table_metrics(reference, prediction)
    diagnostics = {'raw_HTML_TEDS':raw['TEDS'], 'raw_HTML_TEDS_struct':raw['TEDS_struct'],
                   'raw_cell_CER':raw['cell_CER'], 'raw_cell_edit_count':raw['cell_edit_count'],
                   'raw_cell_gt_characters':raw['cell_gt_characters']}
    if not raw['HTML_valid']:
        return dict(raw, score_view_version='table-score-view-v1', html_parser_version='html5lib-1.1-strict-fragment-v1', **diagnostics)
    true_view, reference_images = table_score_view(reference)
    prediction_view, prediction_images = table_score_view(prediction)
    scored = _raw_table_metrics(true_view, prediction_view)
    return dict(scored, score_view_version='table-score-view-v1', html_parser_version='html5lib-1.1-strict-fragment-v1',
                reference_score_view=true_view, prediction_score_view=prediction_view,
                reference_image_count=reference_images, prediction_image_count=prediction_images,
                resource_validation_required=bool(reference_images or prediction_images), **diagnostics)


def structural_scores(prediction: dict, gt: dict) -> dict:
    """Evaluate independent offline matching bound by digest; absent matches never guessed."""
    answer = {}
    applicability = gt.get('applicability', {})
    annotation = gt.get('structure_GT', {})
    assessment = gt.get('assessment', {})
    human_correspondence = (gt.get('acceptance_rule_id') == 'page-good-v1' and assessment.get('kind') == 'human_verified_correspondence')
    ai_correspondence = (gt.get('acceptance_rule_id') == 'page-good-ai-v1' and assessment.get('kind') == 'ai_verified_correspondence'
                         and not ai_provenance_errors(assessment))
    verified = ((human_correspondence or ai_correspondence) and assessment.get('prediction_sha256') == prediction_digest(prediction))
    blocks = prediction.get('ordered_blocks', [])
    matches = assessment.get('matches', {}) if verified else {}
    used = [index for index in matches.values() if index is not None]
    if len(used) != len(set(used)) or any(not isinstance(i, int) or i < 0 or i >= len(blocks) for i in used):
        raise ValueError('offline matches must be injective valid predicted block indices')
    def matched(block_id):
        index = matches.get(block_id)
        return blocks[index] if index is not None else None
    for task in STRUCTURES:
        if applicability.get(task) is False:
            answer[task] = {'status': 'NOT_APPLICABLE'}
            continue
        values = annotation.get(task)
        if not verified or values is None:
            answer[task] = {'status': 'UNAVAILABLE', 'reason': 'INDEPENDENT_BOUND_CORRESPONDENCE_OR_GT_MISSING'}
            continue
        if task == 'text_blocks':
            if not values:
                answer[task] = {'status': 'UNAVAILABLE', 'reason': 'EMPTY_BLOCK_GT'}
                continue
            present = [v for v in values if matched(v['id']) is not None]
            critical = [v for v in values if v.get('critical')]
            recall = len(present) / len(values)
            critical_recall = sum(matched(v['id']) is not None for v in critical) / len(critical) if critical else 1.
            answer[task] = {'status': 'AVAILABLE', 'recall': recall, 'critical_recall': critical_recall,
                            'passes': recall >= .99 and critical_recall == 1.}
        elif task == 'reading_order':
            if not values:
                answer[task] = {'status': 'UNAVAILABLE', 'reason': 'EMPTY_ORDER_GT'}
                continue
            outcomes = [matches.get(v['before']) is not None and matches.get(v['after']) is not None
                        and matches[v['before']] < matches[v['after']] for v in values]
            severe = sum(not ok and v.get('severe', False) for ok, v in zip(outcomes, values))
            accuracy = sum(outcomes) / len(values)
            answer[task] = {'status': 'AVAILABLE', 'pair_accuracy': accuracy, 'severe_errors': severe,
                            'passes': accuracy >= .99 and severe == 0}
        elif task == 'table':
            if not values:
                answer[task] = {'status': 'UNAVAILABLE', 'reason': 'EMPTY_TABLE_GT'}
                continue
            tables = []
            try:
                for value in values:
                    block = matched(value['id'])
                    tables.append(table_metrics(value['html'], (block or {}).get('table_html') or (block or {}).get('raw_text', '')))
            except ImportError:
                answer[task] = {'status': 'UNAVAILABLE', 'reason': 'REQUIRES_APTED_1_0_3_LXML_5_4_0_HTML5LIB_1_1'}
                continue
            chars = sum(v['cell_gt_characters'] for v in tables)
            edits = sum(v['cell_edit_count'] or 0 for v in tables)
            cer = edits / chars if chars else None
            teds = sum(v['TEDS'] for v in tables) / len(tables)
            structure = sum(v['TEDS_struct'] for v in tables) / len(tables)
            critical_ok = all((matched(v['id']) or {}).get(a['field']) == a['value'] for v in values for a in v.get('critical_assertions', []))
            selected = {matches.get(v['id']) for v in values} - {None}
            predicted_tables = {i for i, b in enumerate(blocks) if b.get('table_html') is not None or
                                b.get('block_type', b.get('type', b.get('label'))) == 'table'}
            unmatched_tables = sorted(predicted_tables - selected)
            passes = (not unmatched_tables and all(v['HTML_valid'] and v['cell_edit_count'] is not None for v in tables)
                      and teds >= .95 and structure >= .97 and (cer <= .01 if cer is not None else edits == 0) and critical_ok)
            requires_resources = any(v.get('resource_validation_required') for v in tables)
            answer[task] = {'status': 'AVAILABLE', 'tables': tables, 'TEDS': teds, 'TEDS_struct': structure,
                            'cell_CER': cer, 'critical_assertions_pass': critical_ok,
                            'unmatched_predicted_table_indices': unmatched_tables,
                            'resource_validation_required': requires_resources, 'passes': passes}
        elif task == 'formula':
            answer[task] = {'status': 'UNAVAILABLE', 'reason': 'RENDER_AND_STRUCTURE_REVIEW_REQUIRED',
                            'latex_EM': [((matched(v['id']) or {}).get('formula_latex') == v['latex']) for v in values]}
        elif task in ('resources', 'style'):
            # Assertions are independently checked offline and bound to exact output digest.
            assertions = assessment.get(task + '_assertions')
            if not assertions or any(not isinstance(v.get('passes'), bool) for v in assertions):
                answer[task] = {'status': 'UNAVAILABLE', 'reason': 'BOUND_OFFLINE_ASSERTIONS_REQUIRED'}
            else:
                required_ids = {v['id'] for v in values}
                checked_ids = {v['id'] for v in assertions}
                complete = required_ids == checked_ids
                answer[task] = {'status': 'AVAILABLE' if complete else 'UNAVAILABLE',
                                'passes': complete and all(v['passes'] for v in assertions), 'assertions': assertions}
    if answer.get('table', {}).get('resource_validation_required'):
        resource_metric = answer.get('resources', {})
        if applicability.get('resources') is not True or resource_metric.get('status') in ('NOT_APPLICABLE', None):
            answer['resources'] = {'status':'UNAVAILABLE', 'reason':'TABLE_IMAGES_REQUIRE_EXPLICIT_RESOURCE_GT_AND_VALIDATION'}
    return answer

def score_page(prediction: dict, gt: dict | None) -> dict:
    page_id = prediction.get('page_id') or (gt or {}).get('page_id')
    result = {'page_id': page_id, 'scorer_version': SCORER_VERSION,
              'is_good': None, 'status': 'UNSCORED', 'reasons': [], 'text_groups': [],
              'structural_metrics': {}}
    bad, missing = [], []
    failed = prediction.get('status') not in ('PASS', 'SUCCESS', 'COMPLETE')
    if failed:
        bad.append('execution_failed')
    for key in ('truncated', 'context_overflow', 'critical_error', 'severe_order_error'):
        if prediction.get(key):
            bad.append(key)
    if prediction.get('artifacts_valid') is False or prediction.get('identity_valid') is False:
        bad.append('artifacts_or_identity_invalid')
    # Partial model output is retained diagnostically but failed tasks score as empty.
    if gt:
        if gt.get('page_id') != page_id:
            bad.append('wrong_page_identity')
        for field in ('acceptance_rule_id', 'GT_version', 'scorer_version', 'unit_kind',
                      'required_tasks', 'required_text_groups', 'required_output_units',
                      'critical_assertions', 'GT_complete_for_required_tasks'):
            if field not in gt:
                missing.append('missing_' + field)
        for version_field in ('GT_version', 'acceptance_rule_id', 'scorer_version'):
            if not isinstance(gt.get(version_field), str) or not gt[version_field].strip():
                missing.append('unfrozen_' + version_field)
        rule = gt.get('acceptance_rule_id')
        if rule not in ('page-good-v1', 'page-good-ai-v1'):
            missing.append('unknown_acceptance_rule')
        if gt.get('scorer_version') != SCORER_VERSION:
            missing.append('scorer_version_mismatch')
        if not gt.get('GT_complete_for_required_tasks'):
            missing.append('GT_incomplete')
        if rule == 'page-good-ai-v1':
            provenance = gt.get('reference_provenance', {})
            result['reference_kind'] = 'AI_JUDGED'
            if provenance.get('kind') != 'ai_verified':
                missing.append('GT_not_ai_verified')
            missing.extend(ai_provenance_errors(provenance))
            # Rendered PDF pages and crops are different files from the admitted source.
            # Bind RGB to RGB, and source bytes only to an explicitly named source hash.
            import re
            if not re.fullmatch('[0-9a-f]{64}', str(provenance.get('input_pixel_hash', ''))):
                missing.append('AI_reference_input_pixel_hash_required')
            elif prediction.get('input_pixel_hash') != provenance['input_pixel_hash']:
                bad.append('AI_reference_input_pixels_mismatch')
            if provenance.get('source_sha256') is not None:
                if prediction.get('source_sha256') != provenance['source_sha256']:
                    bad.append('AI_reference_original_source_mismatch')
            uncertainties = gt.get('uncertainties', [])
            if not isinstance(uncertainties, list) or any(not isinstance(u,dict) or (u.get('resolved') is not True and u.get('affects_required_tasks',True)) for u in uncertainties):
                missing.append('AI_unresolved_required_uncertainties')
            if provenance.get('kind') == 'ai_verified' and gt.get('provenance',{}).get('kind') == 'human_verified':
                missing.append('AI_reference_conflicting_human_label')
        else:
            result['reference_kind'] = 'HUMAN_VERIFIED' if gt.get('provenance', {}).get('kind') == 'human_verified' else 'UNVERIFIED'
            if gt.get('provenance', {}).get('kind') != 'human_verified':
                missing.append('GT_not_human_verified')
            if gt.get('reference_provenance', {}).get('kind') == 'ai_verified':
                missing.append('human_reference_conflicting_AI_label')
        if 'text' in gt.get('required_tasks', []) and not gt.get('required_text_groups'):
            missing.append('required_text_groups_empty')
        for task in gt.get('required_tasks', []):
            if task not in ('text', *STRUCTURES):
                missing.append('unsupported_required_task:' + str(task))
            elif task in STRUCTURES and gt.get('applicability', {}).get(task) is not True:
                missing.append('required_task_applicability_conflict:' + task)
        for field in gt.get('required_output_units', []):
            if field not in prediction or prediction[field] is None:
                bad.append('missing_required_output:' + field)
        for group in gt.get('required_text_groups', []):
            field = group.get('prediction_field', 'raw_text')
            reference = group.get('text')
            if not isinstance(reference, str):
                missing.append('text_GT_missing:' + str(group.get('id')))
                continue
            value = prediction.get(field)
            if value is None and not failed:
                bad.append('missing_text_output:' + field)
            value = '' if failed or value is None else value
            if not isinstance(value, str):
                bad.append('invalid_text_output:' + field)
                value = ''
            metrics = text_metrics(reference, value)
            profile = group.get('profile')
            if profile not in LIMITS:
                missing.append('unknown_text_profile:' + str(profile))
                passes = None
            else:
                passes = (metrics['strict_CER'] <= LIMITS[profile] if reference
                          else metrics['hallucinated_characters'] == 0)
                if profile == 'printed_english' and reference:
                    passes = passes and metrics['WER'] is not None and metrics['WER'] <= .02
            result['text_groups'].append({'id': group.get('id'), 'profile': profile,
                                          'passes': passes, **metrics})
        result['structural_metrics'] = structural_scores(prediction, gt)
        for task, metric in result['structural_metrics'].items():
            if metric['status'] == 'UNAVAILABLE':
                missing.append('metric_unavailable:' + task)
            elif metric['status'] == 'AVAILABLE' and not metric.get('passes', False):
                bad.append('structure_gate_failed:' + task)
        for assertion in gt.get('critical_assertions', []):
            field = assertion.get('field', 'raw_text')
            actual = '' if failed else prediction.get(field)
            operation = assertion.get('operation')
            if operation == 'equals':
                passes = actual == assertion.get('value')
            elif operation == 'contains' and isinstance(actual, str) and isinstance(assertion.get('value'), str):
                passes = assertion['value'] in actual
            else:
                missing.append('unsupported_critical_assertion')
                continue
            if not passes:
                bad.append('critical_assertion_failed:' + str(assertion.get('id')))
    else:
        missing.append('GT_missing')
    if bad:
        result.update(is_good=False, status='FAIL', reasons=bad + missing)
    elif missing:
        result['reasons'] = missing
    else:
        good = all(g['passes'] is True for g in result['text_groups'])
        result.update(is_good=good, status='PASS' if good else 'FAIL',
                      reasons=[] if good else ['page_text_gate_failed'])
    result['GT_complete'] = not missing
    # Text validity is independent of unavailable formula/table scoring.
    reference_errors = [reason for reason in missing if reason.startswith(('unfrozen_', 'unknown_acceptance_', 'scorer_version_', 'GT_not_', 'AI_', 'human_reference_conflicting_'))]
    identity_errors = [reason for reason in bad if reason in ('wrong_page_identity', 'AI_reference_input_pixels_mismatch', 'AI_reference_original_source_mismatch')]
    groups = (gt or {}).get('required_text_groups', [])
    result['text_reference_verified'] = bool(gt and groups) and not reference_errors and not identity_errors and all(isinstance(g.get('text'),str) for g in groups)
    result['text_reference_reasons'] = reference_errors + identity_errors
    result['text_metrics_scope'] = 'VERIFIED_REFERENCE' if result['text_reference_verified'] else 'UNVERIFIED_REFERENCE_DIAGNOSTIC_ONLY'
    result['unit_kind'] = (gt or {}).get('unit_kind', 'UNKNOWN')
    families = {side: value for side, value in (
        ('reference', (gt or {}).get('source_family_id')),
        ('prediction', prediction.get('source_family_id')))
        if isinstance(value, str) and value.strip() and value.strip().upper() != 'UNKNOWN'}
    result['source_family_reference_id'] = families.get('reference')
    result['source_family_prediction_id'] = families.get('prediction')
    if len(set(families.values())) > 1:
        result.update(source_family_id=None, source_family_status='CONFLICT')
    elif families:
        result['source_family_id'] = next(iter(families.values()))
        result['source_family_status'] = 'REFERENCE_AND_PREDICTION_MATCH' if len(families) == 2 else next(iter(families)).upper() + '_ONLY'
    else:
        result.update(source_family_id=None, source_family_status='UNKNOWN')
    return result


def summarize(pages: list[dict], wall_seconds: float, gpu_joules: float | None = None) -> dict:
    if not math.isfinite(wall_seconds) or wall_seconds <= 0:
        raise ValueError('wall_seconds must be the positive finite full submitted workload duration')
    if gpu_joules is not None and (not math.isfinite(gpu_joules) or gpu_joules < 0):
        raise ValueError('gpu_joules must be finite and nonnegative')
    workload_GT_complete = bool(pages) and all(p['GT_complete'] for p in pages)
    kinds = sorted({p.get('reference_kind', 'UNVERIFIED') for p in pages})

    def aggregate(group):
        good = sum(p['is_good'] is True for p in group)
        approved_pages = [p for p in group if p.get('text_reference_verified')]
        approved = [m for p in approved_pages for m in p['text_groups']]
        diagnostic = [m for p in group if not p.get('text_reference_verified') for m in p['text_groups']]
        chars = sum(m['gt_characters'] for m in approved)
        errors = sum(m['edit_count'] for m in approved)
        group_macro = [m['strict_CER'] for m in approved if m['strict_CER'] is not None]
        unit_rates = []
        families = {}
        unknown_family_units = 0
        for page in approved_pages:
            unit_chars = sum(metric['gt_characters'] for metric in page['text_groups'])
            unit_errors = sum(metric['edit_count'] for metric in page['text_groups'])
            if not unit_chars:
                continue  # Blank-only references have no CER denominator.
            rate = unit_errors / unit_chars
            unit_rates.append(rate)
            family = page.get('source_family_id')
            if not isinstance(family, str) or not family.strip() or family.strip().upper() == 'UNKNOWN':
                unknown_family_units += 1
                continue
            entry = families.setdefault(family, {'unit_CERs': [], 'gt_characters': 0, 'edit_count': 0})
            entry['unit_CERs'].append(rate)
            entry['gt_characters'] += unit_chars
            entry['edit_count'] += unit_errors
        family_rates = {family: sum(values['unit_CERs']) / len(values['unit_CERs'])
                        for family, values in families.items()}
        family_macro = (sum(family_rates.values()) / len(family_rates)
                        if family_rates and not unknown_family_units else None)
        family_macro_status = ('UNAVAILABLE_UNKNOWN_SOURCE_FAMILY' if unknown_family_units else
                               'AVAILABLE' if family_rates else 'UNAVAILABLE_NO_NONEMPTY_VERIFIED_REFERENCE')
        family_coverage = {}
        for label, rows in (('submitted', group), ('text_reference_verified', approved_pages)):
            known = [page['source_family_id'] for page in rows
                     if isinstance(page.get('source_family_id'), str) and page['source_family_id'].strip()
                     and page['source_family_id'].strip().upper() != 'UNKNOWN']
            family_coverage[label] = {'unit_count':len(rows), 'known_family_units':len(known),
                                      'unknown_family_units':len(rows)-len(known),
                                      'known_source_family_count':len(set(known))}
        all_chars = sum(m['gt_characters'] for p in group for m in p['text_groups'])
        return {'submitted_count':len(group),'good_count':good,
            'GT_complete_count':sum(p['GT_complete'] for p in group),
            'text_reference_verified_units':len(approved_pages),
            'text_reference_verified_characters':chars,
            'text_reference_total_declared_characters':all_chars,
            'text_reference_character_coverage':chars/all_chars if all_chars else None,
            'text_reference_unit_coverage':len(approved_pages)/len(group) if group else None,
            'micro_CER':errors/chars if chars else None,
            'macro_CER':family_macro,
            'unit_macro_CER':sum(unit_rates)/len(unit_rates) if unit_rates else None,
            'family_macro_CER':family_macro,
            'family_macro_status':family_macro_status,
            'macro_aggregation_version':'unit_then_source_family_CER_v1',
            'macro_aggregation':'mean across source families of mean unit CER; unit CER=sum group edits/sum group GT characters',
            'macro_unit_count':len(unit_rates),
            'macro_known_family_unit_count':len(unit_rates)-unknown_family_units,
            'macro_unknown_family_unit_count':unknown_family_units,
            'macro_family_count':len(families),
            'source_family_coverage':family_coverage,
            'verified_blank_only_units':len(approved_pages)-len(unit_rates),
            'text_group_macro_CER_diagnostic':sum(group_macro)/len(group_macro) if group_macro else None,
            'family_macro_components':{family:{'unit_count':len(value['unit_CERs']),
                'unit_macro_CER':family_rates[family], 'gt_characters':value['gt_characters'],
                'edit_count':value['edit_count']} for family,value in families.items()},
            'gt_characters':chars,'edit_count':errors,
            'unverified_text_diagnostics':diagnostic,
            'primary_good_units_per_second':good/wall_seconds if workload_GT_complete else None,
            'primary_status':'AVAILABLE' if workload_GT_complete else 'UNAVAILABLE_FOR_PRIMARY_COMPARISON',
            'diagnostic_known_good_units_per_second':good/wall_seconds,
            'J_per_good_unit':gpu_joules/good if good and gpu_joules is not None and workload_GT_complete else None,
            'energy_reason':'NO_GOOD_PAGES' if not good else 'INCOMPLETE_GT' if not workload_GT_complete else 'METER_UNAVAILABLE' if gpu_joules is None else None}

    strata = {}
    for kind in kinds:
        selected = [p for p in pages if p.get('reference_kind','UNVERIFIED') == kind]
        strata[kind] = {'units':{unit:aggregate([p for p in selected if p['unit_kind']==unit]) for unit in sorted({p['unit_kind'] for p in selected})}}
    units = {}
    for unit in sorted({p['unit_kind'] for p in pages}):
        group = [p for p in pages if p['unit_kind']==unit]
        if len({p.get('reference_kind','UNVERIFIED') for p in group}) == 1:
            units[unit] = aggregate(group)
        else:
            units[unit] = {'submitted_count':len(group),'good_count':None,'micro_CER':None,'macro_CER':None,
                'unit_macro_CER':None,'family_macro_CER':None,'family_macro_status':'UNAVAILABLE_MIXED_REFERENCE_KINDS_USE_STRATA',
                'primary_good_units_per_second':None,'primary_status':'UNAVAILABLE_MIXED_REFERENCE_KINDS_USE_STRATA',
                'diagnostic_known_good_units_per_second':None,'J_per_good_unit':None,
                'reference_kind_counts':dict(Counter(p.get('reference_kind','UNVERIFIED') for p in group))}
    return {'scorer_version':SCORER_VERSION,'full_workload_GT_complete':workload_GT_complete,
            'all_submitted_wall_seconds':wall_seconds,'reference_kinds':kinds,
            'reference_strata':strata,'units':units,'pages':pages}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', required=True, type=Path)
    parser.add_argument('--gt', required=True, type=Path)
    parser.add_argument('--wall-seconds', required=True, type=float)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    pred = json.loads(args.predictions.read_text())
    gold = json.loads(args.gt.read_text())
    pred = pred['pages'] if isinstance(pred, dict) else pred
    gold = gold['pages'] if isinstance(gold, dict) else gold
    pred_map = {p['page_id']: p for p in pred}
    gt_map = {p['page_id']: p for p in gold}
    if len(pred_map) != len(pred) or len(gt_map) != len(gold):
        raise ValueError('duplicate page_id')
    # GT fixed workload is primary: absent predictions stay failures, extras stay visible.
    ids = list(gt_map) + [p for p in pred_map if p not in gt_map]
    scored = [score_page(pred_map.get(p, {'page_id': p, 'status': 'FAIL'}), gt_map.get(p)) for p in ids]
    report = summarize(scored, args.wall_seconds)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    main()
