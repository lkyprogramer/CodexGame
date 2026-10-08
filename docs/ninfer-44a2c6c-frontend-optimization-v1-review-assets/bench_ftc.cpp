// Review harness (not part of NInfer): measures the pinned 44a2c6c frontend tokenization path
// and exact-equivalent candidates on rendered chat sessions, checking every output against the
// legacy result.
#include <algorithm>
#include <array>
#include <charconv>
#include <cctype>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include <nlohmann/json.hpp>

#include "text/unicode.h"

#define private public
#include "targets/qwen3_8/impl/frontend/tokenizer.cpp"
#undef private

#include "targets/qwen3_8/impl/frontend/chat_template.h"

namespace fi  = ninfer::targets::qwen3_8::frontend_internal;
using Json    = nlohmann::json;
using Clock   = std::chrono::steady_clock;
using Restart = std::pair<std::size_t, std::size_t>; // byte offset after added token, token count

static double secs(Clock::time_point a, Clock::time_point b) {
    return std::chrono::duration<double>(b - a).count();
}

static std::string read_file(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) { throw std::runtime_error("cannot open " + path); }
    return std::string(std::istreambuf_iterator<char>(in), {});
}

struct Encoded {
    std::vector<int> ids;
    std::optional<std::uint32_t> stable, turn, user;
    std::vector<std::pair<int, std::uint32_t>> hints;
    bool operator==(const Encoded&) const = default;
};

struct Work {
    std::uint64_t encode_calls = 0;
    std::uint64_t encode_bytes = 0;
    std::uint64_t scan_bytes   = 0; // bytes examined by added-token std::string_view::find
    std::uint64_t added_hits   = 0;
};

// Legacy scanner copied from Tokenizer::encode, with restart trace and scan accounting.
static std::vector<int> encode_legacy_traced(const fi::Tokenizer& tk, std::string_view text,
                                             std::vector<Restart>* restarts, Work* work) {
    if (work) {
        ++work->encode_calls;
        work->encode_bytes += text.size();
    }
    std::vector<int> ids;
    if (text.empty()) { return ids; }
    std::size_t pos = 0;
    while (pos < text.size()) {
        std::size_t match_pos           = std::string_view::npos;
        const fi::AddedToken* match_tok = nullptr;
        for (const fi::AddedToken& token : tk.added_tokens_) {
            if (token.content.empty()) { continue; }
            const std::size_t found = text.find(token.content, pos);
            if (work) {
                work->scan_bytes += found == std::string_view::npos ? text.size() - pos
                                                                    : found - pos + token.content.size();
            }
            if (found == std::string_view::npos) { continue; }
            if (match_tok == nullptr || found < match_pos) {
                match_pos = found;
                match_tok = &token;
            }
        }
        if (match_tok == nullptr) {
            fi::append_bpe_ids(ids, text.substr(pos), tk.has_bpe_merges_, tk.bpe_merge_ranks_,
                               tk.vocab_token_to_id_);
            break;
        }
        if (match_pos > pos) {
            fi::append_bpe_ids(ids, text.substr(pos, match_pos - pos), tk.has_bpe_merges_,
                               tk.bpe_merge_ranks_, tk.vocab_token_to_id_);
        }
        ids.push_back(match_tok->id);
        pos = match_pos + match_tok->content.size();
        if (work) { ++work->added_hits; }
        if (restarts) { restarts->push_back({pos, ids.size()}); }
    }
    return ids;
}

