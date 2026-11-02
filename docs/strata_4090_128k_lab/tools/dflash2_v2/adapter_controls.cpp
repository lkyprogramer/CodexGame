#include "qualification_v2.hpp"
#include <limits>
#include <stdexcept>

int main() {
    std::vector<float> rows(8 * 2560, 1.f), reference = rows;
    std::array<int32_t, 7> tokens{1,2,3,4,5,6,7}, expected = tokens;
    std::array<float, 7> p{}, q{}; p.fill(.5f); q = p;
    const std::vector<int32_t> vocabulary{1,2,3,4,5,6,7};
    int checks = 0;
    auto check = [&](bool hard, bool legacy, bool diag) {
        auto r = df01_compare_v2(rows, reference, tokens.data(), expected.data(), p.data(), q.data(), vocabulary);
        if (r.hard_pass != hard || r.legacy_pass != legacy || r.confidence_difference != diag)
            throw std::runtime_error("classification control " + std::to_string(checks));
        ++checks; return r;
    };
    check(true, true, false);
    for (int i = 0; i < 7; ++i) { p[i] = .8f; check(true, false, true); p[i] = .5f; }
    // A confidence difference must not hide a later hard failure.
    p[0] = .8f; tokens[6] = 6; check(false, false, true); tokens = expected;
    rows[0] = std::numeric_limits<float>::quiet_NaN(); check(false, false, true); rows = reference;
    rows.pop_back(); check(false, false, true); rows = reference;
    reference.pop_back(); check(false, false, true); reference = rows;
    for (int i = 0; i < 2560; ++i) rows[i] = -1; check(false, false, true); rows = reference;
    for (int i = 0; i < 2560; ++i) rows[i] = 1.06f; check(false, false, true); rows = reference;
    for (int i = 0; i < 2560; ++i) rows[i] = 0; check(false, false, true); rows = reference;
    reference[0] = INFINITY; check(false, false, true); reference = rows;
    for (bool actual : {false, true}) for (float bad : {NAN, INFINITY, -.01f, 1.01f}) {
        auto& values = actual ? p : q; values[6] = bad;
        check(false, false, true); values[6] = .5f;
    }
    tokens[6] = expected[6] = -1; check(false, false, true); tokens[6] = expected[6] = 7;
    p = q; p[0] = .05f; q[0] = 0; check(true, true, false);
    p[0] = std::nextafter(.05f, 1.f); check(true, false, true);
    auto r = check(true, false, true);
    if (!df01_write_v2("control.v2.json", r)) throw std::runtime_error("receipt write");
    if (df01_write_v2("control.v2.json", r)) throw std::runtime_error("receipt overwrite");
    p[6] = NAN;
    r = check(false, false, true);
    if (!df01_write_v2("invalid.v2.json", r)) throw std::runtime_error("invalid receipt write");
    std::printf("V2_CLASSIFICATION_CONTROLS_PASS %d checks; no CUDA calls\n", checks);
}
