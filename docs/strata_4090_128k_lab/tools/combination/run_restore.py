"""Actual-history A -> B -> A lifecycle screen for the deployed combination.

Wrong prime replies remain in the returning history.  The histories can differ
between arms, so this screen does not estimate a paired restore speed benefit.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from lab import http, scoring
from lab.assets import verify as verify_assets
from lab.core import check_budget, dump, gpu_lock, hash_obj, load_config
from lab.runner import audited_chat, evidence_lifecycle, make_run_config, validate_counter
from lab.tokenizer import StrataCounter

spec = importlib.util.spec_from_file_location('strata_restore_combo', Path(__file__).with_name('run_combo.py'))
combo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(combo)

TARGETS = (69632, 102400)


def actual_history(request, response):
    """Retain literal observed text/reasoning, including wrong or empty answers."""
    text, reasoning = response.get('text', ''), response.get('reasoning', '')
    if not isinstance(text, str) or not isinstance(reasoning, str):
        raise RuntimeError('RESPONSE_HISTORY_NOT_AUDITABLE: text and reasoning must be strings')
    return copy.deepcopy(request['messages']) + [
        {'role': 'assistant', 'content': text, 'reasoning_content': reasoning}]


def followup_request(history, frozen_case):
    request = copy.deepcopy(frozen_case['body'])
    message = request['messages'][-1]
    if message.get('role') != 'user':
        raise ValueError('Frozen follow-up must end in a user message')
    request['messages'] = copy.deepcopy(history) + [copy.deepcopy(message)]
    return request


def select_cases(corpus):
    if corpus.get('max_context') != 131072 or hash_obj(corpus['cases']) != corpus.get('corpus_sha256'):
        raise ValueError('CORPUS_IDENTITY_MISMATCH')
    indexed = {}
    for case in corpus['cases']:
        if case['id'] in indexed:
            raise ValueError('Duplicate frozen case ID')
        if case.get('request_sha256') != hash_obj(case['body']):
            raise ValueError('FROZEN_REQUEST_HASH_MISMATCH: ' + case['id'])
        indexed[case['id']] = case
    selected = {}
    for target in TARGETS:
        selected[target] = {stage: indexed[prefix + str(target)] for stage, prefix in (
            ('prime', 'park-prime-'), ('side', 'park-side-'),
            ('restore', 'restore-'), ('sampled', 'sampled-retrieval-'))}
        if any(case.get('kind') != 'exact' for case in selected[target].values()):
            raise ValueError('Restore lifecycle expects frozen exact-answer cases')
    return selected


def append_record(path, record):
    with Path(path).open('a', encoding='utf-8') as destination:
        destination.write(json.dumps(record, ensure_ascii=False) + '\n')
        destination.flush()
        os.fsync(destination.fileno())


def execute_stage(c, counter, server, folder, arm, target, stage, case, request):
    prefix = Path(folder) / f'{target}-{stage}'
    dump(prefix.with_suffix('.request.json'), request)
    local_tokens = counter(request)
    check_budget(local_tokens, request['max_tokens'], c['max_context'], c['safety_tokens'])
    log = Path(folder) / 'engine.log'
    offset = log.stat().st_size if log.exists() else 0
    before = combo.resource_sample(server)
    started = time.time()
    response = audited_chat(server, counter, c, request)
    dump(prefix.with_suffix('.response.json'), response)
    with log.open('rb') as source:
        source.seek(offset)
        delta = source.read().decode('utf-8', errors='replace')
    prefix.with_suffix('.engine.log').write_text(delta, encoding='utf-8')
    score = scoring.score(case, response)
    restore = combo.restore_evidence({'expected_restore': stage == 'restore',
                                      'restore_min_tokens': 64000}, delta)
    row = {'schema_version': 1, 'mode': 'ACTUAL_HISTORY_RESTORE', 'arm': arm,
           'target_tokens': target, 'stage': stage, 'started': started,
           'source_case_id': case['id'], 'source_request_sha256': case['request_sha256'],
           'request_sha256': hash_obj(request), 'request': request,
           'local_prompt_tokens': local_tokens, 'max_tokens': request['max_tokens'],
           'expected': case['expected'], 'score': score, 'restore_evidence': restore,
           'metrics': http.measurements(response), 'response': response,
           'engine_log_delta': prefix.with_suffix('.engine.log').name,
           'memory_before': before, 'memory_after': combo.resource_sample(server)}
    append_record(Path(folder) / 'requests.jsonl', row)
    print(json.dumps({'arm': arm, 'target': target, 'stage': stage, 'score': score,
                      'restore': restore, 'metrics': row['metrics']}, ensure_ascii=False), flush=True)
    if response.get('error') or server.abort_reason:
        raise RuntimeError('RESTORE_INFRASTRUCTURE: ' + str(response.get('error') or server.abort_reason))
    if response.get('tools'):
        raise RuntimeError('RESTORE_UNAUTHORIZED_TOOL_OUTPUT')
    return row


def one_arm(c, tree, arm, ready, folder, selected, counter):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    dump(folder / 'cooldown-before-arm.json', combo.wait_cool(c))
    rows = []
    with combo.combination_server(c, tree, arm, ready, folder) as server:
        dump(folder / 'activation.json', combo.validate_startup(server, arm))
        validate_counter(counter, server)
        combo.history_counter_probe(server, counter, c, folder)
        for target in TARGETS:
            dump(folder / f'{target}-cooldown-before-prime.json', combo.wait_cool(c, loaded=True))
            cases = selected[target]
            prime = copy.deepcopy(cases['prime']['body'])
            prime_row = execute_stage(c, counter, server, folder, arm, target, 'prime', cases['prime'], prime)
            rows.append(prime_row)
            # Even if the model answered incorrectly, its literal reply is the
            # only valid assistant history for testing its parked conversation.
            history = actual_history(prime, prime_row['response'])
            side = copy.deepcopy(cases['side']['body'])
            rows.append(execute_stage(c, counter, server, folder, arm, target, 'side', cases['side'], side))
            returned = followup_request(history, cases['restore'])
            restore_row = execute_stage(c, counter, server, folder, arm, target, 'restore', cases['restore'], returned)
            rows.append(restore_row)
            history = actual_history(returned, restore_row['response'])
            sampled = followup_request(history, cases['sampled'])
            rows.append(execute_stage(c, counter, server, folder, arm, target, 'sampled', cases['sampled'], sampled))
    summary = {'arm': arm, 'requests': len(rows),
               'answer_failures': sum(row['score'].get('pass') is not True for row in rows),
               'restore_failures': sum(not row['restore_evidence']['pass'] for row in rows),
               'actual_restore_tokens': [row['restore_evidence']['restored_tokens'] for row in rows if row['stage'] == 'restore'],
               'lifecycle_pass': all(row['restore_evidence']['pass'] for row in rows),
               'all_answers_pass': all(row['score'].get('pass') is True for row in rows),
               'scope': 'actual generated histories; answer failures retained; no paired speed or formal quality NI claim'}
    dump(folder / 'arm-summary.json', summary)
    return summary


def run(config_path, tree, corpus_path, out, execute=False):
    c = load_config(config_path)
    tree, out, corpus_path = Path(tree).resolve(), Path(out).resolve(), Path(corpus_path).resolve()
    if int(c['port']) != 18089 or c['max_context'] != 131072:
        raise ValueError('Restore validation is fixed to lab port 18089 and total context 131072')
    if c['min_available_mib'] < 4096 or c.get('gpu_temp_abort_c', 85) > 85:
        raise ValueError('Do not weaken RAM or thermal protection')
    if Path(c['deployed_repo']).resolve() != tree or c.get('request_overrides'):
        raise ValueError('Use the isolated combination tree without request overrides')
    corpus = json.loads(corpus_path.read_text())
    selected = select_cases(corpus)
    build, ready = combo.validate_tree(tree), combo.ready_spec()
    prepared = {arm: make_run_config(c, tree, arm, ready, out / ('prepared-' + arm)) for arm in ('base', 'cfg')}
    combo.assert_same_except_kvres(prepared['base'], prepared['cfg'])
    if any(Path(value.get('cwd', '')).resolve() != tree for value in prepared.values()):
        raise ValueError('Engine cwd must be the isolated combination tree')
    plan = {'schema_version': 1, 'mode': 'ACTUAL_HISTORY_RESTORE', 'arms': ['base', 'cfg'],
            'order': ['base', 'cfg'], 'targets': list(TARGETS), 'source': build,
            'kv_resident': {'base': 0, 'cfg': 20480}, 'fresh_engines_per_arm': 1,
            'corpus_sha256': corpus['corpus_sha256'],
            'source_cases': {str(target): {stage: case['id'] for stage, case in cases.items()}
                             for target, cases in selected.items()},
            'dynamic_history': 'Every returned assistant text/reasoning is literal observed output; never replaced with gold',
            'restore_min_tokens': 64000, 'primary_result': 'lifecycle mechanism and answer correctness',
            'scope': 'Histories may differ across arms; no fixed-hash paired speed or formal quality NI claim',
            'quality_failure_policy': 'Preserve wrong answers and missing restore evidence; continue other stages/arms',
            'infrastructure_failure_policy': 'Stop on tool output, HTTP/usage/budget/resource/asset/production drift',
            'ready': ready, 'deployment_approved': False}
    plan['plan_sha256'] = hash_obj(plan)
    if not execute:
        return {'state': 'DRY_RUN', 'plan': plan}
    protected = combo.protected_hashes(c)
    initial_service = combo.assert_service_inactive()
    assets = verify_assets(c)
    out.mkdir(parents=True, exist_ok=False)
    dump(out / 'campaign.json', plan)
    dump(out / 'corpus.json', corpus)
    dump(out / 'assets.json', assets)
    dump(out / 'production-before.json', {'service': initial_service, 'file_sha256': protected})
    summaries = []
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    with gpu_lock(c.get('gpu_lock_workspace', c['workspace'])):
        with evidence_lifecycle(c, out):
            try:
                counter = StrataCounter(tree, c['gguf'], c['template'])
                for arm in plan['order']:
                    combo.assert_service_inactive()
                    combo.assert_protected(c, protected)
                    verify_assets(c)
                    if combo.validate_tree(tree) != build:
                        raise RuntimeError('BUILD_RECEIPT_CHANGED')
                    summaries.append(one_arm(c, tree, arm, ready, out / arm, selected, counter))
                    dump(out / 'summary.json', {'arms': summaries, 'paired_speed_claim': False,
                                                'formal_noninferiority': 'NOT_ESTABLISHED'})
            finally:
                dump(out / 'production-after.json', {'service': combo.assert_service_inactive(),
                                                     'file_sha256': combo.assert_protected(c, protected)})
    passed = all(x['lifecycle_pass'] and x['all_answers_pass'] for x in summaries)
    return {'state': 'COMPLETE', 'results': str(out), 'lifecycle_and_answers_pass': passed,
            'arms': summaries, 'deployment_approved': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--corpus', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    result = run(args.config, args.tree, args.corpus, args.out, args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 1 if result.get('lifecycle_and_answers_pass') is False else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, RuntimeError, OSError) as error:
        print('RESTORE_BLOCKED: ' + str(error), file=sys.stderr, flush=True)
        raise SystemExit(2)
