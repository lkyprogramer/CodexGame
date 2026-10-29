// Read fixed token IDs and the same GGUF through llama.cpp's independent graph.
// No tokenizer, sampler, prompt rewrite, MTP, expert compression, or HTTP layer.
#include "llama.h"
#include "ggml-backend.h"
#include <algorithm>
#include <charconv>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

static std::vector<llama_token> read_ids(const std::string &path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot read IDs: " + path);
    std::string text((std::istreambuf_iterator<char>(in)), {});
    std::replace(text.begin(), text.end(), ',', ' ');
    std::istringstream stream(text);
    std::vector<llama_token> ids;
    long long value;
    while (stream >> value) {
        if (value < 0 || value > INT32_MAX) throw std::runtime_error("invalid token ID");
        ids.push_back(static_cast<llama_token>(value));
    }
    if (!stream.eof() || ids.empty()) throw std::runtime_error("malformed or empty IDs");
    return ids;
}

static unsigned long long fnv_ids(const std::vector<llama_token> &ids) {
    unsigned long long value = 1469598103934665603ULL;
    for (auto id : ids) for (int byte = 0; byte < 4; ++byte) {
        value ^= (static_cast<unsigned int>(id) >> (byte * 8)) & 255;
        value *= 1099511628211ULL;
    }
    return value;
}