// Same semantics (leftmost start, then lowest id), single forward scan.
struct FastScanner {
    std::array<std::vector<const fi::AddedToken*>, 256> by_first{};
    explicit FastScanner(const fi::Tokenizer& tk) {
        for (const fi::AddedToken& token : tk.added_tokens_) { // already sorted by id
            if (token.content.empty()) { continue; }
            by_first[static_cast<unsigned char>(token.content[0])].push_back(&token);
        }
    }
    std::vector<int> encode(const fi::Tokenizer& tk, std::string_view text,
                            std::vector<Restart>* restarts) const {
        std::vector<int> ids;
        std::size_t pos = 0;
        while (pos < text.size()) {
            std::size_t match_pos           = std::string_view::npos;
            const fi::AddedToken* match_tok = nullptr;
            for (std::size_t i = pos; i < text.size() && match_tok == nullptr; ++i) {
                const auto& bucket = by_first[static_cast<unsigned char>(text[i])];
                for (const fi::AddedToken* token : bucket) {
                    if (text.compare(i, token->content.size(), token->content) == 0) {
                        match_pos = i;
                        match_tok = token;
                        break;
                    }
                }
            }
            if (match_tok == nullptr) {
                fi::append_bpe_ids(ids, text.substr(pos), tk.has_bpe_merges_, tk.bpe_merge_ranks_,
                                   tk.vocab_token_to_id_);
                break;
            }
            if (match_pos > pos) {
                fi::append_bpe_ids(ids, text.substr(pos, match_pos - pos), tk.has_bpe_merges_,
                                   tk.bpe_merge_ranks_, tk.vocab_token_to_id_);
            }
            ids.push_back(match_tok->id);
            pos = match_pos + match_tok->content.size();
            if (restarts) { restarts->push_back({pos, ids.size()}); }
        }
        return ids;
    }
};

// Verbatim logic of processor.cpp::encode_rendered_chat at 44a2c6c, instrumented.
static Encoded legacy_encode_rendered_chat(const fi::Tokenizer& tk, const fi::RenderedChat& r,
                                           Work& work) {
    Encoded encoded;
    encoded.ids                = encode_legacy_traced(tk, r.text, nullptr, &work);
    const auto encode_boundary = [&](std::size_t byte_offset, bool allow_full,
                                     std::string_view name) -> std::uint32_t {
        if (byte_offset > r.text.size()) {
            throw std::logic_error(std::string(name) + " byte offset exceeds rendered chat");
        }
        std::vector<int> prefix;
        try {
            prefix = encode_legacy_traced(tk, std::string_view(r.text).substr(0, byte_offset),
                                          nullptr, &work);
        } catch (const std::exception&) {
            throw std::logic_error(std::string(name) + " cannot be tokenized independently");
        }
        if (prefix.empty() || (!allow_full && prefix.size() >= encoded.ids.size()) ||
            prefix.size() > encoded.ids.size() ||
            !std::equal(prefix.begin(), prefix.end(), encoded.ids.begin())) {
            throw std::logic_error(std::string(name) + " is not an exact token prefix");
        }
        return static_cast<std::uint32_t>(prefix.size());
    };
    if (r.stable_prefix_byte_offset) {
        encoded.stable = encode_boundary(*r.stable_prefix_byte_offset, true, "stable prefix");
    }
    if (r.turn_rewrite_byte_offset) {
        encoded.turn = encode_boundary(*r.turn_rewrite_byte_offset, false, "turn rewrite prefix");
    }
    if (r.user_turn_byte_offset && *r.user_turn_byte_offset > 0) {
        encoded.user = encode_boundary(*r.user_turn_byte_offset, false, "user turn prefix");
    }
    std::optional<std::uint32_t> previous;
    for (const fi::SemanticCheckpointByteHint& hint : r.checkpoint_hints) {
        const std::uint32_t b = encode_boundary(hint.byte_offset, true, "semantic checkpoint prefix");
        if (previous && b < *previous) {
            throw std::logic_error("semantic checkpoint boundaries are not ordered");
        }
        encoded.hints.push_back({static_cast<int>(hint.kind), b});
        previous = b;
    }
    return encoded;
}

