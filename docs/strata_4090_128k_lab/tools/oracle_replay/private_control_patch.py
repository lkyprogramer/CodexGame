"""Add a one-chunk private-HC control to the frozen P15 oracle engine."""
import hashlib

SOURCE_SHA256 = '3c478709ca21241056f5bf53621e9cee2483711adfd8b365baf3528191a32300'
ANCHOR = '        const int64_t T = std::min(C, n - c0), p0 = pos0 + c0;'
CONTROL = r'''
        // P18: hold C's loan/residency fixed while replacing only HC addresses.
        struct PrivateHC {
            decltype(m)& memory;
            uint16_t* xn16; float* lo; uint16_t* lo16; float* gated;
            std::vector<void*> owned;
            ~PrivateHC() {
                if (owned.empty()) return;
                strata_lab_full_oracle::require(cudaStreamSynchronize(memory.cs) == cudaSuccess &&
                    cudaStreamSynchronize(memory.copy) == cudaSuccess, "private HC final synchronization");
                memory.xn16 = xn16; memory.lo = lo; memory.lo16 = lo16; memory.gated = gated;
                for (void* p : owned)
                    strata_lab_full_oracle::require(cudaFree(p) == cudaSuccess, "private HC free");
            }
        } private_hc{m, m.xn16, m.lo, m.lo16, m.gated, {}};
        if (const char* control = std::getenv("STRATA_LAB_HC_PRIVATE_CONTROL"); control && control[0] == '1') {
            auto& capture = strata_lab_full_oracle::probe();
            strata_lab_full_oracle::require(capture.dir && capture.ref && lab_hc_region() && !lab_hc_keep_loan() &&
                p0 == 0 && T == 4090 && m.T == 4096 && !m.f16_io && !bf16x2_hc(m.f16_io) && !hc_pad(),
                "private HC control requires frozen C replay geometry");
            Alloc h; h.owned = &private_hc.owned; bool allocated = true;
            m.xn16 = h.take<uint16_t>((size_t) m.T * D, allocated);
            m.lo = h.take<float>((size_t) m.T * LR, allocated);
            m.lo16 = h.take<uint16_t>((size_t) m.T * LR, allocated);
            m.gated = h.take<float>((size_t) m.T * D, allocated);
            strata_lab_full_oracle::require(allocated, "private HC control allocation");
            std::fprintf(stderr, "P18_PRIVATE_HC {\"T\":%lld,\"bytes\":%llu,\"separate_allocations\":4,"
                "\"loan_unchanged\":true}\n", (long long) T, (unsigned long long) h.used);
        }
'''


def transform(source):
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256 or source.count(ANCHOR) != 1:
        raise ValueError('PRIVATE_CONTROL_SOURCE_DRIFT')
    return source.replace(ANCHOR, ANCHOR + CONTROL, 1)
