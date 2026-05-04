from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left = list(left_rows)
    right = list(right_rows)
    
    left_key = lambda r: (r.merchant_order_id, r.provider_txn_id)
    right_key = lambda r: (r.merchant_order_id, r.provider_txn_id)
    
    left_counter = Counter(left_key(r) for r in left)
    right_counter = Counter(right_key(r) for r in right)
    
    left_dict = {left_key(r): r for r in left}
    right_dict = {right_key(r): r for r in right}
    
    discrepancies = []
    
    left_keys = set(left_counter.keys())
    right_keys = set(right_counter.keys())
    
    for key in left_keys - right_keys:
        discrepancies.append(Discrepancy("missing_right", key[0], key[1], f"missing in right: {key}"))
    
    for key in right_keys - left_keys:
        discrepancies.append(Discrepancy("missing_left", key[0], key[1], f"missing in left: {key}"))
    
    for key in left_keys & right_keys:
        left_row = left_dict[key]
        right_row = right_dict[key]
        if left_row.amount_cents != right_row.amount_cents:
            discrepancies.append(Discrepancy("amount_mismatch", key[0], key[1], f"left={left_row.amount_cents} right={right_row.amount_cents}"))
    
    for key, count in left_counter.items():
        if count > 1:
            discrepancies.append(Discrepancy("duplicate_left", key[0], key[1], f"duplicate count={count}"))
    
    return discrepancies
