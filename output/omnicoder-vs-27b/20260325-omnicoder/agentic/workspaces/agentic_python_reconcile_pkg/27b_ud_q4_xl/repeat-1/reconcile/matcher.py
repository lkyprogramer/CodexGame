from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)
    
    def key(row: Row) -> tuple[str, str]:
        return (row.merchant_order_id, row.provider_txn_id)
    
    left_counts = Counter(key(r) for r in left_list)
    right_counts = Counter(key(r) for r in right_list)
    
    left_unique = {k: r for k, r in zip(key(r) for r in left_list, left_list) if left_counts[k] == 1}
    right_unique = {k: r for k, r in zip(key(r) for r in right_list, right_list) if right_counts[k] == 1}
    
    discrepancies: list[Discrepancy] = []
    
    # Find duplicates in left
    for k, count in left_counts.items():
        if count > 1:
            row = next(r for r in left_list if key(r) == k)
            discrepancies.append(Discrepancy(
                kind="duplicate_left",
                merchant_order_id=row.merchant_order_id,
                provider_txn_id=row.provider_txn_id,
                detail=f"Appears {count} times in left"
            ))
    
    # Find missing_right (in left but not in right)
    for k in left_counts:
        if k not in right_counts:
            row = left_unique.get(k)
            if row:
                discrepancies.append(Discrepancy(
                    kind="missing_right",
                    merchant_order_id=row.merchant_order_id,
                    provider_txn_id=row.provider_txn_id,
                    detail="Not found in right"
                ))
    
    # Find missing_left (in right but not in left)
    for k in right_counts:
        if k not in left_counts:
            row = right_unique.get(k)
            if row:
                discrepancies.append(Discrepancy(
                    kind="missing_left",
                    merchant_order_id=row.merchant_order_id,
                    provider_txn_id=row.provider_txn_id,
                    detail="Not found in left"
                ))
    
    # Find amount mismatches (in both but different amounts)
    for k in left_counts:
        if k in right_counts:
            left_row = left_unique.get(k)
            right_row = right_unique.get(k)
            if left_row and right_row and left_row.amount_cents != right_row.amount_cents:
                discrepancies.append(Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=left_row.merchant_order_id,
                    provider_txn_id=left_row.provider_txn_id,
                    detail=f"Left: {left_row.amount_cents}, Right: {right_row.amount_cents}"
                ))
    
    return discrepancies
