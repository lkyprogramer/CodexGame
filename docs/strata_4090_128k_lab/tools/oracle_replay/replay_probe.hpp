// P14_REPLAY: a single FFN diagnostic. Adaptive timing/on_routes are disturbed;
// final request logits and timings are not an oracle or a performance result.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <string>
#include <algorithm>
#include <sys/stat.h>

namespace strata_lab_replay {
[[noreturn]] inline void fail(const std::string& why) {
    std::fprintf(stderr, "P14_REPLAY REJECT %s\n", why.c_str());
    std::fflush(stderr);
    std::exit(86);
}
inline void require(bool yes, const std::string& why) { if (!yes) fail(why); }
struct Probe {
    const char* dir = std::getenv("STRATA_LAB_REPLAY_DIR");
    const char* negative = std::getenv("STRATA_LAB_REPLAY_NEGATIVE");
    bool hit = false, complete = false, arm = false;
    std::vector<char> cpu;
    std::vector<const uint8_t*> blobs;
    int64_t rows = 0, count = 0, streamed = 0;
    Probe() {
        if (!dir) return;
        require(*dir && mkdir(dir, 0700) == 0, "output directory must be new");
        require(!negative || !std::strcmp(negative, "input") || !std::strcmp(negative, "dispatch") ||
                !std::strcmp(negative, "mapping"), "unknown negative control");
    }
    ~Probe() {
        if (dir && !complete) {
            std::fprintf(stderr, "P14_REPLAY REJECT target not completed (hit=%d)\n", int(hit));
            std::fflush(stderr);
            std::_Exit(86);
        }
    }
    bool neg(const char* name, int pass) const { return pass == 1 && negative && !std::strcmp(name, negative); }
    std::string path(int pass, const std::string& field) const {
        return std::string(dir) + "/pass" + std::to_string(pass) + "-" + field + ".bin";
    }
    void record(int pass, const std::string& field, size_t bytes, bool guard) {
        auto* f = std::fopen((std::string(dir) + "/records.jsonl").c_str(), "ab");
        require(f != nullptr, "record open");
        const int n = std::fprintf(f, "{\"marker\":\"P14_REPLAY\",\"p0\":0,\"T\":4090,\"layer\":3,\"half\":1,"
                                    "\"pass\":%d,\"field\":\"%s\",\"bytes\":%zu,\"guard\":%s}\n",
                                   pass, field.c_str(), bytes, guard ? "true" : "false");
        require(n > 0 && std::fclose(f) == 0, "record write");
    }
    // Bounded host readback/compare: no full input or Dm copy retained in RAM.
    template<class Read> void raw(int pass, const std::string& field, size_t bytes, bool guard, Read read) {
        auto* out = std::fopen(path(pass, field).c_str(), "wbx");
        require(out != nullptr, "raw output already exists/open failed: " + field);
        auto* old = pass == 1 && guard ? std::fopen(path(0, field).c_str(), "rb") : nullptr;
        require(!(pass == 1 && guard) || old, "missing pass0 snapshot: " + field);
        std::vector<unsigned char> now(1 << 20), before(1 << 20);
        for (size_t off = 0; off < bytes;) {
            const size_t n = std::min(bytes - off, now.size());
            read(off, now.data(), n);
            require(std::fwrite(now.data(), 1, n, out) == n, "raw write: " + field);
            if (old) require(std::fread(before.data(), 1, n, old) == n &&
                             std::memcmp(now.data(), before.data(), n) == 0,
                             "snapshot mismatch: " + field + " block " + std::to_string(off));
            off += n;
        }
        if (old) { require(std::fgetc(old) == EOF, "snapshot length mismatch: " + field); std::fclose(old); }
        require(std::fclose(out) == 0, "raw close: " + field);
        record(pass, field, bytes, guard);
    }
    void host(int pass, const std::string& field, const void* p, size_t bytes, bool guard = true) {
        raw(pass, field, bytes, guard, [&](size_t o, void* b, size_t n) { std::memcpy(b, (const char*) p + o, n); });
    }
    template<class V> void vec(int pass, const std::string& field, const V& v, bool guard = true) {
        host(pass, field, v.data(), v.size() * sizeof(typename V::value_type), guard);
    }
    // This validates the real tables that will be uploaded and consumed, including
    // CPU/GPU row partition and each original (token,k)'s expert and token identity.
    void mapping(const int32_t* ids, const int32_t* slot, const int32_t* src,
                 const std::vector<int32_t>& cnt, const std::vector<int32_t>& off,
                 const std::vector<int32_t>& order, const std::vector<char>& on_cpu,
                 int64_t tk, int64_t k, int64_t rows_cpu) {
        const size_t ne = cnt.size();
        require(off.size() == ne + 1 && off[ne] == tk, "cnt/off coverage");
        require(on_cpu.empty() || on_cpu.size() == ne, "CPU map length");
        std::vector<char> seen((size_t) tk, 0), experts(ne, 0);
        int64_t total = 0, cr = 0;
        for (size_t e = 0; e < ne; ++e) {
            require(cnt[e] >= 0 && off[e] >= 0 && int64_t(off[e]) + cnt[e] <= tk, "expert bounds");
            const bool cpu = !on_cpu.empty() && on_cpu[e];
            if (cnt[e]) require(cpu ? off[e] >= tk - rows_cpu : int64_t(off[e]) + cnt[e] <= tk - rows_cpu,
                                "CPU/GPU overlap");
            total += cnt[e]; if (cpu) cr += cnt[e];
        }
        require(total == tk && cr == rows_cpu, "row count coverage");
        for (int32_t e : order) {
            require(e >= 0 && size_t(e) < ne && !experts[e] && cnt[e] > 0 &&
                    (on_cpu.empty() || !on_cpu[e]), "GPU expert order");
            experts[e] = 1;
        }
        for (size_t e = 0; e < ne; ++e)
            require(cnt[e] == 0 || (!on_cpu.empty() && on_cpu[e]) || experts[e], "GPU order coverage");
        for (int64_t i = 0; i < tk; ++i) {
            const int32_t e = ids[i], s = slot[i];
            require(e >= 0 && size_t(e) < ne && s >= 0 && s < tk && !seen[s], "slot permutation");
            require(s >= off[e] && int64_t(s) < int64_t(off[e]) + cnt[e] && src[s] == i / k,
                    "slot/src expert/token mapping");
            seen[s] = 1;
        }
    }
};
inline Probe& probe() { static Probe p; return p; }
} // namespace strata_lab_replay
