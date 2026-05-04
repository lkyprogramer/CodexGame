from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    discrepancies: list[Discrepancy] = []

    left_counter = Counter((r.merchant_order_id, r.provider_txn_id) for r in left_list)
    right_counter = Counter((r.merchant_order_id, r.provider_txn_id) for r in right_list)

    left_set = set(left_counter.keys())
    right_set = set(right_counter.keys())

    # missing_right: in left but not in right
    for key in left_set - right_set:
        merchant_order_id, provider_txn_id = key
        # Find the row in left to get amount/status for detail
        row = next(r for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key)
        discrepancies.append(
            Discrepancy(
                kind="missing_right",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Found in left but not in right: {row.amount_cents} cents, {row.status}",
            )
        )

    # missing_left: in right but not in left
    for key in right_set - left_set:
        merchant_order_id, provider_txn_id = key
        row = next(r for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key)
        discrepancies.append(
            Discrepancy(
                kind="missing_left",
                merchant_order_id=merchant_order_id,
                provider_txn_id=provider_txn_id,
                detail=f"Found in right but not in left: {row.amount_cents} cents, {row.status}",
            )
        )

    # amount_mismatch: in both but different amount
    for key in left_set & right_set:
        merchant_order_id, provider_txn_id = key
        left_row = next(r for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key)
        right_row = next(r for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key)
        if left_row.amount_cents != right_row.amount_cents:
            discrepancies.append(
                Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Left: {left_row.amount_cents} cents, Right: {right_row.amount_cents} cents",
                )
            )

    # duplicate_left: appears more than once in left
    for key, count in left_counter.items():
        if count > 1:
            merchant_order_id, provider_txn_id = key
            row = next(r for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key)
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Appears {count} times in left: {row.amount_cents} cents, {row.status}",
                )
            )

    return discrepancies
