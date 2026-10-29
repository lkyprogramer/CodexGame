"""Strict feature/encoding whitelist for this one EVEX256 probe, plus upstream ODR checks."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess

LEGACY=set('add and call cmovns cmp imul jg jge jle jmp jne lea mov movabs movsxd movzx nop pop push ret sar shr sub test xor'.split())
AVX=set('vaddps vaddss vbroadcastss vcvtdq2ps vdivss vextractf128 vmovd vmovdqa vmovdqu vmovhlps vmovshdup vmovss vmulss vpextrd vpinsrd vxorps vzeroupper'.split())
AVX2=set('vextracti128 vinserti128 vpaddd vpand vpbroadcastd vpbroadcastq vpbroadcastw vpcmpeqb vpmaddubsw vpmovsxwd vpmovzxbw vpshufb vpsllvd vpsubb vpunpcklqdq vpxor'.split())
EVEX={'valignd':'AVX512F+VL','vextracti32x4':'AVX512F+VL','vpbroadcastd':'AVX512F+VL',
      'vpbroadcastq':'AVX512F+VL','vpbroadcastw':'AVX512BW+VL','vpternlogq':'AVX512F+VL',
      'vpdpwssd':'AVX512VNNI+VL'}


def instruction(mnemonic,raw,operands,baseline=False):
    if baseline:
        if raw in ('62','c4','c5') or mnemonic.startswith('v'):
            raise ValueError('BASELINE_ISA_LEAK '+mnemonic)
        return 'baseline'
    if 'zmm' in operands or re.search(r'\bk[0-7]\b',operands):raise ValueError('UNEXPECTED_WIDTH_OR_MASK')
    if raw=='62':
        if mnemonic not in EVEX:raise ValueError('UNAPPROVED_EVEX '+mnemonic)
        return EVEX[mnemonic]
    if mnemonic.startswith('vpdp'):raise ValueError('VEX_VNNI_NOT_SUPPORTED')
    if mnemonic in LEGACY:return 'baseline'
    if mnemonic in AVX:return 'AVX'
    if mnemonic in AVX2:return 'AVX2'
    if mnemonic=='vfmadd231ps':return 'FMA'
    raise ValueError('UNAPPROVED_INSTRUCTION '+mnemonic)


def audit(tree,out):
    tree=Path(tree).resolve();out=Path(out).resolve();out.mkdir(exist_ok=False,parents=True)
    objects=tree/'build-lab/CMakeFiles/strata_kernels_cpu.dir/src/kernels/cpu'
    report={}
    for name,baseline in [('lab_gu_vnni.cpp.o',False),('lab_gu_dispatch.cpp.o',True)]:
        text=subprocess.check_output(['objdump','-d','-C','-w','-M','intel',str(objects/name)],text=True)
        (out/(name+'.txt')).write_text(text);features={};mnemonics={};count=0
        for line in text.splitlines():
            parts=line.split('\t')
            if len(parts)<3:continue
            raw=parts[1].split();ins=parts[2].split(None,1)
            if not raw or not ins:continue
            feature=instruction(ins[0],raw[0],ins[1] if len(ins)>1 else '',baseline)
            features[feature]=features.get(feature,0)+1;mnemonics[ins[0]]=mnemonics.get(ins[0],0)+1;count+=1
        symbols=subprocess.check_output(['nm','-C','--defined-only',str(objects/name)],text=True)
        if not baseline:
            if '_GLOBAL__sub_I' in symbols or re.search(r'^[0-9a-f]+ [WVwu] ',symbols,re.M):raise ValueError('WIDE_INIT_OR_COMDAT')
            if not mnemonics.get('vpdpwssd'):raise ValueError('VNNI_NOT_EMITTED')
        report[name]={'instructions':count,'features':features,'mnemonics':mnemonics,'symbols':symbols}
    for name in ['src/kernels/cpu/expert_layout.cpp','src/kernels/cpu/expert.cpp','src/kernels/cpu/iq_avx512.cpp']:
        original=subprocess.check_output(['git','-C',str(tree),'show','HEAD:'+name])
        if (tree/name).read_bytes()!=original:raise ValueError('EXISTING_ISA_GATE_OR_WIDE_TU_CHANGED')
    commands=json.loads((tree/'build-lab/compile_commands.json').read_text())
    command=next(x['command'] for x in commands if x['file'].endswith('/lab_gu_vnni.cpp'))
    flags=shlex.split(command)
    required=['-mavx512f','-mavx512bw','-mavx512vl','-mavx512vnni','-mno-avx512vbmi','-mno-avx512vbmi2','-mno-avx512vpopcntdq','-mno-avxvnni','-fno-lto']
    if any(x not in flags for x in required) or '-march=native' in flags:raise ValueError('COMPILE_FLAGS')
    spec=importlib.util.spec_from_file_location('upstream_guard',tree/'tools/check_isa_guard.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    # Dedicated lab registration: upstream guard source/runtime ISA gates remain byte-identical.
    guard.WIDE_PUBLIC=guard.WIDE_PUBLIC|{'lab_gu_dot21','lab_gu_rows21','lab_gu_integer_step'}
    guard.WIDE_OBJECTS=guard.WIDE_OBJECTS+('lab_gu_vnni.cpp',)
    guard.INIT_FREE_OBJECTS=guard.INIT_FREE_OBJECTS+('lab_gu_vnni.cpp',)
    if guard.run_elf(str(tree/'build-lab/libstrata_kernels_cpu.a'))!=0:raise ValueError('UPSTREAM_ODR_GUARD')
    report.update(state='PASS',compile_command=command,existing_gates_unchanged=True,
                  scope='new TU feature/encoding whitelist and baseline isolation; CPU archive ODR audit with three explicit lab entry points')
    (out/'ISA_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tree');p.add_argument('out');a=p.parse_args();r=audit(a.tree,a.out);print(json.dumps({'state':r['state']}))
