from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    left_counts = Counter((r.merchant_order_id, r.provider_txn_id) for r in left_list)
    right_counts = Counter((r.merchant_order_id, r.provider_txn_id) for r in right_list)

    all_keys = set(left_counts.keys()) | set(right_counts.keys())
    discrepancies: list[Discrepancy] = []

    for key in all_keys:
        merchant_order_id, provider_txn_id = key
        left_count = left_counts[key]
        right_count = right_counts[key]

        if left_count > right_count:
            discrepancies.append(Discrepancy(
                kind="duplicate_left",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Left has {left_count} occurrences, Right has {right_count}"
            ))
        elif right_count > left_count:
            discrepancies.append(Discrepancy(
                kind="missing_left",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Left has {left_count} occurrences, Right has {right_count}"
            ))

        # Check for amount mismatch if both have at least one occurrence
        if left_count > 0 and right_count > 0:
            left_amounts = [r.amount_cents for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key]
            right_amounts = [r.amount_cents for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key]
            if set(left_amounts) != set(right_amounts):
                discrepancies.append(Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Left amounts: {left_amounts}, Right amounts: {right_amounts}"
                ))

    # Missing right: keys only in right
    for key in right_counts:
        if key not in left_counts:
            merchant_order_id, provider_txn_id = key
            discrepancies.append(Discrepancy(
                kind="missing_right",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Right has {right_counts[key]} occurrences, Left has 0"
            ))

    return discrepancies
