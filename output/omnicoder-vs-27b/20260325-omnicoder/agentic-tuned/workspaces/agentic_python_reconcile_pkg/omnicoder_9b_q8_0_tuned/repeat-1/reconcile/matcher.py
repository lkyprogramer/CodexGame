from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_map: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    right_map: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    for row in left_rows:
        key = (row.merchant_order_id, row.provider_txn_id)
        left_map[row.merchant_order_id][key] += row.amount_cents
    
    for row in right_rows:
        key = (row.merchant_order_id, row.provider_txn_id)
        right_map[row.merchant_order_id][key] += row.amount_cents
    
    discrepancies: list[Discrepancy] = []
    
    all_merchant_ids = set(left_map.keys()) | set(right_map.keys())
    
    for mid in all_merchant_ids:
        left_side = left_map.get(mid, {})
        right_side = right_map.get(mid, {})
        
        left_keys = set(left_side.keys())
        right_keys = set(right_side.keys())
        
        only_left = left_keys - right_keys
        only_right = right_keys - left_keys
        common = left_keys & right_keys
        
        for key in only_left:
            discrepancies.append(Discrepancy(
                kind="duplicate_left",
                merchant_order_id=mid,
                provider_txn_id=key[1],
                detail=f"Duplicate entry on left for {key[1]}"
            ))
        
        for key in only_right:
            discrepancies.append(Discrepancy(
                kind="missing_left",
                merchant_order_id=mid,
                provider_txn_id=key[1],
                detail=f"Missing on left for {key[1]}"
            ))
        
        for key in common:
            left_total = left_side[key]
            right_total = right_side[key]
            if left_total != right_total:
                discrepancies.append(Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=mid,
                    provider_txn_id=key[1],
                    detail=f"Amount mismatch: left={left_total}, right={right_total}"
                ))
    
    return discrepancies


def render_summary(discrepancies: list[Discrepancy]) -> str:
    counts = defaultdict(int)
    for d in discrepancies:
        counts[d.kind] += 1
    
    parts = []
    for kind in sorted(counts.keys()):
        parts.append(f"{kind}={counts[kind]}")
    
    if not parts:
        return "no discrepancies"
    
    return "; ".join(parts)