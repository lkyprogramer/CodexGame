"""Audit the gather TU, its baseline dispatcher, and archive symbol isolation."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import subprocess

BASE = set('add and call cmovns cmp imul jg jge jle jmp jne lea leave mov movabs movsxd movzx nop pop push ret sar shr sub test xor'.split())
AVX = set('vaddps vaddss vbroadcastss vcvtdq2ps vdivss vextractf128 vmovaps vmovd vmovdqa vmovdqu vmovhlps vmovq vmovshdup vmovss vmulss vxorps vzeroupper'.split())
AVX2 = set('vextracti128 vpaddd vpand vpbroadcastd vpbroadcastq vpbroadcastw vpcmpeqb vpcmpeqd vpgatherdd vpmaddubsw vpmaddwd vpmovsxwd vpmovzxbw vpor vpshufb vpsllvd vpsubb vpxor'.split())
FMA = {'vfmadd213ps', 'vfmadd231ps'}


def classify(mnemonic, raw, operands, baseline):
    if raw == '62' or 'zmm' in operands or re.search(r'\bk[0-7]\b', operands):
        raise ValueError('WIDE_ENCODING_OR_REGISTER')
    if baseline:
        if raw in ('c4', 'c5') or mnemonic.startswith('v'):
            raise ValueError('BASELINE_ISA_LEAK')
        return 'baseline'
    if mnemonic == 'cs' and operands.endswith('nop WORD PTR [rax+rax*1+0x0]'):
        return 'padding'
    for feature, allowed in [('baseline', BASE), ('AVX', AVX), ('AVX2', AVX2), ('FMA', FMA)]:
        if mnemonic in allowed:
            return feature
    raise ValueError('UNAPPROVED_INSTRUCTION ' + mnemonic)


def audit(tree, out):
    tree, out = Path(tree).resolve(), Path(out).resolve()
    out.mkdir(exist_ok=False)
    objects = tree / 'build-lab/CMakeFiles/strata_kernels_cpu.dir/src/kernels/cpu'
    report = {}
    for name, baseline in [('lab_gu_gather.cpp.o', False), ('lab_gu_gather_dispatch.cpp.o', True)]:
        text = subprocess.check_output(['objdump','-d','-C','-w','-M','intel',str(objects/name)], text=True)
        (out / (name + '.txt')).write_text(text)
        features, mnemonics, dot_gathers = {}, {}, 0
        function = ''
        for line in text.splitlines():
            if re.match(r'^[0-9a-f]+ <', line):
                function = line
            parts = line.split('\t')
            if len(parts) < 3 or not parts[1].split() or not parts[2].split():
                continue
            ins = parts[2].split(None, 1)
            feature = classify(ins[0], parts[1].split()[0], ins[1] if len(ins)>1 else '', baseline)
            features[feature] = features.get(feature, 0) + 1
            mnemonics[ins[0]] = mnemonics.get(ins[0], 0) + 1
            if '::lab_gu_dot21(' in function and ins[0] == 'vpgatherdd':
                dot_gathers += 1
        symbols = subprocess.check_output(['nm','-C','--defined-only',str(objects/name)], text=True)
        if not baseline and ('_GLOBAL__sub_I' in symbols or re.search(r'^[0-9a-f]+ [WVwu] ',symbols,re.M) or dot_gathers == 0):
            raise ValueError('KERNEL_SYMBOL_OR_ACTUAL_GATHER')
        report[name] = {'features': features, 'mnemonics': mnemonics, 'dot_gather_instructions': dot_gathers, 'symbols': symbols}
    for name in ['src/kernels/cpu/expert_layout.cpp','src/kernels/cpu/expert.cpp','src/kernels/cpu/iq_avx512.cpp','tools/check_isa_guard.py']:
        if (tree/name).read_bytes() != subprocess.check_output(['git','-C',str(tree),'show','HEAD:'+name]):
            raise ValueError('OLD_GATE_CHANGED ' + name)
    commands = json.loads((tree/'build-lab/compile_commands.json').read_text())
    command = next(x['command'] for x in commands if x['file'].endswith('/lab_gu_gather.cpp'))
    flags = shlex.split(command)
    required = ['-mavx2','-mfma','-mf16c','-mno-avx512f','-mno-avx512vl','-mno-avx512vnni','-mno-avxvnni','-fno-lto']
    if any(x not in flags for x in required) or '-march=native' in flags:
        raise ValueError('KERNEL_COMPILE_FLAGS')
    spec = importlib.util.spec_from_file_location('upstream_isa_guard', tree/'tools/check_isa_guard.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    guard.WIDE_PUBLIC = guard.WIDE_PUBLIC | {'lab_gu_dot21','lab_gu_rows21','lab_gu_lookup21','lab_gu_grid21'}
    guard.WIDE_OBJECTS = guard.WIDE_OBJECTS + ('lab_gu_gather.cpp',)
    guard.INIT_FREE_OBJECTS = guard.INIT_FREE_OBJECTS + ('lab_gu_gather.cpp',)
    original = tree.parent / 'v027-20261028'
    archive_logs, archive_codes = {}, {}
    for label, source in [('p6', original), ('candidate', tree)]:
        log = io.StringIO()
        with contextlib.redirect_stdout(log):
            archive_codes[label] = guard.run_elf(str(source/'build-lab/libstrata_kernels_cpu.a'))
        archive_logs[label] = log.getvalue()
        (out/(label+'-archive-guard.log')).write_text(log.getvalue())
    violations = {k: [x for x in v.splitlines() if x.startswith('  VIOLATION ')] for k,v in archive_logs.items()}
    if violations['candidate'] != violations['p6'] or archive_codes['candidate'] != archive_codes['p6']:
        raise ValueError('NEW_ARCHIVE_ISA_VIOLATION')
    if violations['p6']:
        if len(violations['p6']) != 2 or not all('iq_avx512.cpp.o' in x for x in violations['p6']):
            raise ValueError('UNEXPECTED_BASELINE_ISA_VIOLATION')
        relative = 'build-lab/CMakeFiles/strata_kernels_cpu.dir/src/kernels/cpu/iq_avx512.cpp.o'
        hashes = [hashlib.sha256((source/relative).read_bytes()).hexdigest() for source in [original, tree]]
        if hashes[0] != hashes[1]:
            raise ValueError('BASELINE_WIDE_OBJECT_CHANGED')
        report['unchanged_wide_object_sha256'] = hashes[0]
    report['archive_guard'] = {'state': 'NO_NEW_VIOLATIONS', 'raw_exit_codes': archive_codes, 'baseline_violations': violations['p6']}
    report.update(state='PASS', compile_command=command, old_isa_gates_unchanged=True)
    (out/'ISA_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('tree');p.add_argument('out');a=p.parse_args()
    print(json.dumps({'state':audit(a.tree,a.out)['state']}))
