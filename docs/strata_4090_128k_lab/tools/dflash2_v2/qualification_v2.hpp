#pragma once
#include "qualification_compare.hpp"
#include <algorithm>
#include <array>
#include <cstdio>

// The v1 comparator remains unchanged. Only its full-drafter confidence
// distance is diagnostic; finite/range checks apply to both backends.
struct Df01V2Result {
    bool legacy_pass = false;
    bool hard_pass = false;
    bool confidence_difference = false;
    std::string legacy_reason, hard_reason;
    std::array<float, 7> actual{}, reference{};
};

inline Df01V2Result df01_compare_v2(
    const std::vector<float>& got, const std::vector<float>& ref,
    const int32_t* tokens, const int32_t* expected,
    const float* probabilities, const float* wanted,
    const std::vector<int32_t>& vocabulary) {
    Df01V2Result r;
    r.legacy_pass = df01_compare(got, ref, tokens, expected, probabilities, wanted, r.legacy_reason);
    // Preserve v1 row/token/actual-probability gates. The reference probability
    // validity and both token domains are checked explicitly below.
    r.hard_pass = df01_compare(got, ref, tokens, expected, probabilities, probabilities, r.hard_reason);
    for (int i = 0; i < 7; ++i) {
        r.actual[i] = probabilities[i]; r.reference[i] = wanted[i];
        const bool valid = std::isfinite(probabilities[i]) && std::isfinite(wanted[i]) &&
            probabilities[i] >= 0 && probabilities[i] <= 1 && wanted[i] >= 0 && wanted[i] <= 1;
        if (!valid) { r.hard_pass = false; r.hard_reason = "probability validity " + std::to_string(i); }
        if (valid && std::abs(probabilities[i] - wanted[i]) > 0.05f) r.confidence_difference = true;
        if (std::find(vocabulary.begin(), vocabulary.end(), tokens[i]) == vocabulary.end() ||
            std::find(vocabulary.begin(), vocabulary.end(), expected[i]) == vocabulary.end()) {
            r.hard_pass = false; r.hard_reason = "token domain " + std::to_string(i);
        }
    }
    return r;
}

inline bool df01_write_v2(const std::string& path, const Df01V2Result& r) {
    std::FILE* f = std::fopen(path.c_str(), "wbx");
    if (!f) return false;
    auto quote = [&](const std::string& value) {
        std::fputc('"', f);
        for (unsigned char c : value) {
            if (c == '"' || c == '\\') std::fputc('\\', f);
            if (c < 32) std::fprintf(f, "\\u%04x", unsigned(c)); else std::fputc(c, f);
        }
        std::fputc('"', f);
    };
    auto number = [&](float value) {
        if (std::isfinite(value)) std::fprintf(f, "%.9g", double(value)); else std::fputs("null", f);
    };
    std::fprintf(f, "{\"schema\":\"df01-v2-drafter/1\",\"legacy_v1_numeric_result\":\"%s\",\"legacy_reason\":", r.legacy_pass ? "PASS" : "FAIL");
    quote(r.legacy_reason);
    std::fprintf(f, ",\"v2_confidence_diagnostic\":{\"limit\":0.05,\"threshold_exceeded\":%s,\"values\":[", r.confidence_difference ? "true" : "false");
    for (int i = 0; i < 7; ++i) {
        if (i) std::fputc(',', f);
        std::fprintf(f, "{\"index\":%d,\"actual\":", i); number(r.actual[i]);
        std::fputs(",\"reference\":", f); number(r.reference[i]);
        std::fputs(",\"abs_diff\":", f); number(std::abs(r.actual[i] - r.reference[i]));
        std::fputc('}', f);
    }
    std::fprintf(f, "]},\"v2_hard_gates\":{\"drafter_rows_tokens_probability_validity\":\"%s\",\"reason\":", r.hard_pass ? "PASS" : "FAIL");
    quote(r.hard_reason);
    std::fputs(",\"independent_selector\":\"NOT_RUN\",\"target_sampling\":\"NOT_RUN\",\"commit_state\":\"NOT_RUN\",\"EOS\":\"NOT_RUN\",\"resources_and_activation\":\"NOT_RUN\"},\"D1_v2_qualified\":false}\n", f);
    const bool ok = std::ferror(f) == 0;
    return std::fclose(f) == 0 && ok;
}
