// CPU-only finite screen of redundant zero filling. No CUDA headers or calls.
#include "strata/core/conversation_buffer.hpp"
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sys/resource.h>
#include <vector>

using strata::core::ConversationBuffer;
using Clock = std::chrono::steady_clock;

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    const size_t bytes = std::strtoull(argv[1], nullptr, 10);
    if (bytes == 0 || bytes > size_t(3) * 1024 * 1024 * 1024) return 2;
    std::vector<uint8_t> source(bytes, 0xa5);
    const char* order = "ABBAAB";  // Three fixed pairs; never replace a sample.
    for (int i = 0; i < 6; ++i) {
        rusage before{}, after{};
        getrusage(RUSAGE_SELF, &before);
        const auto t0 = Clock::now();
        ConversationBuffer dst;
        if (order[i] == 'A') dst.resize(bytes);
        else dst.resize_for_overwrite(bytes);
        const auto t1 = Clock::now();
        const bool copied = dst.visit(0, bytes, [&](uint8_t* p, size_t n, size_t at) {
            std::memcpy(p, source.data() + at, n);
            return true;
        });
        const auto t2 = Clock::now();
        getrusage(RUSAGE_SELF, &after);
        const bool equal = dst.visit(0, bytes, [&](const uint8_t* p, size_t n, size_t at) {
            return std::memcmp(p, source.data() + at, n) == 0;
        });
        if (!copied || !equal) return 1;
        auto ms = [](auto a, auto b) { return std::chrono::duration<double, std::milli>(b - a).count(); };
        std::printf("{\"order\":%d,\"arm\":\"%c\",\"bytes\":%zu,\"capacity_bytes\":%zu,"
                    "\"resize_ms\":%.6f,\"copy_ms\":%.6f,\"total_ms\":%.6f,"
                    "\"minor_fault_delta\":%ld,\"major_fault_delta\":%ld,\"payload_equal\":true}\n",
                    i, order[i], bytes, dst.bytes(), ms(t0,t1), ms(t1,t2), ms(t0,t2),
                    after.ru_minflt-before.ru_minflt, after.ru_majflt-before.ru_majflt);
        std::fflush(stdout);
    }
}