// B1: one main encode with restart trace, then E(R[:b]) = T[:t_r] || E(R[r:b]) for the last
// completed added-token restart r <= b. Same call order, error names and allow_full rules.
static Encoded single_pass(const fi::Tokenizer& tk, const FastScanner* fast,
                           const fi::RenderedChat& r, std::vector<int> ids,
                           const std::vector<Restart>& restarts, Work& work) {
    Encoded encoded;
    encoded.ids = std::move(ids);
    struct Local {
        bool tokenizable = true;
        std::size_t n    = 0;
        bool matches     = false;
    };
    std::map<std::size_t, Local> memo;
    const auto resolve = [&](std::size_t b) -> const Local& {
        if (auto it = memo.find(b); it != memo.end()) { return it->second; }
        auto it = std::upper_bound(restarts.begin(), restarts.end(), b,
                                   [](std::size_t v, const Restart& x) { return v < x.first; });
        const std::size_t rb = it == restarts.begin() ? 0 : std::prev(it)->first;
        const std::size_t rt = it == restarts.begin() ? 0 : std::prev(it)->second;
        Local out;
        try {
            const std::string_view piece = std::string_view(r.text).substr(rb, b - rb);
            ++work.encode_calls;
            work.encode_bytes += piece.size();
            const std::vector<int> local =
                fast ? fast->encode(tk, piece, nullptr) : encode_legacy_traced(tk, piece, nullptr, nullptr);
            out.n       = rt + local.size();
            out.matches = out.n <= encoded.ids.size() &&
                          std::equal(local.begin(), local.end(), encoded.ids.begin() + static_cast<std::ptrdiff_t>(rt));
        } catch (const std::exception&) { out.tokenizable = false; }
        return memo.emplace(b, out).first->second;
    };
    const auto boundary = [&](std::size_t b, bool allow_full, std::string_view name) -> std::uint32_t {
        if (b > r.text.size()) {
            throw std::logic_error(std::string(name) + " byte offset exceeds rendered chat");
        }
        const Local& l = resolve(b);
        if (!l.tokenizable) {
            throw std::logic_error(std::string(name) + " cannot be tokenized independently");
        }
        if (l.n == 0 || (!allow_full && l.n >= encoded.ids.size()) || l.n > encoded.ids.size() ||
            !l.matches) {
            throw std::logic_error(std::string(name) + " is not an exact token prefix");
        }
        return static_cast<std::uint32_t>(l.n);
    };
    if (r.stable_prefix_byte_offset) {
        encoded.stable = boundary(*r.stable_prefix_byte_offset, true, "stable prefix");
    }
    if (r.turn_rewrite_byte_offset) {
        encoded.turn = boundary(*r.turn_rewrite_byte_offset, false, "turn rewrite prefix");
    }
    if (r.user_turn_byte_offset && *r.user_turn_byte_offset > 0) {
        encoded.user = boundary(*r.user_turn_byte_offset, false, "user turn prefix");
    }
    std::optional<std::uint32_t> previous;
    for (const fi::SemanticCheckpointByteHint& hint : r.checkpoint_hints) {
        const std::uint32_t b = boundary(hint.byte_offset, true, "semantic checkpoint prefix");
        if (previous && b < *previous) {
            throw std::logic_error("semantic checkpoint boundaries are not ordered");
        }
        encoded.hints.push_back({static_cast<int>(hint.kind), b});
        previous = b;
    }
    return encoded;
}

static fi::ChatMessage to_message(const Json& m) {
    fi::ChatMessage out;
    out.role = m.at("role").get<std::string>();
    if (m.contains("content") && m["content"].is_string()) {
        out.parts.push_back(fi::ChatPart::text_part(m["content"].get<std::string>()));
    }
    if (m.contains("reasoning_content") && m["reasoning_content"].is_string()) {
        out.reasoning_content = m["reasoning_content"].get<std::string>();
    }
    if (m.contains("tool_calls")) {
        for (const Json& call : m["tool_calls"]) {
            out.tool_calls.push_back({call.value("id", ""), call["function"]["name"].get<std::string>(),
                                      call["function"]["arguments"].get<std::string>()});
        }
    }
    if (m.contains("tool_call_id")) { out.tool_call_id = m["tool_call_id"].get<std::string>(); }
    return out;
}

