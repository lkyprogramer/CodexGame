#pragma once
// Planned interface specification, not linked into the current NInfer binary.
#include <cstdint>
#include <span>
#include <vector>
namespace ninfer::lab_contract {
using TokenId = std::uint32_t;
enum class Origin { Mtp, Suffix, DFlash2 };
enum class QKind { PointMass, Sparse16, NativeMtp };
struct SparseQRow { std::vector<TokenId> ids; std::vector<float> probabilities; };
struct ProposalBatch {
  Origin origin;
  QKind q_kind;
  std::uint64_t target_frontier;
  std::uint32_t physical_width; // anchor + maximum proposals
  std::uint32_t live_proposals;
  std::vector<TokenId> drafts;
  std::vector<SparseQRow> actual_conditional_q;
  std::uint64_t opaque_native_q_lifetime; // resolved only by the existing MTP owner
};
struct CommitDecision { std::uint32_t licensed, committed; bool terminal, cancelled; };
struct RoundMetrics {
  std::uint64_t round_id;
  std::uint32_t proposed, accepted, licensed, committed;
  double round_wall_ms, lookup_ms, catchup_ms;
};
// An owning implementation must validate support, q normalization, widths,
// frontiers, request identity and lifetimes before exposing the batch to Verify.
}
