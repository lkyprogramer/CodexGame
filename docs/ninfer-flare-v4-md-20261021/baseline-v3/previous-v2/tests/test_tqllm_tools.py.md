# V2 支撑材料：`tests/test_tqllm_tools.py`

> 原样文本归档，不是 V3 新增实现；旧 P7—P12 状态只作历史记录。恢复方式见根目录 `support/REHYDRATE.md`。

<!-- payload-path: tests/test_tqllm_tools.py -->
<!-- payload-sha256: 8358598debd1f4280d5a3c4042c28a87dda9e7bd40cf9c66fa596efe662c4105 -->
<!-- payload-bytes: 6506 -->

<!-- payload-begin -->
````python
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tqllm_tools import estimate_budget, eligible_remote_chunks, select_pages, summarize_rounds

GiB = 1 << 30

def budget():
    return dict(total_gpu_bytes=24*GiB, baseline_gpu_peak_bytes=22*GiB,
                total_host_bytes=64*GiB, baseline_host_peak_bytes=24*GiB,
                draft_weights_bytes=GiB//2, draft_layers=5, draft_kv_heads=8,
                draft_head_dim=128, draft_hidden=5120, target_feature_layers=5,
                aggregate_archive_tokens=262144, gpu_ring_rows=2176,
                resident_draft_lanes=1, staging_bytes=64<<20, index_bytes=20<<20,
                scratch_bytes=64<<20, graph_bytes=64<<20, draft_head_extra_bytes=0,
                checkpoint_bytes=0, pinned_transfer_bytes=32<<20,
                gpu_reserve_bytes=512<<20, host_reserve_bytes=8*GiB,
                archive_kind="projected_bf16", inputs_measured=False,
                reclaimed_gpu_bytes=0, reclaim_evidence="")

