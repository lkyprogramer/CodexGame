from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)
    
    # Group by (merchant_order_id, provider_txn_id)
    left_map: dict[tuple[str, str], list[Row]] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        if key not in left_map:
            left_map[key] = []
        left_map[key].append(row)
    
    right_map: dict[tuple[str, str], list[Row]] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        if key not in right_map:
            right_map[key] = []
        right_map[key].append(row)
    
    discrepancies: list[Discrepancy] = []
    
    # Check for duplicates on left
    for key, rows in left_map.items():
        if len(rows) > 1:
            discrepancies.append(Discrepancy(
                kind="duplicate_left",
                merchant_order_id=key[0],
                provider_txn_id=key[1],
                detail=f"Duplicate found on left"
            ))
    
    # Check for missing right (in left but not in right)
    for key in left_map:
        if key not in right_map:
            discrepancies.append(Discrepancy(
                kind="missing_right",
                merchant_order_id=key[0],
                provider_txn_id=key[1],
                detail="Found on left but not on right"
            ))
    
    # Check for missing left (in right but not in left)
    for key in right_map:
        if key not in left_map:
            discrepancies.append(Discrepancy(
                kind="missing_left",
                merchant_order_id=key[0],
                provider_txn_id=key[1],
                detail="Found on right but not on left"
            ))
    
    # Check for amount mismatch (same key on both sides, different amounts)
    for key in left_map:
        if key in right_map:
            left_amount = left_map[key][0].amount_cents
            right_amount = right_map[key][0].amount_cents
            if left_amount != right_amount:
                discrepancies.append(Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"Amount differs: left={left_amount}, right={right_amount}"
                ))
    
    return discrepancies