static fi::RenderedChat render(const fi::CompiledChatTemplate& tpl, const Json& request) {
    std::vector<fi::ChatMessage> messages;
    for (const Json& m : request.at("messages")) { messages.push_back(to_message(m)); }
    fi::ChatRenderOptions options;
    options.add_generation_prompt    = true;
    options.enable_thinking          = true;
    options.reasoning_effort         = ninfer::ReasoningEffort::Medium;
    options.preserve_thinking        = true;
    options.prefix_checkpoint_policy = ninfer::PrefixCheckpointPolicy::RollingTool;
    if (request.contains("tools")) {
        for (const Json& tool : request["tools"]) { options.tool_jsons.push_back(tool.dump()); }
    }
    return tpl.render(messages, options);
}

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "usage: bench_ftc RESDIR SESSION.jsonl [--no-legacy] | bench_ftc RESDIR --raw FILE\n";
        return 2;
    }
    const std::string resdir = argv[1];
    const std::string tj  = read_file(resdir + "/tokenizer.json");
    const std::string tcj = read_file(resdir + "/tokenizer_config.json");
    const std::string gcj = read_file(resdir + "/generation_config.json");
    const std::string tpl_src = read_file(resdir + "/chat_template.jinja");
    const auto t_load0 = Clock::now();
    const fi::Tokenizer tk(fi::TokenizerResources{tj, tcj, gcj});
    const auto t_load1 = Clock::now();
    const fi::CompiledChatTemplate tpl = fi::CompiledChatTemplate::resolve(tpl_src);
    const FastScanner fast(tk);
    std::size_t max_added = 0;
    for (const auto& t : tk.added_tokens_) { max_added = std::max(max_added, t.content.size()); }

    if (std::string(argv[2]) == "--raw") {
        const std::string text = read_file(argv[3]);
        Work w;
        auto a = Clock::now();
        const auto legacy = encode_legacy_traced(tk, text, nullptr, &w);
        auto b = Clock::now();
        const auto quick = fast.encode(tk, text, nullptr);
        auto c = Clock::now();
        Json out{{"file", argv[3]}, {"bytes", text.size()}, {"tokens", legacy.size()},
                 {"legacy_s", secs(a, b)}, {"fastscan_s", secs(b, c)}, {"equal", legacy == quick},
                 {"scan_bytes", w.scan_bytes}, {"added_hits", w.added_hits},
                 {"legacy_MBps", text.size() / 1e6 / secs(a, b)}, {"fast_MBps", text.size() / 1e6 / secs(b, c)}};
        std::cout << out.dump() << "\n";
        return legacy == quick ? 0 : 1;
    }

    int legacy_turns = std::numeric_limits<int>::max();
    if (argc > 3 && std::string(argv[3]) == "--no-legacy") { legacy_turns = 0; }
    if (argc > 3 && std::string(argv[3]).rfind("--legacy-turns=", 0) == 0) {
        legacy_turns = std::stoi(std::string(argv[3]).substr(15));
    }
    std::ifstream in(argv[2]);
    std::string line;
    std::optional<fi::RenderedChat> prev_render;
    std::vector<int> prev_ids;
    std::vector<Restart> prev_restarts;
    int turn = 0;
    int failures = 0;
    std::cerr << "tokenizer_load_s=" << secs(t_load0, t_load1) << " added=" << tk.added_tokens_.size()
              << " max_added_bytes=" << max_added << "\n";
    while (std::getline(in, line)) {
        const Json row = Json::parse(line);
        const auto r0 = Clock::now();
        const fi::RenderedChat r = render(tpl, row.at("request"));
        const auto r1 = Clock::now();
        std::uint64_t sum_b = 0;
        std::size_t queries = r.checkpoint_hints.size();
        for (const auto& h : r.checkpoint_hints) { sum_b += h.byte_offset; }
        if (r.stable_prefix_byte_offset) { sum_b += *r.stable_prefix_byte_offset; ++queries; }
        if (r.turn_rewrite_byte_offset) { sum_b += *r.turn_rewrite_byte_offset; ++queries; }
        if (r.user_turn_byte_offset && *r.user_turn_byte_offset > 0) { sum_b += *r.user_turn_byte_offset; ++queries; }

        Json out{{"case", row.value("case_id", "")}, {"turn", turn}, {"messages", row["request"]["messages"].size()},
                 {"render_bytes", r.text.size()}, {"render_s", secs(r0, r1)}, {"boundary_queries", queries},
                 {"hints", r.checkpoint_hints.size()},
                 {"legacy_requested_bytes", r.text.size() + sum_b},
                 {"amplification", static_cast<double>(r.text.size() + sum_b) / r.text.size()}};

        // One full encode with the legacy scanner (what B1 still pays) + trace.
        Work wfull;
        std::vector<Restart> restarts;
        auto a = Clock::now();
        std::vector<int> ids = encode_legacy_traced(tk, r.text, &restarts, &wfull);
        auto b = Clock::now();
        out["tokens"]          = ids.size();
        out["added_hits"]      = wfull.added_hits;
        out["full_encode_s"]   = secs(a, b);
        out["full_scan_bytes"] = wfull.scan_bytes;

        std::vector<Restart> frestarts;
        a = Clock::now();
        std::vector<int> fids = fast.encode(tk, r.text, &frestarts);
        b = Clock::now();
        out["full_encode_fastscan_s"] = secs(a, b);
        const bool fast_equal = fids == ids && frestarts == restarts;
        out["fastscan_equal"] = fast_equal;
        failures += fast_equal ? 0 : 1;

        // Pure BPE share: encode ordinary segments only (no added-token search).
        {
            std::vector<int> scratch;
            std::size_t pos = 0;
            a = Clock::now();
            for (std::size_t k = 0; k < restarts.size(); ++k) {
                const std::size_t end = restarts[k].first;
                // token content length = restarts[k].first - start_of_token; recover from id
                const int id = ids[restarts[k].second - 1];
                std::size_t len = 0;
                for (const auto& t : tk.added_tokens_) { if (t.id == id) { len = t.content.size(); break; } }
                const std::size_t start = end - len;
                if (start > pos) {
                    fi::append_bpe_ids(scratch, std::string_view(r.text).substr(pos, start - pos), tk.has_bpe_merges_,
                                       tk.bpe_merge_ranks_, tk.vocab_token_to_id_);
                }
                pos = end;
            }
            if (pos < r.text.size()) {
                fi::append_bpe_ids(scratch, std::string_view(r.text).substr(pos), tk.has_bpe_merges_,
                                   tk.bpe_merge_ranks_, tk.vocab_token_to_id_);
            }
            b = Clock::now();
            out["bpe_only_s"] = secs(a, b);
        }

        Encoded legacy;
        bool have_legacy = false;
        if (turn < legacy_turns) {
            Work wl;
            a = Clock::now();
            legacy = legacy_encode_rendered_chat(tk, r, wl);
            b = Clock::now();
            have_legacy = true;
            out["legacy_s"]            = secs(a, b);
            out["legacy_encode_calls"] = wl.encode_calls;
            out["legacy_encode_bytes"] = wl.encode_bytes;
            out["legacy_scan_bytes"]   = wl.scan_bytes;
        }

        // B1 with the legacy scanner, and B1 with the single-pass scanner.
        {
            Work w;
            a = Clock::now();
            std::vector<Restart> rs;
            std::vector<int> main_ids = encode_legacy_traced(tk, r.text, &rs, nullptr);
            Encoded e = single_pass(tk, nullptr, r, std::move(main_ids), rs, w);
            b = Clock::now();
            out["b1_s"]              = secs(a, b);
            out["b1_local_bytes"]    = w.encode_bytes;
            out["b1_local_calls"]    = w.encode_calls;
            if (have_legacy) {
                const bool eq = e == legacy;
                out["b1_equal_legacy"] = eq;
                failures += eq ? 0 : 1;
            } else {
                // Reference for later candidates when legacy is skipped on this turn.
                legacy      = e;
                have_legacy = true;
                out["reference"] = "b1-legacy-scanner";
            }
        }
        {
            Work w;
            a = Clock::now();
            std::vector<Restart> rs;
            std::vector<int> main_ids = fast.encode(tk, r.text, &rs);
            Encoded e = single_pass(tk, &fast, r, std::move(main_ids), rs, w);
            b = Clock::now();
            out["b1_fastscan_s"] = secs(a, b);
            if (have_legacy) {
                const bool eq = e == legacy;
                out["b1_fastscan_equal_legacy"] = eq;
                failures += eq ? 0 : 1;
            }
        }

        // B0: legacy boundary algorithm (every prefix re-encoded from byte 0) with only the
        // added-token scan replaced by the single-pass scanner.
        if (std::getenv("FTC_B0") != nullptr) {
            Encoded e;
            a = Clock::now();
            e.ids = fast.encode(tk, r.text, nullptr);
            const auto prefix_len = [&](std::size_t off) {
                return static_cast<std::uint32_t>(
                    fast.encode(tk, std::string_view(r.text).substr(0, off), nullptr).size());
            };
            if (r.stable_prefix_byte_offset) { e.stable = prefix_len(*r.stable_prefix_byte_offset); }
            if (r.turn_rewrite_byte_offset) { e.turn = prefix_len(*r.turn_rewrite_byte_offset); }
            if (r.user_turn_byte_offset && *r.user_turn_byte_offset > 0) {
                e.user = prefix_len(*r.user_turn_byte_offset);
            }
            for (const auto& hint : r.checkpoint_hints) {
                e.hints.push_back({static_cast<int>(hint.kind), prefix_len(hint.byte_offset)});
            }
            b = Clock::now();
            out["b0_fastscan_legacy_boundaries_s"] = secs(a, b);
            if (have_legacy) {
                const bool eq = e == legacy;
                out["b0_equal_reference"] = eq;
                failures += eq ? 0 : 1;
            }
        }

        // B2 emulation: LCP with previous render, largest restart r with r + (M-1) <= LCP.
        if (prev_render) {
            const std::string& o = prev_render->text;
            std::size_t lcp = 0;
            const std::size_t lim = std::min(o.size(), r.text.size());
            while (lcp < lim && o[lcp] == r.text[lcp]) { ++lcp; }
            const std::size_t guard = max_added == 0 ? 0 : max_added - 1;
            std::size_t cut_b = 0, cut_t = 0;
            for (const Restart& x : prev_restarts) {
                if (lcp >= guard && x.first <= lcp - guard) { cut_b = x.first; cut_t = x.second; }
            }
            Work w;
            a = Clock::now();
            std::vector<Restart> suffix_rs;
            std::vector<int> suffix = fast.encode(tk, std::string_view(r.text).substr(cut_b), &suffix_rs);
            std::vector<int> joined(prev_ids.begin(), prev_ids.begin() + static_cast<std::ptrdiff_t>(cut_t));
            joined.insert(joined.end(), suffix.begin(), suffix.end());
            std::vector<Restart> joined_rs;
            for (const Restart& x : prev_restarts) { if (x.first <= cut_b) { joined_rs.push_back(x); } }
            for (const Restart& x : suffix_rs) { joined_rs.push_back({x.first + cut_b, x.second + cut_t}); }
            Encoded e = single_pass(tk, &fast, r, joined, joined_rs, w);
            b = Clock::now();
            out["b2_lcp_bytes"]      = lcp;
            out["b2_cut_bytes"]      = cut_b;
            out["b2_suffix_bytes"]   = r.text.size() - cut_b;
            out["b2_s"]              = secs(a, b);
            const bool eq_tokens     = joined == ids;
            out["b2_tokens_equal_full"] = eq_tokens;
            failures += eq_tokens ? 0 : 1;
            if (have_legacy) {
                const bool eq = e == legacy;
                out["b2_equal_legacy"] = eq;
                failures += eq ? 0 : 1;
            }
        }
        std::cout << out.dump() << std::endl;
        prev_render   = r;
        prev_ids      = ids;
        prev_restarts = restarts;
        ++turn;
    }
    std::cerr << "failures=" << failures << "\n";
    return failures == 0 ? 0 : 1;
}
