#include "lab_p01b_trace.hpp"
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    using namespace strata::lab_p01b;
    if (argc != 3) return 2;
    if (std::string(argv[1]) == "records") {
        setenv("STRATA_LAB_P01B_TRACE", argv[2], 1);
        begin_request();
        for (int i = 0; i < 66; ++i) {
            begin_window(103183 + i, 2, false, false);
            verified(true); commit_enter(1, 0, 0, false, true, i == 1);
            commit_return(); token(i); draft_return(); end_window();
        }
        end_request();
        begin_request();
        for (int i = 0; i < 2050; ++i) token(i);
        end_request();
        begin_request();
        for (int i = 0; i <= kWindows; ++i) begin_window(103183 + i, 1, false, false);
        end_request();
        std::cout << "RECORD_PROBE_COMPLETE\n";
        return 0;
    }
    if (std::string(argv[1]) == "on") setenv("STRATA_LAB_P01B_TRACE", argv[2], 1);
    else unsetenv("STRATA_LAB_P01B_TRACE");
    constexpr int batches = 10000;
    const auto start = now();
    for (int b = 0; b < batches; ++b) {
        begin_request();
        for (int i = 0; i < 64; ++i) {
            begin_window(103183 + i, 4, false, false); verified(true);
            commit_enter(3, 0, 0, false, true, false); commit_return();
            token(i); draft_return(); end_window();
        }
    }
    const auto elapsed = now() - start;
    std::cout << "{\"mode\":\"" << argv[1] << "\",\"windows\":" << batches * 64
        << ",\"elapsed_ns\":" << elapsed << ",\"ns_per_window\":"
        << double(elapsed) / (batches * 64) << ",\"state_bytes\":" << sizeof(State) << "}\n";
}