class BudgetTests(unittest.TestCase):
    def test_full_draft_kv_is_five_gib(self):
        r=estimate_budget(budget());self.assertEqual(r["draft_kv_bytes_per_token"],20480)
        self.assertEqual(r["hypothetical_full_draft_kv_bytes"],5*GiB)
    def test_projected_archive_is_two_point_five_gib(self):
        self.assertEqual(estimate_budget(budget())["host_archive_bytes"],5*GiB//2)
    def test_raw_features_are_not_free(self):
        b=budget();b["archive_kind"]="raw_features_bf16"
        self.assertEqual(estimate_budget(b)["host_archive_bytes"],25*GiB//2)
    def test_ring_scales_with_lanes_not_context(self):
        b=budget();r=estimate_budget(b);b["resident_draft_lanes"]=4
        self.assertEqual(estimate_budget(b)["gpu_ring_bytes"],r["gpu_ring_bytes"]*4)
    def test_archive_scales_with_aggregate_tokens(self):
        b=budget();r=estimate_budget(b);b["aggregate_archive_tokens"]*=2
        s=estimate_budget(b);self.assertEqual(s["host_archive_bytes"],r["host_archive_bytes"]*2)
        self.assertEqual(s["gpu_ring_bytes"],r["gpu_ring_bytes"])
    def test_illustrative_never_qualified(self):
        self.assertEqual(estimate_budget(budget())["verdict"],"ILLUSTRATIVE_ONLY")
    def test_measured_fit_is_only_budget_go(self):
        b=budget();b["inputs_measured"]=True
        self.assertEqual(estimate_budget(b)["verdict"],"BUDGET_GO_NOT_GPU_QUALIFIED")
    def test_reserve_enforced(self):
        b=budget();b["baseline_gpu_peak_bytes"]=24*GiB;b["inputs_measured"]=True
        self.assertFalse(estimate_budget(b)["fits_with_reserve"])
        self.assertEqual(estimate_budget(b)["verdict"],"BUDGET_NO_GO")
    def test_host_budget_enforced(self):
        b=budget();b["baseline_host_peak_bytes"]=60*GiB
        self.assertFalse(estimate_budget(b)["fits_with_reserve"])
    def test_negative_rejected(self):
        b=budget();b["graph_bytes"]=-1
        with self.assertRaises(ValueError):estimate_budget(b)
    def test_bool_rejected_as_integer(self):
        b=budget();b["draft_layers"]=True
        with self.assertRaises(ValueError):estimate_budget(b)
    def test_unknown_archive_rejected(self):
        b=budget();b["archive_kind"]="target_kv"
        with self.assertRaises(ValueError):estimate_budget(b)
    def test_reclaim_requires_evidence(self):
        b=budget();b["reclaimed_gpu_bytes"]=1
        with self.assertRaises(ValueError):estimate_budget(b)
    def test_reclaim_cannot_exceed_baseline(self):
        b=budget();b["reclaimed_gpu_bytes"]=25*GiB;b["reclaim_evidence"]="owned-slabs.json"
        with self.assertRaises(ValueError):estimate_budget(b)
    def test_missing_size_rejected(self):
        b=budget();del b["scratch_bytes"]
        with self.assertRaises(ValueError):estimate_budget(b)

class RetrievalOracleTests(unittest.TestCase):
    def test_262k_includes_oldest_not_only_4096(self):
        ids=eligible_remote_chunks(262144,1536)
        self.assertEqual(ids[0],0);self.assertEqual(len(ids),16288)
        self.assertGreater(len(ids),4096)
    def test_empty_prefix(self):self.assertEqual(eligible_remote_chunks(10,1536),[])
    def test_partial_chunk_not_out_of_bounds(self):
        ids=eligible_remote_chunks(104,32)
        self.assertTrue(all((i+1)*16<=72 for i in ids));self.assertEqual(len(ids),4)
    def test_negative_recent_rejected(self):
        with self.assertRaises(ValueError):eligible_remote_chunks(100,-1)
    def test_zero_chunk_rejected(self):
        with self.assertRaises(ValueError):eligible_remote_chunks(100,10,0)
    def test_page_ties_stable(self):self.assertEqual(select_pages({9:1.0,0:1.0,4:2.0},2),[4,0])
    def test_nan_score_rejected(self):
        with self.assertRaises(ValueError):select_pages({0:float("nan")},1)
    def test_zero_page_budget(self):self.assertEqual(select_pages({0:1},0),[])

class RoundCostTests(unittest.TestCase):
    def rows(self):return [dict(committed_tokens=4,accepted_drafts=3,drafted_tokens=5,round_wall_ns=20_000_000),
                           dict(committed_tokens=1,accepted_drafts=0,drafted_tokens=5,round_wall_ns=30_000_000)]
    def test_uses_committed_including_bonus(self):
        r=summarize_rounds(self.rows());self.assertEqual(r["effective_tokens_per_second"],100.0)
        self.assertEqual(r["draft_acceptance"],.3)
    def test_zero_acceptance_can_commit_one(self):
        r=summarize_rounds(self.rows()[1:]);self.assertAlmostEqual(r["effective_tokens_per_second"],1000/30)
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):summarize_rounds([])
    def test_nonpositive_time_rejected(self):
        rows=self.rows();rows[0]["round_wall_ns"]=0
        with self.assertRaises(ValueError):summarize_rounds(rows)
    def test_more_accepted_than_proposed_rejected(self):
        rows=self.rows();rows[0]["accepted_drafts"]=6
        with self.assertRaises(ValueError):summarize_rounds(rows)
    def test_too_many_committed_rejected(self):
        rows=self.rows();rows[0]["committed_tokens"]=5
        with self.assertRaises(ValueError):summarize_rounds(rows)
    def test_cancelled_zero_commit_allowed(self):
        rows=self.rows();rows[0]["committed_tokens"]=0
        self.assertEqual(summarize_rounds(rows)["committed_tokens"],1)
    def test_no_drafts(self):
        r=summarize_rounds([dict(committed_tokens=1,accepted_drafts=0,drafted_tokens=0,round_wall_ns=1)])
        self.assertIsNone(r["draft_acceptance"])

if __name__=="__main__":unittest.main()
````
<!-- payload-end -->
