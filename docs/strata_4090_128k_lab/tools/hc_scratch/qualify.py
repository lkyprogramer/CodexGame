"""P13 same-token native qualification; all timings here are diagnostic only."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools/v027'), str(Path(__file__).parent)]
import prepare
import run_reference_logits as reference
from lab.core import dump, gpu_inventory, gpu_lock, load_config, sha256
from lab.runner import make_run_config, wait_released


def run(variant, name, case_name, diagnostic=False, dump_stage=None, startup_only=False):
    task = prepare.TASK
    receipt = json.loads((task / 'REGISTRATION_RECEIPT.json').read_text())
    if receipt['sha256'] != sha256(task / 'PREREGISTRATION.json'):
        raise RuntimeError('REGISTRATION_DRIFT')
    c = load_config((prepare.P6 if variant == 'P6' else task) / 'config.json')
    source = reference.baseline.source_receipt(Path(load_config(prepare.P6 / 'config.json')['deployed_repo']), prepare.P6)
    before = json.loads((task / 'production-before.json').read_text())
    reference.baseline.combo.assert_service_inactive()
    reference.baseline.combo.assert_protected(c, before['file_sha256'])
    folder = task / name
    folder.mkdir(exist_ok=False)
    tokens = json.loads((task / 'tokens.json').read_text())
    if (task / 'numerical-fixtures.json').exists():
        tokens += json.loads((task / 'numerical-fixtures.json').read_text())['fixtures']
    selected = next(x for x in tokens if x['name'] == case_name)
    if sha256(Path(selected['path'])) != selected['sha256']:
        raise RuntimeError('TOKEN_DRIFT')
    prefix = folder / 'empty-prefix.ids'
    prefix.write_text('\n')
    case = {'name': case_name, 'tokens': selected, 'prefix': {'path': str(prefix)}}
    c['extra_frozen_env'].update(STRATA_LAB_HC_REGION='1' if variant in ('B', 'C') else '0',
         STRATA_LAB_HC_KEEP_LOAN='1' if variant == 'B' else '0', STRATA_LAB_HC_MANIFEST='1')
    if diagnostic:
        (folder / 'diag').mkdir()
        c['extra_frozen_env'].update(STRATA_LAB_HC_DIAG_DIR=str(folder / 'diag'), STRATA_DBG_CPU_GATE='1')
        if dump_stage:
            c['extra_frozen_env']['STRATA_LAB_HC_DIAG_DUMP'] = dump_stage
    cfg = make_run_config(c, Path(c['deployed_repo']), 'cfg', {}, folder)
    for key, value in {**reference.baseline.CONSERVATIVE, **reference.baseline.combo.FROZEN_ENV}.items():
        if cfg['env'].get(key) != value:
            raise RuntimeError('FROZEN_ENV_DRIFT: ' + key)
    reference.baseline.assert_kvres(cfg)
    dump(folder / 'plan.json', {'started_utc': datetime.now(timezone.utc).isoformat(), 'preregistration_sha256': receipt['sha256'],
         'variant': variant, 'tokens': selected, 'exe_sha256': sha256(Path(cfg['exe'])), 'args': cfg['args'],
         'strata_env': {k: v for k, v in cfg['env'].items() if k.startswith('STRATA_')},
         'same_tokens_and_initial_state': 'fresh engine configuration; valid state identity requires separate checkpoints',
         'native_requests': 0 if startup_only else 1, 'P6_source': source})
    try:
        with gpu_lock(c['gpu_lock_workspace']):
            dump(folder / 'cooldown.json', reference.baseline.combo.wait_cool(c))
            reference.run_native(c, folder, [] if startup_only else [case])
            wait_released(c)
        dump(folder / 'COMPLETION.json', {'state': 'COMPLETE', 'variant': variant,
             'native_requests': 0 if startup_only else 1,
             'logits_sha256': None if startup_only else sha256(folder / (case_name + '.f32')),
             'original_six_status': 'FAIL_UNCHANGED', 'performance_sample': False})
    except BaseException as error:
        dump(folder / 'FAILURE.json', {'error': str(error), 'partial_files_preserved': True})
        raise
    finally:
        dump(folder / 'production-after.json', {'service': reference.baseline.combo.assert_service_inactive(),
             'file_sha256': reference.baseline.combo.assert_protected(c, before['file_sha256']), 'gpu': gpu_inventory('0')})
    return json.loads((folder / 'COMPLETION.json').read_text())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', required=True, choices=['P6', 'A', 'B', 'C'])
    parser.add_argument('--name', required=True)
    parser.add_argument('--case', default='think-4096')
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--dump-stage')
    parser.add_argument('--startup-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.variant, args.name, args.case, args.diagnostic, args.dump_stage, args.startup_only)), flush=True)
