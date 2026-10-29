"""Derive one IQ3_S kernel from the actual ggml oracle, changing only integer madd+add."""
from pathlib import Path
import argparse
import shutil


def replace(s,a,b):
    if s.count(a)!=1:raise ValueError('kernel anchor count '+str(s.count(a))+' '+a[:80])
    return s.replace(a,b)


def apply(tree,ggml,kernel_only=False):
    tree=Path(tree);ggml=Path(ggml)
    source=(ggml/'ggml/src/ggml-cpu/arch/x86/quants.c').read_text()
    start=source.index('void ggml_vec_dot_iq3_s_q8_K(')
    oracle=source[start:source.index('#elif defined(__AVX__)',start)]
    body=oracle[oracle.index('    const block_iq3_s'):]
    body=body.replace('#if defined(__AVX2__)','')
    body=replace(body,'x = vx;','x = reinterpret_cast<const block_iq3_s*>(vx);')
    body=replace(body,'y = vy;','y = reinterpret_cast<const block_q8_K*>(vy);')
    old='''            const __m256i p1 = _mm256_madd_epi16(dot1, _mm256_set1_epi16(2*ls1+1));
            const __m256i p2 = _mm256_madd_epi16(dot2, _mm256_set1_epi16(2*ls2+1));
            sumi1 = _mm256_add_epi32(sumi1, p1);
            sumi2 = _mm256_add_epi32(sumi2, p2);'''
    new='''            sumi1 = _mm256_dpwssd_epi32(sumi1, dot1, _mm256_set1_epi16(2*ls1+1));
            sumi2 = _mm256_dpwssd_epi32(sumi2, dot2, _mm256_set1_epi16(2*ls2+1));'''
    body=replace(body,old,new)
    body=replace(body,'    *s = hsum_float_8(accumf);','    return hsum_float_8(accumf);')
    hs=source[source.index('static inline float hsum_float_8('):]
    hs=hs[:hs.index('\n}')+2]
    code='''// Derived from the frozen actual ggml IQ3_S oracle; original unpack and FP order retained.
// The only dot arithmetic change is madd_epi16 + add_epi32 -> non-saturating EVEX.256 dpwssd.
#include "lab_gu_kernel.hpp"
#include "ggml.h"
#define GGML_COMMON_DECL_CPP
#define GGML_COMMON_IMPL_CPP
#include "ggml-common.h"
#include "simd-mappings.h"
#include <immintrin.h>
#include <cassert>
#include <cmath>
namespace strata::kernels::cpu {
'''+hs+'''
float lab_gu_dot21(int n,const uint8_t* vx,const void* vy) {
#ifdef LAB_GU_PROBE_RED_STUB
    return 0.0f;
#endif
    assert(n%QK_K==0);
'''+body+'''
}
void lab_gu_rows21(const NativeFmt& f,const uint8_t* blob,const void* act,float* ff,int r0,int r1) {
    for(int r=r0;r<r1;++r) {
        const float g=lab_gu_dot21((int)f.n_embd,blob+(size_t)r*f.gu_row,act);
        const float u=lab_gu_dot21((int)f.n_embd,blob+f.up_off+(size_t)r*f.gu_row,act);
        ff[r]=(g/(1.f+std::exp(-g)))*u;
    }
}
void lab_gu_integer_step(const int16_t* v,const int16_t* s,const int32_t* a,int32_t* out) {
    const auto value=_mm256_dpwssd_epi32(_mm256_loadu_si256((const __m256i*)a),
         _mm256_loadu_si256((const __m256i*)v),_mm256_loadu_si256((const __m256i*)s));
    _mm256_storeu_si256((__m256i*)out,value);
}
} // namespace strata::kernels::cpu
'''
    dest=tree/'src/kernels/cpu';(dest/'lab_gu_vnni.cpp').write_text(code)
    if kernel_only:return
    for name in ['lab_gu_dispatch.cpp','lab_gu_kernel.hpp','gu_probe.cpp']:
        shutil.copy2(Path(__file__).with_name(name),dest/name)
    p=dest/'native_expert.cpp';s=p.read_text();anchor='#include "lab_gu_profile.hpp"'
    s=replace(s,anchor,anchor+'\n#include "lab_gu_kernel.hpp"')
    anchor='    const int mt_min = native_gu_mt_min(f.gu_type);   // #152'
    s=replace(s,anchor,anchor+'''
    if (f.gu_type==21 && nt==1 && !f.tail_off && lab_gu_vnni_enabled()) {
        lab_gu_hit();
        lab_gu_rows21(f,blob,act[0],ff[0],r0,r1);
        return;
    }''');p.write_text(s)
    p=tree/'CMakeLists.txt';s=p.read_text();s+='''
# Experiment-only IQ3_S nt=1 EVEX256 probe. Baseline ISA gates remain unchanged.
target_sources(strata_kernels_cpu PRIVATE src/kernels/cpu/lab_gu_dispatch.cpp src/kernels/cpu/lab_gu_vnni.cpp)
set_property(SOURCE src/kernels/cpu/lab_gu_vnni.cpp APPEND PROPERTY INCLUDE_DIRECTORIES
    "${STRATA_GGML_DIR}/ggml/src/ggml-cpu;${STRATA_GGML_DIR}/ggml/src")
set_source_files_properties(src/kernels/cpu/lab_gu_vnni.cpp PROPERTIES COMPILE_OPTIONS
    "-mavx2;-mfma;-mf16c;-mavx512f;-mavx512bw;-mavx512vl;-mavx512vnni;-mno-avx512vbmi;-mno-avx512vbmi2;-mno-avx512vpopcntdq;-mno-avxvnni;-mprefer-vector-width=256;-fno-lto")
set_property(SOURCE src/kernels/cpu/lab_gu_vnni.cpp APPEND PROPERTY COMPILE_DEFINITIONS
    $<$<BOOL:${LAB_GU_PROBE_RED_STUB}>:LAB_GU_PROBE_RED_STUB>)
add_executable(lab_gu_probe src/kernels/cpu/gu_probe.cpp)
target_include_directories(lab_gu_probe PRIVATE src/kernels/cpu third_party/ggml)
target_compile_options(lab_gu_probe PRIVATE -mavx2 -mfma -mf16c)
target_link_libraries(lab_gu_probe PRIVATE strata_kernels_cpu)
''';p.write_text(s)
    (tree/'lab-gu-oracle-avx2.txt').write_text(oracle)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tree');p.add_argument('ggml');p.add_argument('--kernel-only',action='store_true');a=p.parse_args();apply(a.tree,a.ggml,a.kernel_only)
