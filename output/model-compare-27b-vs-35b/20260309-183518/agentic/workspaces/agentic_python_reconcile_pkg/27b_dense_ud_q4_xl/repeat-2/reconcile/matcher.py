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

        # Detect duplicates on left
        if len(left_rows_for_key) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Found {len(left_rows_for_key)} rows on left",
                )
            )

        # Detect duplicates on right (optional, not required by tests but consistent)
        if len(right_rows_for_key) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_right",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Found {len(right_rows_for_key)} rows on right",
                )
            )

        # Missing on left (exists on right but not on left)
        if not left_rows_for_key and right_rows_for_key:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail="Present on right but missing on left",
                )
            )

        # Missing on right (exists on left but not on right)
        if left_rows_for_key and not right_rows_for_key:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail="Present on left but missing on right",
                )
            )

        # Amount mismatch (when both exist)
        if left_rows_for_key and right_rows_for_key:
            # Compare first row of each side for amount
            left_amount = left_rows_for_key[0].amount_cents
            right_amount = right_rows_for_key[0].amount_cents
            if left_amount != right_amount:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Left: {left_amount}, Right: {right_amount}",
                    )
                )

    return discrepancies
