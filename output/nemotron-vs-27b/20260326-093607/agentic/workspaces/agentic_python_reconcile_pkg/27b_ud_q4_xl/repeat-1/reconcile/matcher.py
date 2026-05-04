from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    discrepancies: list[Discrepancy] = []

    # Build key -> list of rows for left and right
    left_by_key: dict[tuple[str, str], list[Row]] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        left_by_key.setdefault(key, []).append(row)

    right_by_key: dict[tuple[str, str], list[Row]] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        right_by_key.setdefault(key, []).append(row)

    all_keys = set(left_by_key.keys()) | set(right_by_key.keys())

    for key in all_keys:
        left_rows_for_key = left_by_key.get(key, [])
        right_rows_for_key = right_by_key.get(key, [])

        merchant_order_id, provider_txn_id = key

        # Check for duplicates on left
        if len(left_rows_for_key) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Found {len(left_rows_for_key)} rows on left",
                )
            )

        # Check for duplicates on right
        if len(right_rows_for_key) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_right",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Found {len(right_rows_for_key)} rows on right",
                )
            )

        # Missing on left or right
        if not left_rows_for_key:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail="Row exists on right but not on left",
                )
            )
        elif not right_rows_for_key:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail="Row exists on left but not on right",
                )
            )
        else:
            # Both exist, check for amount mismatch
            # Compare first row of each (if duplicates exist, we already reported them)
            left_row = left_rows_for_key[0]
            right_row = right_rows_for_key[0]
            if left_row.amount_cents != right_row.amount_cents:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Left: {left_row.amount_cents}, Right: {right_row.amount_cents}",
                    )
                )

    return discrepancies