int main(int argc, char **argv) {
    llama_model *model = nullptr;
    llama_context *ctx = nullptr;
    try {
        std::string model_path, cases_path, backend_path;
        int layers = 18, context = 131072, batch_size = 512, threads = 16;
        for (int i = 1; i < argc; i += 2) {
            if (i + 1 == argc) throw std::runtime_error("option needs a value");
            std::string key = argv[i], value = argv[i + 1];
            if (key == "--model") model_path = value;
            else if (key == "--cases") cases_path = value;
            else if (key == "--backend-path") backend_path = value;
            else if (key == "--ngl") layers = std::stoi(value);
            else if (key == "--max-context") context = std::stoi(value);
            else if (key == "--batch") batch_size = std::stoi(value);
            else if (key == "--threads") threads = std::stoi(value);
            else throw std::runtime_error("unknown option: " + key);
        }
        if (context != 131072 || batch_size < 1 || batch_size > 1024 || threads < 1 || threads > 32)
            throw std::runtime_error("invalid lab bounds");
        if (model_path.empty() || cases_path.empty() || backend_path.empty())
            throw std::runtime_error("missing model, cases or backend path");
        ggml_backend_load_all_from_path(backend_path.c_str());
        llama_backend_init();
        std::printf("BUILD ggml_version=%s ggml_commit=%s\n", ggml_version(), ggml_commit());
        std::fflush(stdout);
        auto mp = llama_model_default_params();
        mp.n_gpu_layers = layers;
        mp.load_mode = LLAMA_LOAD_MODE_MMAP;
        mp.lazy_mode = LLAMA_LAZY_MODE_ON;
        mp.mmap_prefetch = LLAMA_MMAP_PREFETCH_MODE_OFF;
        mp.use_extra_bufts = false;
        mp.load_mtp = false;
        model = llama_model_load_from_file(model_path.c_str(), mp);
        if (!model) throw std::runtime_error("model load failed");
        const auto *vocab = llama_model_get_vocab(model);
        const int width = llama_vocab_n_tokens(vocab);
        if (width != 248320) throw std::runtime_error("unexpected vocabulary size");
        std::ifstream cases(cases_path);
        if (!cases) throw std::runtime_error("cannot read cases manifest");
        std::string line;
        while (std::getline(cases, line)) {
            if (line.empty()) continue;
            std::istringstream fields(line);
            std::string name, tokens_path, prefix_path, output_path, extra;
            if (!(fields >> name >> tokens_path >> prefix_path >> output_path) || fields >> extra)
                throw std::runtime_error("case manifest needs four whitespace-free fields");
            auto ids = read_ids(tokens_path);
            const auto prefix = read_ids(prefix_path);
            if (ids.size() + prefix.size() + 1 + 4096 > static_cast<size_t>(context))
                throw std::runtime_error("total context budget exceeded");
            for (auto id : ids) if (id >= width) throw std::runtime_error("input token outside vocabulary");
            for (auto id : prefix) if (id >= width) throw std::runtime_error("prefix token outside vocabulary");
            auto cp = llama_context_default_params();
            cp.n_ctx = context;
            cp.n_batch = cp.n_ubatch = batch_size;
            cp.n_seq_max = 1;
            cp.n_threads = cp.n_threads_batch = threads;
            cp.type_k = cp.type_v = GGML_TYPE_F16;
            cp.moe_cache_mode = LLAMA_MOE_CACHE_MODE_OFF;
            cp.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_AUTO;
            cp.op_offload = layers > 0;
            cp.offload_kqv = layers > 0;
            ctx = llama_init_from_model(model, cp);
            if (!ctx || llama_n_ctx(ctx) != static_cast<unsigned>(context))
                throw std::runtime_error("context creation or size mismatch");
            std::printf("CASE %s input=%zu prefix=%zu input_fnv=%016llx prefix_fnv=%016llx vocab=%d kv=f16 moe_cache=off\n",
                        name.c_str(), ids.size(), prefix.size(), fnv_ids(ids), fnv_ids(prefix), width);
            std::fflush(stdout);
            auto batch = llama_batch_init(batch_size, 0, 1);
            auto decode = [&](const llama_token *tokens, int count, int position) {
                batch.n_tokens = count;
                for (int i = 0; i < count; ++i) {
                    batch.token[i] = tokens[i];
                    batch.pos[i] = position + i;
                    batch.n_seq_id[i] = 1;
                    batch.seq_id[i][0] = 0;
                    batch.logits[i] = i == count - 1;
                }
                const int rc = llama_decode(ctx, batch);
                if (rc != 0) throw std::runtime_error("llama_decode failed: " + std::to_string(rc));
            };
            auto started = std::chrono::steady_clock::now();
            for (size_t at = 0; at < ids.size(); at += batch_size) {
                const int count = static_cast<int>(std::min<size_t>(batch_size, ids.size() - at));
                decode(ids.data() + at, count, static_cast<int>(at));
                const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - started).count();
                std::printf("PREFILL %s %zu/%zu %.3f\n", name.c_str(), at + count, ids.size(), seconds);
                std::fflush(stdout);
            }
            FILE *out = std::fopen(output_path.c_str(), "wb");
            if (!out) throw std::runtime_error("cannot open logits output");
            for (size_t step = 0; step <= prefix.size(); ++step) {
                const float *row = llama_get_logits_ith(ctx, -1);
                if (!row) throw std::runtime_error("missing output logits");
                int top = 0;
                for (int id = 0; id < width; ++id) {
                    if (!std::isfinite(row[id])) throw std::runtime_error("nonfinite reference logits");
                    if (row[id] > row[top]) top = id;
                }
                if (std::fwrite(row, sizeof(float), width, out) != static_cast<size_t>(width))
                    throw std::runtime_error("logits write failed");
                std::fflush(out);
                std::printf("ROW %s %zu top=%d value=%.9g forced_next=%d\n", name.c_str(), step,
                            top, row[top], step < prefix.size() ? prefix[step] : -1);
                std::fflush(stdout);
                if (step < prefix.size()) decode(&prefix[step], 1, static_cast<int>(ids.size() + step));
            }
            std::fclose(out);
            llama_batch_free(batch);
            llama_free(ctx);
            ctx = nullptr;
            std::printf("COMPLETE %s rows=%zu\n", name.c_str(), prefix.size() + 1);
            std::fflush(stdout);
        }
        llama_model_free(model);
        llama_backend_free();
        return 0;
    } catch (const std::exception &error) {
        std::fprintf(stderr, "REFERENCE_FAILURE: %s\n", error.what());
        if (ctx) llama_free(ctx);
        if (model) llama_model_free(model);
        llama_backend_free();
        return 1;
    }
}
