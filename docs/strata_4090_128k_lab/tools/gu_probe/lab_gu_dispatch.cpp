// Baseline-ISA capability/selection code, separated from the EVEX-256 translation unit.
#include "lab_gu_kernel.hpp"
#include "strata/kernels/cpu/expert_layout.hpp"
#include <atomic>
#include <cpuid.h>
#include <cstdlib>

namespace strata::kernels::cpu {
namespace {
std::atomic<int> mode{-1};
struct alignas(64) HitCounter { uint64_t value=0; };
HitCounter hits[128];
std::atomic<unsigned> slots{0};
}
bool lab_gu_vnni_supported() {
    if (!cpu_avx2_ok() || cpu_isa_cap()<3) return false;
    if (const char* e=std::getenv("STRATA_FORCE_AVX2");e && e[0]=='1') return false;
    unsigned a,b,c,d;
    if (__get_cpuid_max(0,nullptr)<7) return false;
    __cpuid_count(1,0,a,b,c,d);
    if (!(c&(1u<<27))) return false;
    unsigned lo,hi;__asm__ volatile("xgetbv":"=a"(lo),"=d"(hi):"c"(0));
    if ((lo&0xE6)!=0xE6) return false;
    __cpuid_count(7,0,a,b,c,d);
    return (b&(1u<<16)) && (b&(1u<<30)) && (b&(1u<<31)) && (c&(1u<<11));
}
bool lab_gu_vnni_enabled() {
    static const bool requested=[] {const char* e=std::getenv("STRATA_LAB_GU_VNNI");return e && e[0]=='1' && !e[1];}();
    const int test=mode.load(std::memory_order_relaxed);
    static const bool supported=lab_gu_vnni_supported();
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
