"""Audited live multi-turn supplement to the fixed KVRES combination replay.

Both arms run the same reviewed service tree and native binary. Only KV residency
changes. Generated histories intentionally diverge: this is a task-completion
screen, not a fixed-token speed comparison or a quality noninferiority proof.
Model-generated Python is scored only by the existing isolated Docker grader.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from lab import http
from lab.assets import verify as verify_assets
from lab.core import check_budget, dump, gpu_lock, hash_obj, load_config, sha256
from lab.runner import audited_chat, evidence_lifecycle, make_run_config, validate_counter
from lab.tokenizer import StrataCounter


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chain = load_module('strata_frozen_chain', ROOT / 'tools/session/chain_bench.py')


class TaskFailure(RuntimeError):
    """A valid budget/context failure; retain it and run the remaining paired arms."""


def request_for_turn(messages, requirement, seed, counter, c):
    """Freeze one actual history and fit output using the real rendered prompt."""
    body = {
        'model': 'strata',
        'messages': copy.deepcopy(messages) + [{'role': 'user', 'content': requirement + chain.FORMAT}],
        'max_tokens': 32768,
        'temperature': 1.0,
        'top_p': 0.95,
        'top_k': 20,
        'reasoning_effort': 'xhigh',
        'seed': seed,
    }
    count = counter(body)
    body['max_tokens'] = min(32768, c['max_context'] - c['safety_tokens'] - count)
    if body['max_tokens'] < 1024:
        raise TaskFailure('CONTEXT_LIMIT: less than 1024 output tokens remain for the next chain turn')
    check_budget(count, body['max_tokens'], c['max_context'], c['safety_tokens'])
    return body, count


def score_response(response, upto, image):
    """Run trusted tests in Docker; the host never imports model output."""
    if response.get('error'):
        return {'pass': False, 'passed': [False] * upto, 'reason': response['error'], 'graded': False}
    if response.get('finish_reason') != 'stop' or response.get('tools'):
        return {'pass': False, 'passed': [False] * upto,
                'reason': 'truncated response or unexpected tool output', 'graded': False}
    blocks = re.findall(r'```python\s*\n(.*?)```', response.get('text') or '', re.S)
    if len(blocks) != 1:
        return {'pass': False, 'passed': [False] * upto,
                'reason': 'expected exactly one complete Python module', 'graded': False}
    passed = chain.grade(blocks[0], upto, image)
    if not isinstance(passed, list) or len(passed) != upto or any(type(x) is not bool for x in passed):
        raise RuntimeError('GRADER_NOT_AUDITABLE: isolated grader did not return one boolean per requirement')
    return {'pass': all(passed), 'passed': passed, 'reason': 'isolated requirements 1..turn', 'graded': True}


def append_record(path, record):
    with Path(path).open('a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
        f.flush()
        os.fsync(f.fileno())


def summarize_chain(rows, elapsed_s, task_budget_s, expected_turns=8, error=None):
    complete = len(rows) == expected_turns and all(x.get('score', {}).get('pass') is True for x in rows)
    complete = complete and elapsed_s <= task_budget_s and error is None
    return {
        'turns_recorded': len(rows),
        'expected_turns': expected_turns,
        'successful_turns': sum(x.get('score', {}).get('pass') is True for x in rows),
        'task_success': complete,
        'error': error,
        'task_elapsed_s': elapsed_s,
        'task_budget_s': task_budget_s,
        'restricted_time_to_success_s': elapsed_s if complete else task_budget_s,
        'inference_wall_s': sum(x.get('metrics', {}).get('wall_s') or 0 for x in rows),
        'grading_wall_s': sum(x.get('grading_wall_s') or 0 for x in rows),
        'scope': 'one evolving generated-history Python task; no fixed-output throughput or formal NI claim',
    }


def one_chain(c, tree, arm, ready, folder, pair, seed, image, task_budget_s, combo):
    folder = Path(folder)
    rows = []
    messages = [{'role': 'system', 'content': chain.SYSTEM}]
    counter = StrataCounter(tree, c['gguf'], c['template'])
    with combo.combination_server(c, tree, arm, ready, folder) as server:
        validate_counter(counter, server)
        combo.history_counter_probe(server, counter, c, folder)
        dump(folder / 'activation.json', combo.validate_startup(server, arm))
        started = time.perf_counter()
        chain_error = None
        try:
            for turn, requirement in enumerate(chain.REQS):
                body, count = request_for_turn(messages, requirement, seed, counter, c)
                # The existing grader caps each test at 60s, its outer command
                # at 60*upto+60s and exact-container cleanup at another 30s.
                grade_bound_s = 60 * (turn + 1) + 90
                remaining = task_budget_s - (time.perf_counter() - started)
                if remaining <= grade_bound_s + 1:
                    raise TaskFailure('TASK_BUDGET: insufficient remaining budget for generation and isolated grading')
                request_c = dict(c, request_timeout_s=min(c['request_timeout_s'], remaining - grade_bound_s))
                dump(folder / f'turn-{turn:02d}.request.json', body)
                response = audited_chat(server, counter, request_c, body)
                dump(folder / f'turn-{turn:02d}.response.json', response)
                grading_started = time.perf_counter()
                grader_error = None
                try:
                    score = score_response(response, turn + 1, image)
                except Exception as error:
                    grader_error = error
                    score = {'pass': False, 'passed': None, 'graded': False,
                             'reason': 'GRADER_INFRASTRUCTURE: ' + str(error)}
                grading_wall_s = time.perf_counter() - grading_started
                row = {
                    'pair': pair, 'arm': arm, 'turn': turn, 'seed': seed,
                    'request_sha256': hash_obj(body), 'request_file': f'turn-{turn:02d}.request.json',
                    'response_file': f'turn-{turn:02d}.response.json',
                    'local_prompt_tokens': count, 'max_tokens': body['max_tokens'],
                    'metrics': http.measurements(response), 'score': score,
                    'grading_wall_s': grading_wall_s,
                    'memory_after': combo.resource_sample(server),
                    'error': response.get('error'), 'finish_reason': response.get('finish_reason'),
                }
                rows.append(row)
                append_record(folder / 'requests.jsonl', row)
                print(json.dumps({'pair': pair, 'arm': arm, 'turn': turn, 'score': score,
                                  'metrics': row['metrics']}, ensure_ascii=False), flush=True)
                if response.get('error') or server.abort_reason:
                    raise RuntimeError('CHAIN_INFRASTRUCTURE: ' + str(response.get('error') or server.abort_reason))
                if grader_error is not None:
                    raise RuntimeError('CHAIN_GRADER_INFRASTRUCTURE: ' + str(grader_error)) from grader_error
                messages = copy.deepcopy(body['messages'])
                assistant = {'role': 'assistant', 'content': response.get('text') or ''}
                if response.get('reasoning'):
                    assistant['reasoning_content'] = response['reasoning']
                messages.append(assistant)
                dump(folder / 'messages.json', messages)
        except TaskFailure as error:
            chain_error = str(error)
        except BaseException as error:
            chain_error = str(error)
            raise
        finally:
            elapsed = time.perf_counter() - started
            summary = summarize_chain(rows, elapsed, task_budget_s, len(chain.REQS), chain_error)
            dump(folder / 'chain.json', {'pair': pair, 'arm': arm, 'seed': seed,
                                         'grader_image': image, 'rows': rows, 'summary': summary,
                                         'abort': server.abort_reason})
    return summary


def run(config_path, tree, out, pairs, image, task_budget_s, execute=False):
    if type(pairs) is not int or pairs < 1:
        raise ValueError('pairs must be a positive integer fixed before execution')
    if isinstance(task_budget_s, bool) or not math.isfinite(task_budget_s) or task_budget_s <= 0:
        raise ValueError('task budget must be a positive finite number')
    tree, out = Path(tree).resolve(), Path(out).resolve()
    c = load_config(config_path)
    combo = load_module('strata_combo_runtime', Path(__file__).with_name('run_combo.py'))
    if int(c['port']) != 18089 or c['max_context'] != 131072:
        raise ValueError('Chain validation is fixed to lab port 18089 and total context 131072')
    if c['min_available_mib'] < 4096 or c.get('gpu_temp_abort_c', 85) > 85:
        raise ValueError('Do not weaken RAM or thermal protection')
    if Path(c['deployed_repo']).resolve() != tree or c.get('request_overrides'):
        raise ValueError('Use the isolated combination tree without request overrides')
    build = combo.validate_tree(tree)
    ready = combo.ready_spec()
    prepared = {arm: make_run_config(c, tree, arm, ready, out / ('prepared-' + arm))
                for arm in ('base', 'cfg')}
    combo.assert_same_except_kvres(prepared['base'], prepared['cfg'])
    if any(Path(x.get('cwd', '')).resolve() != tree for x in prepared.values()):
        raise ValueError('Engine cwd must be the isolated combination tree')
    plan = {
        'schema_version': 1, 'mode': 'LIVE_CHAIN', 'arms': ['base', 'cfg'],
        'kv_resident': {'base': 0, 'cfg': 20480}, 'pairs': pairs,
        'order': [['base', 'cfg'] if n % 2 == 0 else ['cfg', 'base'] for n in range(pairs)],
        'seeds': [42 + n for n in range(pairs)], 'source': build,
        'requirements': chain.REQS, 'format': chain.FORMAT, 'system': chain.SYSTEM,
        'requirements_sha256': hash_obj(chain.REQS), 'tests_sha256': hash_obj(chain.TESTS),
        'grader_source_sha256': sha256(ROOT / 'tools/session/chain_bench.py'),
        'grader_driver_sha256': hash_obj(chain.DRIVER), 'image_requested': image,
        'task_budget_s': task_budget_s, 'request_max_tokens': 32768,
        'sampling': {'temperature': 1.0, 'top_p': 0.95, 'top_k': 20, 'reasoning_effort': 'xhigh'},
        'counter': 'same service tree and PT=0; exact rendered tokens, qualified against live usage',
        'scope': 'small generated-history task-completion screen; not formal 2pp NI or fixed-output performance',
    }
    if not execute:
        return {'state': 'DRY_RUN', 'plan': plan}
    out.mkdir(parents=True, exist_ok=False)
    protected = combo.protected_hashes(c)
    dump(out / 'protected-before.json', protected)
    combo.assert_service_inactive()
    img = chain.image_id(image)
    plan['grader_image'] = img
    plan['plan_sha256'] = hash_obj(plan)
    dump(out / 'campaign.json', plan)
    dump(out / 'assets.json', verify_assets(c))
    dump(out / 'production-before.json', combo.assert_service_inactive())
    os.environ.update(STRATA_PRESERVE_THINKING='0', STRATA_REPLY_REUSE='1')
    summaries = []
    with gpu_lock(c.get('gpu_lock_workspace', c['workspace'])):
        with evidence_lifecycle(c, out):
            try:
                for pair in range(pairs):
                    for arm in plan['order'][pair]:
                        combo.assert_service_inactive()
                        combo.assert_protected(c, protected)
                        if combo.validate_tree(tree) != build:
                            raise RuntimeError('BUILD_RECEIPT_CHANGED')
                        cooldown = combo.wait_cool(c)
                        folder = out / f'pair-{pair:02d}-{arm}'
                        folder.mkdir(parents=True, exist_ok=False)
                        dump(folder / 'cooldown.json', cooldown)
                        result = one_chain(c, tree, arm, ready, folder, pair, plan['seeds'][pair],
                                           img, task_budget_s, combo)
                        summaries.append({'pair': pair, 'arm': arm, **result})
                        dump(out / 'summary.json', {'pairs_planned': pairs, 'chains': summaries,
                                                    'formal_noninferiority': 'NOT_ESTABLISHED'})
            finally:
                dump(out / 'protected-after.json', combo.assert_protected(c, protected))
                dump(out / 'production-after.json', combo.assert_service_inactive())
    return {'state': 'COMPLETE', 'results': str(out), 'chains': summaries,
            'formal_noninferiority': 'NOT_ESTABLISHED'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--pairs', type=int, default=2)
    parser.add_argument('--image', required=True, help='existing local Docker image; never pulled')
    parser.add_argument('--task-budget-s', type=float, default=2400)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    result = run(args.config, args.tree, args.out, args.pairs, args.image,
                 args.task_budget_s, args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if any(not x['task_success'] for x in result.get('chains', [])) else 0


if __name__ == '__main__':
    raise SystemExit(main())
