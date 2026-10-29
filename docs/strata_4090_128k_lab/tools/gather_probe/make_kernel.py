"""Build the default-off IQ3_S nt=1 probe from the actual ggml AVX2 oracle.

The only change in the dot body is scalar codebook assembly -> two AVX2
gathers.  The existing P5 replay harness supplies the real-fixture and complete
ExpertPool checks; its integer-fusion check is replaced by lookup parity.
"""
import argparse
import hashlib
import json
from pathlib import Path


OLD_LOOKUP = """            // At leat on my CPU (Ryzen 7950X), using _mm256_i32gather_epi32 is slower than _mm256_set_epi32. Strange.
            //const __m256i q2_1 = _mm256_i32gather_epi32((const int *)iq3s_grid, idx.vec[0], 4);
            //const __m256i q2_2 = _mm256_i32gather_epi32((const int *)iq3s_grid, idx.vec[1], 4);
            const __m256i q2_1 = _mm256_set_epi32(
                    iq3s_grid[idx.index[7]], iq3s_grid[idx.index[6]], iq3s_grid[idx.index[5]], iq3s_grid[idx.index[4]],
                    iq3s_grid[idx.index[3]], iq3s_grid[idx.index[2]], iq3s_grid[idx.index[1]], iq3s_grid[idx.index[0]]
            );
            const __m256i q2_2 = _mm256_set_epi32(
                    iq3s_grid[idx.index[15]], iq3s_grid[idx.index[14]], iq3s_grid[idx.index[13]], iq3s_grid[idx.index[12]],
                    iq3s_grid[idx.index[11]], iq3s_grid[idx.index[10]], iq3s_grid[idx.index[ 9]], iq3s_grid[idx.index[ 8]]
            );"""
NEW_LOOKUP = """            const __m256i q2_1 = _mm256_i32gather_epi32((const int *)iq3s_grid, idx.vec[0], 4);
            const __m256i q2_2 = _mm256_i32gather_epi32((const int *)iq3s_grid, idx.vec[1], 4);"""


def replace_once(text, before, after):
    count = text.count(before)
    if count != 1:
        raise ValueError(f"GATHER_ANCHOR_COUNT {count}: {before[:80]}")
    return text.replace(before, after)


def oracle_parts(source):
    signature = "void ggml_vec_dot_iq3_s_q8_K("
    if source.count(signature) != 1:
        raise ValueError("GATHER_ORACLE_FUNCTION_COUNT")
    start = source.index(signature)
    end = source.index("#elif defined(__AVX__)", start)
    oracle = source[start:end]
    if oracle.count("#if defined(__AVX2__)") != 1:
        raise ValueError("GATHER_ORACLE_AVX2_BRANCH")
    body = oracle[oracle.index("    const block_iq3_s"):]
    body = replace_once(body, "#if defined(__AVX2__)", "")
    body = replace_once(body, "x = vx;", "x = reinterpret_cast<const block_iq3_s*>(vx);")
    body = replace_once(body, "y = vy;", "y = reinterpret_cast<const block_q8_K*>(vy);")
    body = replace_once(body, OLD_LOOKUP, NEW_LOOKUP)
    body = replace_once(body, "    *s = hsum_float_8(accumf);", "    return hsum_float_8(accumf);")
    # Keep the oracle's exact final reduction instead of writing another one.
    start = source.index("static inline float hsum_float_8(")
    end = source.index("\n}", start) + 2
    return oracle, body, source[start:end]


HEADER = """// Experimental IQ3_S nt=1 codebook gather; existing ISA gates stay intact.
#pragma once
#include "strata/kernels/cpu/native_expert.hpp"
#include <cstdint>
namespace strata::kernels::cpu {
bool lab_gu_gather_supported();
bool lab_gu_gather_enabled();
void lab_gu_set_mode(bool enabled);
uint64_t lab_gu_hits(); // Read only while the pool is parked.
void lab_gu_hit();
float lab_gu_dot21(int n, const uint8_t* weight, const void* activation);
void lab_gu_rows21(const NativeFmt&, const uint8_t* blob, const void* activation, float* ff, int r0, int r1);
void lab_gu_lookup21(const uint32_t* grid, const int32_t* indices, uint32_t* out);
const uint32_t* lab_gu_grid21(); // Read-only codebook for the lookup parity check.
} // namespace strata::kernels::cpu
"""

