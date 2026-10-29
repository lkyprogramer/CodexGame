// Experimental IQ3_S nt=1 integer-fusion probe; no production ISA gate is changed.
#pragma once
#include "strata/kernels/cpu/native_expert.hpp"
#include <cstdint>
namespace strata::kernels::cpu {
bool lab_gu_vnni_supported();
bool lab_gu_vnni_enabled();
void lab_gu_set_mode(bool enabled);
uint64_t lab_gu_hits(); // Read only while the pool is parked.
void lab_gu_hit();
float lab_gu_dot21(int n, const uint8_t* weight, const void* activation);
void lab_gu_rows21(const NativeFmt&, const uint8_t* blob, const void* activation, float* ff, int r0, int r1);
void lab_gu_integer_step(const int16_t* values, const int16_t* scales, const int32_t* acc, int32_t* out);
} // namespace strata::kernels::cpu
