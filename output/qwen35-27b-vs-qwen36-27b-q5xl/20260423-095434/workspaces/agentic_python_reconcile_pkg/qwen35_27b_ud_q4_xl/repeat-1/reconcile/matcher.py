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
        # Find one matching row from left to get details
        for r in left_list:
            if r.merchant_order_id == merchant_order_id and r.provider_txn_id == provider_txn_id:
                discrepancies.append(
                    Discrepancy(
                        kind="missing_right",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Found in left but not in right",
                    )
                )
                break

    # missing_left: in right but not in left
    for key in right_set - left_set:
        merchant_order_id, provider_txn_id = key
        # Find one matching row from right to get details
        for r in right_list:
            if r.merchant_order_id == merchant_order_id and r.provider_txn_id == provider_txn_id:
                discrepancies.append(
                    Discrepancy(
                        kind="missing_left",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Found in right but not in left",
                    )
                )
                break

    # amount_mismatch: same key in both but different amount
    for key in left_set & right_set:
        merchant_order_id, provider_txn_id = key
        left_amounts = [r.amount_cents for r in left_list if r.merchant_order_id == merchant_order_id and r.provider_txn_id == provider_txn_id]
        right_amounts = [r.amount_cents for r in right_list if r.merchant_order_id == merchant_order_id and r.provider_txn_id == provider_txn_id]
        if left_amounts and right_amounts and left_amounts[0] != right_amounts[0]:
            discrepancies.append(
                Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Left amount {left_amounts[0]} != Right amount {right_amounts[0]}",
                )
            )

    # duplicate_left: key appears more than once in left
    for key, count in left_counter.items():
        if count > 1:
            merchant_order_id, provider_txn_id = key
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Appears {count} times in left",
                )
            )

    return discrepancies