DISPATCH = """// Baseline-ISA selection; the AVX2 TU is entered only after cpu_avx2_ok().
#include "lab_gu_gather.hpp"
#include "strata/kernels/cpu/expert_layout.hpp"
#include <atomic>
#include <cstdlib>
namespace strata::kernels::cpu {
namespace {
std::atomic<int> mode{-1};
struct alignas(64) HitCounter { uint64_t value=0; };
HitCounter hits[128];
std::atomic<unsigned> slots{0};
}
bool lab_gu_gather_supported() {
    // The existing helper checks FMA/F16C, AVX2, ISA cap, OSXSAVE and XCR0.
    return cpu_avx2_ok();
}
bool lab_gu_gather_enabled() {
    static const bool requested=[] {
        const char* e=std::getenv("STRATA_LAB_GU_GATHER");
        return e && e[0]=='1' && !e[1];
    }();
    const int test=mode.load(std::memory_order_relaxed);
    static const bool supported=lab_gu_gather_supported();
    return (test<0 ? requested : test!=0) && supported;
}
void lab_gu_set_mode(bool enabled) {mode.store(enabled?1:0,std::memory_order_relaxed);}
void lab_gu_hit() {
    thread_local unsigned slot=slots.fetch_add(1,std::memory_order_relaxed);
    if (slot>=128) std::abort();
    ++hits[slot].value;
}
uint64_t lab_gu_hits() {
    uint64_t sum=0;
    for (unsigned i=0;i<slots.load(std::memory_order_relaxed);++i) sum+=hits[i].value;
    return sum;
}
} // namespace strata::kernels::cpu
"""

LOOKUP_PARITY = """static void lookup_parity() {
    std::mt19937 random(42);const uint32_t* grid=lab_gu_grid21();
    alignas(32) int32_t indices[8];alignas(32) uint32_t reference[8],candidate[8];
    for(int i=0;i<100000;++i) {
        // The first 512 vectors cover every legal codebook index and both ends.
        for(int j=0;j<8;++j)indices[j]=i<512?(i+j)%512:(int32_t)(random()&511);
        if(i==512) {const int32_t edge[8]={0,511,0,511,511,0,511,0};std::memcpy(indices,edge,sizeof indices);}
        if(i==513) {const int32_t edge[8]={511,256,1,0,255,510,128,127};std::memcpy(indices,edge,sizeof indices);}
        for(int j=0;j<8;++j)reference[j]=grid[indices[j]];
        lab_gu_lookup21(grid,indices,candidate);
        equal(reference,candidate,sizeof reference,"codebook-lookup");
    }
}
"""

CMAKE = """
# Experiment-only IQ3_S nt=1 AVX2 codebook gather. Default off; old ISA gates unchanged.
target_sources(strata_kernels_cpu PRIVATE src/kernels/cpu/lab_gu_gather_dispatch.cpp src/kernels/cpu/lab_gu_gather.cpp)
set_property(SOURCE src/kernels/cpu/lab_gu_gather.cpp APPEND PROPERTY INCLUDE_DIRECTORIES
    "${STRATA_GGML_DIR}/ggml/src/ggml-cpu;${STRATA_GGML_DIR}/ggml/src")
set_source_files_properties(src/kernels/cpu/lab_gu_gather.cpp PROPERTIES COMPILE_OPTIONS
    "-mavx2;-mfma;-mf16c;-mno-avx512f;-mno-avx512vl;-mno-avx512vnni;-mno-avxvnni;-fno-lto")
set_property(SOURCE src/kernels/cpu/lab_gu_gather.cpp APPEND PROPERTY COMPILE_DEFINITIONS
    $<$<BOOL:${LAB_GU_GATHER_RED_STUB}>:LAB_GU_GATHER_RED_STUB>)
add_executable(lab_gu_probe src/kernels/cpu/lab_gu_gather_probe.cpp)
target_include_directories(lab_gu_probe PRIVATE src/kernels/cpu third_party/ggml)
target_compile_options(lab_gu_probe PRIVATE -mavx2 -mfma -mf16c)
target_link_libraries(lab_gu_probe PRIVATE strata_kernels_cpu)
"""


