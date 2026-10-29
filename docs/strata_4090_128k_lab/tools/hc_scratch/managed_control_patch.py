"""P20 diagnostic only: managed backing for the four independent HC arrays."""
import hashlib

SOURCE_SHA256 = '0f33677020ef6f9b57de74b961f12a1380a6bbee4ac56dd813b22069c624b2a3'
OLD = r'''            strata_lab_full_oracle::require(free_bytes >= required_bytes, "private HC control VRAM headroom");
            Alloc h; h.owned = &private_hc.owned; bool allocated = true;
            m.xn16 = h.take<uint16_t>((size_t) m.T * D, allocated);
            m.lo = h.take<float>((size_t) m.T * LR, allocated);
            m.lo16 = h.take<uint16_t>((size_t) m.T * LR, allocated);
            m.gated = h.take<float>((size_t) m.T * D, allocated);
            strata_lab_full_oracle::require(allocated, "private HC control allocation");
            std::fprintf(stderr, "P19_PRIVATE_HC {\"T\":%lld,\"bytes\":%llu,\"separate_allocations\":4,"
                "\"loan_unchanged\":true}\n", (long long) T, (unsigned long long) h.used);'''

NEW = r'''            // Only the diagnostic shadow arrays are pageable. Native cache storage is unchanged.
            int device = -1, managed = 0, concurrent = 0;
            strata_lab_full_oracle::require(cudaGetDevice(&device) == cudaSuccess &&
                cudaDeviceGetAttribute(&managed, cudaDevAttrManagedMemory, device) == cudaSuccess &&
                cudaDeviceGetAttribute(&concurrent, cudaDevAttrConcurrentManagedAccess, device) == cudaSuccess &&
                managed == 1 && concurrent == 1, "managed HC oversubscription capability");
            strata_lab_full_oracle::require(p0 == 0 && T == 16384 && m.T == T && m.cache,
                                            "managed HC frozen16K geometry");
            cudaPointerAttributes cache_attr{}, region_attr{};
            strata_lab_full_oracle::require(
                cudaPointerGetAttributes(&cache_attr, m.cache->device_slot(0)) == cudaSuccess &&
                cudaPointerGetAttributes(&region_attr, m.region) == cudaSuccess &&
                cache_attr.type == cudaMemoryTypeDevice && region_attr.type == cudaMemoryTypeDevice,
                "managed HC must not change native cache backing");
            uint64_t managed_bytes = 0;
            auto take_managed = [&](uint64_t payload) -> void* {
                const uint64_t bytes = (payload + 256 + 255) & ~255ull;
                void* p = nullptr;
                strata_lab_full_oracle::require(cudaMallocManaged(&p, (size_t) bytes, cudaMemAttachGlobal) == cudaSuccess,
                                                "managed HC allocation");
                private_hc.owned.push_back(p);
                cudaPointerAttributes a{};
                strata_lab_full_oracle::require(cudaPointerGetAttributes(&a, p) == cudaSuccess &&
                                                a.type == cudaMemoryTypeManaged, "managed HC pointer type");
                managed_bytes += bytes;
                return p;
            };
            m.xn16 = (uint16_t*) take_managed((uint64_t) m.T * D * sizeof(uint16_t));
            m.lo = (float*) take_managed((uint64_t) m.T * LR * sizeof(float));
            m.lo16 = (uint16_t*) take_managed((uint64_t) m.T * LR * sizeof(uint16_t));
            m.gated = (float*) take_managed((uint64_t) m.T * D * sizeof(float));
            strata_lab_full_oracle::require(managed_bytes == required_bytes && private_hc.owned.size() == 4,
                                            "managed HC padded extent");
            std::fprintf(stderr, "P19_PRIVATE_HC {\"T\":%lld,\"bytes\":%llu,\"separate_allocations\":4,"
                "\"loan_unchanged\":true}\n", (long long) T, (unsigned long long) managed_bytes);
            std::fprintf(stderr, "P20_MANAGED_HC {\"T\":%lld,\"bytes\":%llu,\"managed_allocations\":4,"
                "\"device\":%d,\"managed_memory\":%d,\"concurrent_managed_access\":%d,"
                "\"cache_memory_type\":%d,\"region_memory_type\":%d,\"cache_slots\":%lld,\"loan_unchanged\":true}\n",
                (long long) T, (unsigned long long) managed_bytes, device, managed, concurrent,
                int(cache_attr.type), int(region_attr.type), (long long) m.cache->slots());'''


def transform(source):
    if hashlib.sha256(source.encode()).hexdigest() != SOURCE_SHA256 or source.count(OLD) != 1:
        raise ValueError('MANAGED_CONTROL_SOURCE_DRIFT')
    return source.replace(OLD, NEW, 1)
