#include "qualification_v2.hpp"
#include <fstream>
#include <stdexcept>

struct Saved {
    std::vector<float> rows;
    std::array<int32_t,7> tokens{};
    std::array<float,7> probabilities{};
};
static Saved read(const char* path, uint32_t magic) {
    std::ifstream f(path, std::ios::binary); uint32_t h[4]{};
    f.read(reinterpret_cast<char*>(h), sizeof(h));
    if (!f || h[0] != magic || h[1] != 1 || h[2] != 20480 || h[3] != 7)
        throw std::runtime_error("saved header");
    Saved d; d.rows.resize(h[2]);
    f.read(reinterpret_cast<char*>(d.rows.data()), d.rows.size()*4);
    f.read(reinterpret_cast<char*>(d.tokens.data()), 28);
    f.read(reinterpret_cast<char*>(d.probabilities.data()), 28);
    if (!f || f.peek() != EOF) throw std::runtime_error("saved payload");
    return d;
}
int main(int argc, char** argv) {
    if (argc != 5) return 2;
    try {
        auto actual = read(argv[1], 0x424f3144), reference = read(argv[2], 0x46523144);
        std::ifstream fixture(argv[3], std::ios::binary); int32_t h[4]{};
        fixture.read(reinterpret_cast<char*>(h), sizeof(h));
        if (!fixture || h[0] <= 0 || h[0] > 2300 || h[2] != 256) throw std::runtime_error("fixture header");
        fixture.seekg(16 + int64_t(h[0])*5*2560*4 + 2*2560*4);
        std::vector<int32_t> vocabulary(h[2]);
        fixture.read(reinterpret_cast<char*>(vocabulary.data()), vocabulary.size()*4);
        if (!fixture) throw std::runtime_error("fixture vocabulary");
        auto r = df01_compare_v2(actual.rows, reference.rows, actual.tokens.data(), reference.tokens.data(),
            actual.probabilities.data(), reference.probabilities.data(), vocabulary);
        if (!df01_write_v2(argv[4], r)) throw std::runtime_error("exclusive receipt write");
        std::printf("SAVED_REPLAY legacy=%s drafter_hard=%s confidence_difference=%d D1_qualified=false\n",
            r.legacy_pass ? "PASS" : "FAIL", r.hard_pass ? "PASS" : "FAIL", r.confidence_difference);
        return r.hard_pass ? 0 : 1;
    } catch (const std::exception& e) { std::fprintf(stderr, "%s\n", e.what()); return 2; }
}
