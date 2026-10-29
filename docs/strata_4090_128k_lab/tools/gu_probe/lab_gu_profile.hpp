// Lab-only CPU-miss accounting and bounded real-input capture. No arithmetic changes.
#pragma once
#include "strata/kernels/cpu/native_expert.hpp"
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <stdexcept>
#include <string>
#include <dlfcn.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

namespace strata::kernels::cpu {
inline int64_t lab_gu_now_ns() {
    return std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now().time_since_epoch()).count();
}
inline void lab_gu_oracle(int type, int nt, const void* dot) {
    static const bool enabled = std::getenv("STRATA_LAB_GU_PROFILE") != nullptr;
    if (!enabled || type < 0 || type >= 64 || nt < 1 || nt > 8) return;
    thread_local bool seen[64][9] = {};
    if (seen[type][nt]) return;
    seen[type][nt] = true;
    Dl_info info{};
    if (dladdr(dot, &info) == 0) std::abort();
    std::fprintf(stderr, "LAB_GU_ORACLE type=%d nt=%d path=ggml dot_offset=%llu module=%s\n", type, nt,
        (unsigned long long) ((uintptr_t) dot - (uintptr_t) info.dli_fbase), info.dli_fname);
}

class LabGuProfile {
    // Header 64 words; phase[type][4]; jobs[type][nt][2]; work[thread][type][nt][3].
    static constexpr size_t kTypes = 64, kNt = 9, kHeader = 64;
    static constexpr size_t kPhase = kHeader, kJobs = kPhase + kTypes*4;
    static constexpr size_t kWork = kJobs + kTypes*kNt*2;
    uint64_t* data_ = nullptr;
    size_t bytes_ = 0;
    int fd_ = -1, threads_ = 0;
    std::string capture_dir_;
    int capture_type_ = -1, capture_limit_ = 192;
    std::map<const uint8_t*, int> captured_;
    int batches_ = 0;

