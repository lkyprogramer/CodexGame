from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    # Build lookup by (merchant_order_id, provider_txn_id)
    left_by_key: dict[tuple[str, str], list[Row]] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        left_by_key.setdefault(key, []).append(row)

    right_by_key: dict[tuple[str, str], list[Row]] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        right_by_key.setdefault(key, []).append(row)

    discrepancies: list[Discrepancy] = []

    # Detect duplicates on left
    for key, rows in left_by_key.items():
        if len(rows) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"{len(rows)} occurrences on left",
                )
            )

    # Detect duplicates on right
    for key, rows in right_by_key.items():
        if len(rows) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_right",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"{len(rows)} occurrences on right",
                )
            )

    # Compare matched keys
    all_keys = set(left_by_key.keys()) | set(right_by_key.keys())
    for key in all_keys:
        left_rows_for_key = left_by_key.get(key, [])
        right_rows_for_key = right_by_key.get(key, [])

        if not left_rows_for_key and right_rows_for_key:
            # Missing on left
            for row in right_rows_for_key:
                discrepancies.append(
                    Discrepancy(
                        kind="missing_left",
                        merchant_order_id=key[0],
                        provider_txn_id=key[1],
                        detail="present on right but not on left",
                    )
                )
        elif left_rows_for_key and not right_rows_for_key:
            # Missing on right
            for row in left_rows_for_key:
                discrepancies.append(
                    Discrepancy(
                        kind="missing_right",
                        merchant_order_id=key[0],
                        provider_txn_id=key[1],
                        detail="present on left but not on right",
                    )
                )
        else:
            # Both sides have entries; compare amounts
            # Use first occurrence for comparison
            left_amount = left_rows_for_key[0].amount_cents
            right_amount = right_rows_for_key[0].amount_cents
            if left_amount != right_amount:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=key[0],
                        provider_txn_id=key[1],
                        detail=f"left={left_amount}, right={right_amount}",
                    )
                )

    return discrepancies
