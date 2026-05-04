from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    left_counter = Counter((r.merchant_order_id, r.provider_txn_id) for r in left_list)
    right_counter = Counter((r.merchant_order_id, r.provider_txn_id) for r in right_list)

    left_dict = {(r.merchant_order_id, r.provider_txn_id): r for r in left_list}
    right_dict = {(r.merchant_order_id, r.provider_txn_id): r for r in right_list}

    discrepancies: list[Discrepancy] = []

    all_keys = set(left_counter.keys()) | set(right_counter.keys())

    for key in all_keys:
        mo_id, pt_id = key
        left_count = left_counter.get(key, 0)
        right_count = right_counter.get(key, 0)

        if left_count > 1:
            discrepancies.append(Discrepancy("duplicate_left", mo_id, pt_id, f"appears {left_count} times on left"))

        if left_count == 0:
            discrepancies.append(Discrepancy("missing_left", mo_id, pt_id, "not found on left"))
        elif right_count == 0:
            discrepancies.append(Discrepancy("missing_right", mo_id, pt_id, "not found on right"))
        else:
            left_row = left_dict[key]
            right_row = right_dict[key]
            if left_row.amount_cents != right_row.amount_cents:
                discrepancies.append(Discrepancy("amount_mismatch", mo_id, pt_id, f"left={left_row.amount_cents}, right={right_row.amount_cents}"))

    return discrepancies
