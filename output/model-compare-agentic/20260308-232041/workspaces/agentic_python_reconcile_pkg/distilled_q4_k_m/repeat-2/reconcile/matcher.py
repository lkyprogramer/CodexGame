from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    # Create tuples for comparison (merchant_order_id, provider_txn_id)
    left_list = list(left_rows)
    right_list = list(right_rows)
    
    # Count occurrences for duplicate detection
    left_counter = Counter((r.merchant_order_id, r.provider_txn_id) for r in left_list)
    right_counter = Counter((r.merchant_order_id, r.provider_txn_id) for r in right_list)
    
    # Track unique keys
    left_keys = set(left_counter.keys())
    right_keys = set(right_counter.keys())
    
    discrepancies: list[Discrepancy] = []
    
    # Find missing_left (in right but not in left)
    for key in right_keys - left_keys:
        merchant_order_id, provider_txn_id = key
        row = next(r for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key)
        discrepancies.append(Discrepancy(
            kind="missing_left",
            merchant_order_id=merchant_order_id,
            provider_txn_id=provider_txn_id,
            detail=f"Row exists in right but not in left"
        ))
    
    # Find missing_right (in left but not in right)
    for key in left_keys - right_keys:
        merchant_order_id, provider_txn_id = key
        row = next(r for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key)
        discrepancies.append(Discrepancy(
            kind="missing_right",
            merchant_order_id=merchant_order_id,
            provider_txn_id=provider_txn_id,
            detail=f"Row exists in left but not in right"
        ))
    
    # Find amount mismatches and duplicates
    for key in left_keys & right_keys:
        merchant_order_id, provider_txn_id = key
        left_count = left_counter[key]
        right_count = right_counter[key]
        
        # Check for duplicates in left
        if left_count > 1:
            discrepancies.append(Discrepancy(
                kind="duplicate_left",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Duplicate found {left_count} times in left"
            ))
        
        # Check for amount mismatch
        left_row = next(r for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key)
        right_row = next(r for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key)
        if left_row.amount_cents != right_row.amount_cents:
            discrepancies.append(Discrepancy(
                kind="amount_mismatch",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Left amount: {left_row.amount_cents}, Right amount: {right_row.amount_cents}"
            ))
    
    return discrepancies