    static void write_file(const std::string& name, const void* data, size_t bytes) {
        FILE* file = std::fopen(name.c_str(), "wbx");
        if (!file || std::fwrite(data, 1, bytes, file) != bytes || std::fclose(file) != 0)
            throw std::runtime_error("GU_CAPTURE_WRITE_FAILED: " + name);
    }
public:
    explicit LabGuProfile(int threads): threads_(threads) {
        const char* file = std::getenv("STRATA_LAB_GU_PROFILE");
        if (!file) throw std::runtime_error("GU_PROFILE_PATH_MISSING");
        bytes_ = (kWork + (size_t) threads*kTypes*kNt*3)*sizeof(uint64_t);
        fd_ = open(file, O_CREAT|O_EXCL|O_RDWR, 0600);
        if (fd_ < 0 || ftruncate(fd_, (off_t) bytes_) != 0) throw std::runtime_error("GU_PROFILE_CREATE_FAILED");
        data_ = (uint64_t*) mmap(nullptr, bytes_, PROT_READ|PROT_WRITE, MAP_SHARED, fd_, 0);
        if (data_ == MAP_FAILED) throw std::runtime_error("GU_PROFILE_MMAP_FAILED");
        data_[0] = 0x31454c49464f5250ULL; data_[1] = 1; data_[2] = threads;
        data_[3] = kTypes; data_[4] = kNt; data_[8] = bytes_;
        if (const char* dir = std::getenv("STRATA_LAB_GU_CAPTURE")) {
            capture_dir_ = dir;
            const char* type = std::getenv("STRATA_LAB_GU_CAPTURE_TYPE");
            if (!type) throw std::runtime_error("GU_CAPTURE_TYPE_MISSING");
            capture_type_ = std::atoi(type);
        }
        std::fprintf(stderr, "LAB_GU_PROFILE version=1 threads=%d file=%s capture_type=%d\n", threads, file, capture_type_);
    }
    ~LabGuProfile() {
        if (data_ && data_ != MAP_FAILED) { msync(data_, bytes_, MS_SYNC); munmap(data_, bytes_); }
        if (fd_ >= 0) close(fd_);
    }
    void work(int thread, int type, int nt, int rows, uint64_t ns) {
        if (thread < 0 || thread >= threads_ || type < 0 || type >= 64 || nt < 1 || nt > 8) std::abort();
        auto* bin = data_ + kWork + (((size_t) thread*kTypes + type)*kNt + nt)*3;
        ++bin[0]; bin[1] += rows; bin[2] += ns;
    }
    template<class Jobs> void phase(const NativeFmt& f, Jobs* jobs, int n, uint64_t gu, uint64_t quant, uint64_t down) {
        auto* phase = data_ + kPhase + (size_t) f.gu_type*4;
        ++phase[0]; phase[1] += gu; phase[2] += quant; phase[3] += down;
        ++data_[5]; data_[6] += n;
        for (int i = 0; i < n; ++i) {
            const NativeFmt& actual = jobs[i].fmt ? *jobs[i].fmt : f;
            if (actual.gu_type != f.gu_type || actual.n_ff != f.n_ff) std::abort();
            const int nt = jobs[i].nt;
            if (nt < 1 || nt > 8) std::abort();
            auto* bin = data_ + kJobs + ((size_t) f.gu_type*kNt + nt)*2;
            ++bin[0]; bin[1] += nt; data_[7] += nt;
        }
    }
    template<class Jobs> void capture(const NativeFmt& f, Jobs* jobs, int n) {
        if (capture_dir_.empty() || f.gu_type != capture_type_ || batches_ >= 256) return;
        if (f.had_block || f.had_gu || f.had_d || f.tail_off) throw std::runtime_error("GU_CAPTURE_UNSUPPORTED_GEOMETRY");
        int extra = 0;
        for (int e = 0; e < n; ++e) if (!captured_.count(jobs[e].blob)) ++extra;
        if ((int) captured_.size()+extra > capture_limit_) return;
        const std::string batch = "batch-"+std::to_string(batches_++);
        std::string manifest = "{\"gu_type\":"+std::to_string(f.gu_type)+",\"jobs\":[";
        for (int e = 0; e < n; ++e) {
            auto found = captured_.find(jobs[e].blob);
            if (found == captured_.end()) {
                const int id = (int) captured_.size(); captured_[jobs[e].blob] = id;
                const std::string stem = capture_dir_ + "/fixture-" + std::to_string(id);
                write_file(stem+".blob", jobs[e].blob, f.bytes);
                char meta[1024];
                const int bytes = std::snprintf(meta, sizeof meta,
                    "{\"id\":%d,\"gu_type\":%d,\"d_type\":%d,\"n_embd\":%lld,\"n_ff\":%lld,"
                    "\"gu_row\":%zu,\"d_row\":%zu,\"up_off\":%zu,\"down_off\":%zu,\"bytes\":%zu,"
                    "\"act_bytes\":%zu,\"h_bytes\":%zu}\n", id, f.gu_type, f.d_type,
                    (long long) f.n_embd, (long long) f.n_ff, f.gu_row, f.d_row, f.up_off, f.down_off,
                    f.bytes, f.act_bytes, f.h_bytes);
                if (bytes <= 0 || (size_t) bytes >= sizeof meta) std::abort();
                write_file(stem+".json", meta, bytes);
                found = captured_.find(jobs[e].blob);
            }
            if (e) manifest += ",";
            manifest += "{\"blob\":"+std::to_string(found->second)+",\"nt\":"+std::to_string(jobs[e].nt)+",\"acts\":[";
            for (int t = 0; t < jobs[e].nt; ++t) {
                const std::string name = batch+"-e"+std::to_string(e)+"-t"+std::to_string(t)+".act";
                write_file(capture_dir_+"/"+name, jobs[e].nact[t], f.act_bytes);
                if (t) manifest += ",";
                manifest += "\""+name+"\"";
            }
            manifest += "]}";
        }
        manifest += "]}\n";
        write_file(capture_dir_+"/"+batch+".json",manifest.data(),manifest.size());
    }
};
} // namespace strata::kernels::cpu
