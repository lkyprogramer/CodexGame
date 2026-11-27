// T25: dense llama.cpp logits in the KL-divergence-base format, on given token ids.
//   t25_dense <gguf> <ids file> <first> <ub> <out.bin>
//   t25_dense <gguf> <ids file> gen <G> <out ids file>   greedy continuation (one token per
//       llama_decode) of G tokens; writes the ids followed by the continuation
// ids file: whitespace-separated token ids (one sequence, n_ctx = its length, one chunk).
// Header _logits_, n_ctx, n_vocab, 1, tokens; then one record per position first..n_ctx-2 (the
// log-probs after tokens 0..=j, predicting token j+1), encoded as llama-perplexity does: within
// 16 of the max, u16 steps of (max - min) / 65535 above min_log_prob, padded to an even count.
// ub 1: one token per llama_decode (like -ub 1); ub 512: n_ubatch 512, the sequence in batches of
// 512 tokens (llama splits one large batch into the same ubatches, like -ub 512).
// Build: g++ -O2 -std=c++17 -I$LLAMA/include -I$LLAMA/ggml/include t25_dense.cpp \
//        -L$LLAMA/build/bin -lllama -Wl,-rpath,$LLAMA/build/bin -o t25_dense
#include "llama.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
static void encode(const float * l, int nv, std::vector<uint16_t> & rec) {
    float mx = l[0], mn = l[0];
    for (int i = 1; i < nv; i++) { mx = std::max(mx, l[i]); mn = std::min(mn, l[i]); }
    mn = std::max(mn, mx - 16.0f);
    double sum = 0;
    for (int i = 0; i < nv; i++) sum += std::exp((double) (l[i] - mx));
    const float lse = (float) std::log(sum);
    const float min_log_prob = mn - mx - lse;
    const float scale = (mx - mn) / 65535.0f;
    std::fill(rec.begin(), rec.end(), 0);
    std::memcpy(&rec[0], &scale, 4);
    std::memcpy(&rec[2], &min_log_prob, 4);
    if (scale != 0.0f) {
        const float inv = 1.0f / scale;
        for (int i = 0; i < nv; i++) rec[4 + i] = l[i] > mn ? (uint16_t) std::nearbyint(inv * (l[i] - mn)) : 0;
    }
}
int main(int argc, char ** argv) {
    if (argc != 6) { std::fprintf(stderr, "usage: %s <gguf> <ids> <first> <ub 1|512> <out.bin>\n", argv[0]); return 2; }
    std::vector<llama_token> ids;
    { std::ifstream f(argv[2]); for (long t; f >> t;) ids.push_back((llama_token) t); }
    const bool gen = std::string(argv[3]) == "gen";
    const int n = (int) ids.size(), first = gen ? 0 : std::atoi(argv[3]), ub = gen ? 1 : std::atoi(argv[4]), g = gen ? std::atoi(argv[4]) : 0;
    if (gen ? (n < 1 || g < 1) : (n < 4 || first < 1 || first >= n - 1 || (ub != 1 && ub != 512))) { std::fprintf(stderr, "bad arguments (n %d first %d ub %d)\n", n, first, ub); return 2; }
    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 999;
    llama_model * model = llama_model_load_from_file(argv[1], mp);
    if (!model) return 1;
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = n + g + 16; cp.n_batch = 512; cp.n_ubatch = 512; cp.n_seq_max = 1;
    llama_context * ctx = llama_init_from_model(model, cp);
    if (!ctx) return 1;
    const int nv = llama_vocab_n_tokens(llama_model_get_vocab(model));
    std::vector<uint16_t> rec(2 * ((nv + 1) / 2) + 4);
    if (gen) {
        llama_batch b1 = llama_batch_init(1, 0, 1);
        std::vector<llama_token> all = ids;
        for (int p = 0; p < n + g - 1; p++) {
            b1.n_tokens = 1; b1.token[0] = all[p]; b1.pos[0] = p; b1.n_seq_id[0] = 1; b1.seq_id[0][0] = 0; b1.logits[0] = p >= n - 1;
            if (llama_decode(ctx, b1) != 0) { std::fprintf(stderr, "decode failed at %d\n", p); return 1; }
            if (p >= n - 1) {
                const float * l = llama_get_logits_ith(ctx, 0);
                all.push_back((llama_token) (std::max_element(l, l + nv) - l));
            }
        }
        std::ofstream o(argv[5]);
        for (size_t i = 0; i < all.size(); i++) o << (i ? " " : "") << all[i];
        o << "\n";
        std::printf("%d prompt tokens + %d greedy\n", n, g);
        llama_batch_free(b1); llama_free(ctx); llama_model_free(model);
        return 0;
    }
    FILE * out = std::fopen(argv[5], "wb");
    if (!out) return 1;
    const int32_t hdr[3] = {n, nv, 1};
    std::fwrite("_logits_", 1, 8, out);
    std::fwrite(hdr, 4, 3, out);
    std::fwrite(ids.data(), 4, n, out);
    llama_batch batch = llama_batch_init(512, 0, 1);
    for (int p = 0; p < n - 1; p += ub) {
        const int m = std::min(ub, n - 1 - p);
        batch.n_tokens = m;
        for (int i = 0; i < m; i++) {
            batch.token[i] = ids[p + i]; batch.pos[i] = p + i; batch.n_seq_id[i] = 1; batch.seq_id[i][0] = 0;
            batch.logits[i] = p + i >= first;
        }
        if (llama_decode(ctx, batch) != 0) { std::fprintf(stderr, "decode failed at %d\n", p); return 1; }
        for (int i = 0; i < m; i++) {
            if (p + i < first) continue;
            encode(llama_get_logits_ith(ctx, i), nv, rec);
            std::fwrite(rec.data(), 2, rec.size(), out);
        }
    }
    std::fclose(out);
    std::printf("%d tokens, %d records from %d, ub %d\n", n, n - 1 - first, first, ub);
    llama_batch_free(batch); llama_free(ctx); llama_model_free(model);
    return 0;
}
