from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    discrepancies: list[Discrepancy] = []

    # Build key -> list of rows for left and right
    # Key is (merchant_order_id, provider_txn_id)
    left_by_key: dict[tuple[str, str], list[Row]] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        if key not in left_by_key:
            left_by_key[key] = []
        left_by_key[key].append(row)

    right_by_key: dict[tuple[str, str], list[Row]] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        if key not in right_by_key:
            right_by_key[key] = []
        right_by_key[key].append(row)

    left_keys = set(left_by_key.keys())
    right_keys = set(right_by_key.keys())

    # missing_right: in left but not in right
    for key in left_keys - right_keys:
        row = left_by_key[key][0]
        discrepancies.append(
            Discrepancy(
                kind="missing_right",
                merchant_order_id=row.merchant_order_id,
                provider_txn_id=row.provider_txn_id,
                detail=f"Found in left but not in right",
            )
        )

    # missing_left: in right but not in left
    for key in right_keys - left_keys:
        row = right_by_key[key][0]
        discrepancies.append(
            Discrepancy(
                kind="missing_left",
                merchant_order_id=row.merchant_order_id,
                provider_txn_id=row.provider_txn_id,
                detail=f"Found in right but not in left",
            )
        )

    # Check for duplicates and amount mismatches in common keys
    for key in left_keys & right_keys:
        left_rows_for_key = left_by_key[key]
        right_rows_for_key = right_by_key[key]

        # duplicate_left: more than one row in left for this key
        if len(left_rows_for_key) > 1:
            row = left_rows_for_key[0]
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=row.merchant_order_id,
                    provider_txn_id=row.provider_txn_id,
                    detail=f"Duplicate found in left: {len(left_rows_for_key)} occurrences",
                )
            )

        # amount_mismatch: compare amounts (use first occurrence for comparison)
        left_amount = left_rows_for_key[0].amount_cents
        right_amount = right_rows_for_key[0].amount_cents
        if left_amount != right_amount:
            row = left_rows_for_key[0]
            discrepancies.append(
                Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=row.merchant_order_id,
                    provider_txn_id=row.provider_txn_id,
                    detail=f"Left amount {left_amount} != Right amount {right_amount}",
                )
            )

    return discrepancies
