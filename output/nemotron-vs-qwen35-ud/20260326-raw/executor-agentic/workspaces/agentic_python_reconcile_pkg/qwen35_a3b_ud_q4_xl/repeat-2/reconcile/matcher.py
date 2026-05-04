from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    # Count occurrences of each key in left and right
    left_counts: Counter[tuple[str, str]] = Counter(
        (row.merchant_order_id, row.provider_txn_id) for row in left_list
    )
    right_counts: Counter[tuple[str, str]] = Counter(
        (row.merchant_order_id, row.provider_txn_id) for row in right_list
    )

    # Track amounts for each key
    left_amounts: dict[tuple[str, str], int] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        if key not in left_amounts:
            left_amounts[key] = row.amount_cents

    right_amounts: dict[tuple[str, str], int] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        if key not in right_amounts:
            right_amounts[key] = row.amount_cents

    discrepancies: list[Discrepancy] = []

    all_keys = set(left_counts.keys()) | set(right_counts.keys())

    for key in all_keys:
        merchant_order_id, provider_txn_id = key
        left_count = left_counts[key]
        right_count = right_counts[key]

        # Duplicate on left
        if left_count > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Found {left_count} occurrences on left",
                )
            )

        # Missing on left (exists in right but not in left)
        if left_count == 0 and right_count > 0:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Present in right but not in left",
                )
            )

        # Missing on right (exists in left but not in right)
        if left_count > 0 and right_count == 0:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Present in left but not in right",
                )
            )

        # Amount mismatch (exists in both but amounts differ)
        if left_count > 0 and right_count > 0:
            left_amt = left_amounts[key]
            right_amt = right_amounts[key]
            if left_amt != right_amt:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Left: {left_amt}, Right: {right_amt}",
                    )
                )

    return discrepancies
