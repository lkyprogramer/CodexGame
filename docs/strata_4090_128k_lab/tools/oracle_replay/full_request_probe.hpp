// P15_ORACLE: diagnostic dispatch transcript. Synchronization disturbs adaptive
// timing. This is not a performance result; weights and final state are frozen externally.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <fstream>
#include <sstream>
#include <sys/stat.h>

namespace strata_lab_full_oracle {
[[noreturn]] inline void reject(const std::string& why) {
    std::fprintf(stderr, "P15_ORACLE REJECT %s\n", why.c_str());
    std::fflush(nullptr);
    std::_Exit(86);
}
inline void require(bool ok, const std::string& why) { if (!ok) reject(why); }
struct Key {
    int64_t p0, T, layer, half;
    std::string str() const {
        return "p" + std::to_string(p0) + "-T" + std::to_string(T) + "-l" +
               std::to_string(layer) + "-h" + std::to_string(half);
    }
};
struct Entry { std::string key, field; size_t bytes; };
struct Probe {
    const char* dir = std::getenv("STRATA_LAB_ORACLE_DIR");
    const char* ref = std::getenv("STRATA_LAB_ORACLE_REF");
    std::vector<Entry> expected;
    std::map<std::string, size_t> index;
    size_t consumed = 0, count = 0, chunks = 0, ffn = 0;
    size_t ref_chunks = 0, ref_ffn = 0;
    bool chunk_open = false, initial_seen = false;
    Probe() {
        require(!ref || dir, "reference requires output directory");
        if (!dir) return;
        require(*dir && mkdir(dir, 0700) == 0, "output directory must be new");
        if (!ref) return;
        unsigned long long c = 0, f = 0, n = 0;
        std::ifstream done(std::string(ref) + "/COMPLETE.json");
        std::string line;
        require(bool(std::getline(done, line)), "reference has no COMPLETE.json");
        int end = 0;
        require(std::sscanf(line.c_str(), "{\"marker\":\"P15_ORACLE_COMPLETE\",\"chunks\":%llu,\"ffn\":%llu,\"records\":%llu}%n",
                            &c, &f, &n, &end) == 3 && end == (int) line.size() && c && f && n,
                "invalid reference completion");
        require(!std::getline(done, line), "extra reference completion data");
        ref_chunks = (size_t) c; ref_ffn = (size_t) f;
        std::ifstream manifest(std::string(ref) + "/records.tsv");
        require(bool(manifest), "reference manifest missing");
        while (std::getline(manifest, line)) {
            std::istringstream in(line);
            Entry e; unsigned long long bytes = 0; char extra;
            require(bool(std::getline(in, e.key, '\t')) && bool(std::getline(in, e.field, '\t')) &&
                    bool(in >> bytes) && !(in >> extra) && !e.key.empty() && !e.field.empty(), "invalid reference manifest row");
            e.bytes = (size_t) bytes;
            require(bytes == e.bytes && index.emplace(e.key + "/" + e.field, expected.size()).second,
                    "duplicate/oversize reference entry");
            expected.push_back(std::move(e));
        }
        require(expected.size() == n, "reference completion/manifest count mismatch");
    }
    ~Probe() {
        if (!dir) return;
        require(!chunk_open && chunks && ffn && (!ref || (consumed == expected.size() && chunks == ref_chunks && ffn == ref_ffn)),
                "unconsumed reference or incomplete request");
        auto* out = std::fopen((std::string(dir) + "/COMPLETE.json").c_str(), "wx");
        require(out != nullptr, "completion open");
        const int n = std::fprintf(out, "{\"marker\":\"P15_ORACLE_COMPLETE\",\"chunks\":%zu,\"ffn\":%zu,\"records\":%zu}\n",
                                   chunks, ffn, count);
        require(n > 0 && std::fclose(out) == 0, "completion write");
        std::fprintf(stderr, "P15_ORACLE COMPLETE chunks=%zu ffn=%zu records=%zu reference_consumed=%zu path=%s diagnostic_only=1\n",
                     chunks, ffn, count, consumed, dir);
    }
    std::string path(const char* base, const Key& k, const std::string& field) const {
        return std::string(base) + "/" + k.str() + "-" + field + ".bin";
    }
    void record(const Key& k, const std::string& field, size_t bytes, int64_t mismatch) {
        auto* t = std::fopen((std::string(dir) + "/records.tsv").c_str(), "ab");
        require(t, "manifest open");
        int n = std::fprintf(t, "%s\t%s\t%zu\n", k.str().c_str(), field.c_str(), bytes);
        require(n > 0 && std::fclose(t) == 0, "manifest write");
        auto* j = std::fopen((std::string(dir) + "/records.jsonl").c_str(), "ab");
        require(j, "record open");
        n = std::fprintf(j, "{\"p0\":%lld,\"T\":%lld,\"layer\":%lld,\"half\":%lld,\"field\":\"%s\",\"bytes\":%zu,\"reference\":%s,\"first_mismatch_byte\":%lld}\n",
                         (long long) k.p0, (long long) k.T, (long long) k.layer, (long long) k.half, field.c_str(), bytes,
                         ref ? "true" : "false", (long long) mismatch);
        require(n > 0 && std::fclose(j) == 0, "record write");
        ++count;
    }
    template<class Read> void raw(const Key& k, const std::string& field, size_t bytes, Read read) {
        if (!dir) return;
        const std::string label = k.str() + "/" + field;
        if (ref) {
            require(consumed < expected.size(), "extra live field " + label);
            const Entry& e = expected[consumed];
            require(e.key == k.str() && e.field == field && e.bytes == bytes, "reference order/shape " + label);
        }
        auto* out = std::fopen(path(dir, k, field).c_str(), "wbx");
        require(out, "output exists/open " + label);
        auto* prior = ref ? std::fopen(path(ref, k, field).c_str(), "rb") : nullptr;
        require(!ref || prior, "reference raw missing " + label);
        std::vector<unsigned char> now(1 << 20), before(1 << 20);
        int64_t mismatch = -1;
        for (size_t off = 0; off < bytes;) {
            const size_t n = std::min(bytes - off, now.size());
            read(off, now.data(), n);
            require(std::fwrite(now.data(), 1, n, out) == n, "raw write " + label);
            if (prior) {
                require(std::fread(before.data(), 1, n, prior) == n, "reference raw truncated " + label);
                if (mismatch < 0 && std::memcmp(now.data(), before.data(), n)) {
                    size_t i = 0; while (now[i] == before[i]) ++i;
                    mismatch = (int64_t) (off + i);
                }
            }
            off += n;
        }
        if (prior) { require(std::fgetc(prior) == EOF, "reference raw too long " + label); std::fclose(prior); }
        require(std::fclose(out) == 0, "raw close " + label);
        record(k, field, bytes, mismatch);
        if (ref) ++consumed;
        require(mismatch < 0, "byte mismatch " + label + " offset=" + std::to_string(mismatch));
    }
    void host(const Key& k, const std::string& field, const void* p, size_t bytes) {
        raw(k, field, bytes, [&](size_t o, void* b, size_t n) { std::memcpy(b, (const char*) p + o, n); });
    }
    template<class V> void vec(const Key& k, const std::string& field, const V& v) {
        host(k, field, v.data(), v.size() * sizeof(typename V::value_type));
    }
    template<class T> std::vector<T> load(const Key& k, const std::string& field, size_t max_count) {
        require(ref, "load outside replay");
        const auto it = index.find(k.str() + "/" + field);
        require(it != index.end(), "reference dispatch entry missing " + k.str() + "/" + field);
        const size_t bytes = expected[it->second].bytes;
        require(bytes % sizeof(T) == 0 && bytes / sizeof(T) <= max_count, "reference dispatch size");
        std::vector<T> out(bytes / sizeof(T));
        auto* f = std::fopen(path(ref, k, field).c_str(), "rb");
        require(f, "reference dispatch raw missing");
        require(std::fread(out.data(), 1, bytes, f) == bytes && std::fgetc(f) == EOF, "reference dispatch raw size");
        std::fclose(f);
        return out;
    }
};
inline Probe& probe() { static Probe p; return p; }
} // namespace strata_lab_full_oracle
