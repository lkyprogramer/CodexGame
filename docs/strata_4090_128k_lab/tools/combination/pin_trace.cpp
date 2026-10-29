// Experiment-only CUDA runtime allocation tracing; never alters requested sizes or flags.
#include <cuda_runtime_api.h>
#include <dlfcn.h>
#include <unistd.h>
#include <time.h>
#include <cstdio>
#include <cstdlib>
#include <cstdint>
#include <map>
#include <mutex>
#include <string>

namespace {
struct Entry { size_t bytes; bool registered; };
struct State {
    std::mutex mutex;
    std::map<void*, Entry> live;
    uint64_t allocated = 0, registered = 0, peak = 0, sequence = 0;
    FILE* output = nullptr;
    State() {
        const char* prefix = std::getenv("STRATA_BOUNDARY_PIN_TRACE");
        if (prefix) {
            const std::string path = std::string(prefix) + "." + std::to_string(getpid()) + ".jsonl";
            output = std::fopen(path.c_str(), "a");
        }
    }
};
State& state() { static State* value = new State; return *value; }
thread_local unsigned depth = 0;
struct Scope { bool outer; Scope(): outer(depth++ == 0) {} ~Scope() { --depth; } };
template<class T> T resolve(const char* name) {
    auto pointer = reinterpret_cast<T>(dlsym(RTLD_NEXT, name));
    if (!pointer) { std::fprintf(stderr, "PIN_TRACE_RESOLVE_FAILED %s\n", name); std::abort(); }
    return pointer;
}
void record(const char* operation, void* pointer, size_t bytes, unsigned flags,
            cudaError_t result, bool registered, bool release, void* caller) {
    State& s = state();
    std::lock_guard<std::mutex> guard(s.mutex);
    size_t released = 0;
    bool known = false;
    if (result == cudaSuccess && pointer) {
        if (release) {
            auto entry = s.live.find(pointer);
            if (entry != s.live.end()) {
                known = true; released = entry->second.bytes;
                (entry->second.registered ? s.registered : s.allocated) -= released;
                s.live.erase(entry);
            }
        } else {
            // Successful overlapping CUDA registrations are not expected; retain an audit flag.
            known = s.live.count(pointer) != 0;
            if (!known) {
                s.live.emplace(pointer, Entry{bytes, registered});
                (registered ? s.registered : s.allocated) += bytes;
            }
        }
    }
    const uint64_t total = s.allocated + s.registered;
    if (total > s.peak) s.peak = total;
    timespec realtime{}, monotonic{};
    clock_gettime(CLOCK_REALTIME, &realtime); clock_gettime(CLOCK_MONOTONIC, &monotonic);
    Dl_info location{}; dladdr(caller, &location);
    const auto offset = reinterpret_cast<uintptr_t>(caller) - reinterpret_cast<uintptr_t>(location.dli_fbase);
    if (s.output) {
        std::fprintf(s.output,
          "{\"sequence\":%llu,\"pid\":%d,\"realtime_ns\":%llu,\"monotonic_ns\":%llu,"
          "\"operation\":\"%s\",\"pointer\":\"%p\",\"bytes\":%zu,\"flags\":%u,\"result\":%d,"
          "\"release\":%s,\"known_pointer\":%s,\"released_bytes\":%zu,\"allocated_bytes\":%llu,"
          "\"registered_bytes\":%llu,\"outstanding_bytes\":%llu,\"peak_bytes\":%llu,\"caller_offset\":%llu}\n",
          static_cast<unsigned long long>(++s.sequence), getpid(),
          static_cast<unsigned long long>(realtime.tv_sec)*1000000000ULL+realtime.tv_nsec,
          static_cast<unsigned long long>(monotonic.tv_sec)*1000000000ULL+monotonic.tv_nsec,
          operation,pointer,bytes,flags,static_cast<int>(result),release?"true":"false",known?"true":"false",released,
          static_cast<unsigned long long>(s.allocated),static_cast<unsigned long long>(s.registered),
          static_cast<unsigned long long>(total),static_cast<unsigned long long>(s.peak),static_cast<unsigned long long>(offset));
        std::fflush(s.output);
    }
}
}

extern "C" cudaError_t cudaHostAlloc(void** pointer, size_t bytes, unsigned flags) {
    static auto next = resolve<decltype(&cudaHostAlloc)>("cudaHostAlloc"); Scope scope;
    auto result = next(pointer, bytes, flags);
    if (scope.outer) record("cudaHostAlloc", result==cudaSuccess?*pointer:nullptr, bytes, flags, result, false, false, __builtin_return_address(0));
    return result;
}
extern "C" cudaError_t cudaMallocHost(void** pointer, size_t bytes) {
    static auto next = resolve<decltype(&cudaMallocHost)>("cudaMallocHost"); Scope scope;
    auto result = next(pointer, bytes);
    if (scope.outer) record("cudaMallocHost", result==cudaSuccess?*pointer:nullptr, bytes, 0, result, false, false, __builtin_return_address(0));
    return result;
}
extern "C" cudaError_t cudaFreeHost(void* pointer) {
    static auto next = resolve<decltype(&cudaFreeHost)>("cudaFreeHost"); Scope scope;
    auto result = next(pointer);
    if (scope.outer) record("cudaFreeHost",pointer,0,0,result,false,true,__builtin_return_address(0));
    return result;
}
extern "C" cudaError_t cudaHostRegister(void* pointer, size_t bytes, unsigned flags) {
    static auto next = resolve<decltype(&cudaHostRegister)>("cudaHostRegister"); Scope scope;
    auto result = next(pointer,bytes,flags);
    if (scope.outer) record("cudaHostRegister",pointer,bytes,flags,result,true,false,__builtin_return_address(0));
    return result;
}
extern "C" cudaError_t cudaHostUnregister(void* pointer) {
    static auto next = resolve<decltype(&cudaHostUnregister)>("cudaHostUnregister"); Scope scope;
    auto result = next(pointer);
    if (scope.outer) record("cudaHostUnregister",pointer,0,0,result,true,true,__builtin_return_address(0));
    return result;
}