def kernel_source(body, reduction):
    return """// Derived from the frozen actual ggml IQ3_S AVX2 oracle.
// Only the two codebook loads differ; integer and floating-point arithmetic retain their order.
#include "lab_gu_gather.hpp"
#include "ggml.h"
#define GGML_COMMON_DECL_CPP
#define GGML_COMMON_IMPL_CPP
#include "ggml-common.h"
#include "simd-mappings.h"
#include <immintrin.h>
#include <cassert>
#include <cmath>
namespace strata::kernels::cpu {
""" + reduction + """
float lab_gu_dot21(int n,const uint8_t* vx,const void* vy) {
#ifdef LAB_GU_GATHER_RED_STUB
    return 0.0f;
#endif
    assert(n%QK_K==0);
""" + body + """
}
void lab_gu_rows21(const NativeFmt& f,const uint8_t* blob,const void* act,float* ff,int r0,int r1) {
    for(int r=r0;r<r1;++r) {
        const float g=lab_gu_dot21((int)f.n_embd,blob+(size_t)r*f.gu_row,act);
        const float u=lab_gu_dot21((int)f.n_embd,blob+f.up_off+(size_t)r*f.gu_row,act);
        ff[r]=(g/(1.f+std::exp(-g)))*u;
    }
}
void lab_gu_lookup21(const uint32_t* grid,const int32_t* indices,uint32_t* out) {
    const __m256i values=_mm256_i32gather_epi32((const int*)grid,
        _mm256_loadu_si256((const __m256i*)indices),4);
    _mm256_storeu_si256((__m256i*)out,values);
}
const uint32_t* lab_gu_grid21() { return iq3s_grid; }
} // namespace strata::kernels::cpu
"""


def harness_source(template):
    text = replace_once(template, '#include "lab_gu_kernel.hpp"', '#include "lab_gu_gather.hpp"')
    text = text.replace("lab_gu_vnni_supported", "lab_gu_gather_supported")
    text = text.replace("lab_gu_vnni_enabled", "lab_gu_gather_enabled")
    start = text.index("static void integer_parity() {")
    end = text.index("static void direct_parity(", start)
    text = text[:start] + LOOKUP_PARITY + text[end:]
    text = replace_once(text, "    integer_parity();size_t", "    lookup_parity();size_t")
    text = replace_once(text, '\\"integer_vectors\\":100000', '\\"lookup_vectors\\":100000')
    return text


def apply(tree, ggml):
    tree, ggml = Path(tree), Path(ggml)
    source = (ggml / "ggml/src/ggml-cpu/arch/x86/quants.c").read_text()
    oracle, body, reduction = oracle_parts(source)
    dest = tree / "src/kernels/cpu"
    native_path = dest / "native_expert.cpp"
    native = native_path.read_text()
    native = replace_once(native, '#include "lab_gu_profile.hpp"',
                          '#include "lab_gu_profile.hpp"\n#include "lab_gu_gather.hpp"')
    anchor = "    const int mt_min = native_gu_mt_min(f.gu_type);   // #152"
    native = replace_once(native, anchor, anchor + """
    if (f.gu_type==21 && nt==1 && !f.tail_off && lab_gu_gather_enabled()) {
        lab_gu_hit();
        lab_gu_rows21(f,blob,act[0],ff[0],r0,r1);
        return;
    }""")
    cmake_path = tree / "CMakeLists.txt"
    cmake = cmake_path.read_text()
    if "lab_gu_probe" in cmake or "lab_gu_gather" in cmake:
        raise ValueError("GATHER_BUILD_TARGET_ALREADY_EXISTS")
    template = Path(__file__).parents[1] / "gu_probe/gu_probe.cpp"
    generated = {
        dest / "lab_gu_gather.hpp": HEADER,
        dest / "lab_gu_gather_dispatch.cpp": DISPATCH,
        dest / "lab_gu_gather.cpp": kernel_source(body, reduction),
        dest / "lab_gu_gather_probe.cpp": harness_source(template.read_text()),
        tree / "lab-gu-gather-oracle-avx2.txt": oracle,
    }
    # Validate every anchor and destination before changing the experiment tree.
    for path in generated:
        if path.exists():
            raise ValueError(f"GATHER_OUTPUT_ALREADY_EXISTS: {path}")
    writes = {native_path: native, cmake_path: cmake + CMAKE, **generated}
    for path, content in writes.items():
        path.write_text(content)
    return {
        "mechanism": "IQ3_S nt1 scalar codebook loads to AVX2 gather only",
        "oracle_sha256": hashlib.sha256(oracle.encode()).hexdigest(),
        "files": {str(path.relative_to(tree)): hashlib.sha256(content.encode()).hexdigest()
                  for path, content in writes.items()},
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("tree")
    parser.add_argument("ggml")
    args = parser.parse_args()
    print(json.dumps(apply(args.tree, args.ggml), indent=2))
