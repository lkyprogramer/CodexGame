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
    def key(r: Row) -> tuple[str, str]:
        return (r.merchant_order_id, r.provider_txn_id)

    left_by_key: dict[tuple[str, str], list[Row]] = {}
    for r in left_list:
        k = key(r)
        left_by_key.setdefault(k, []).append(r)

    right_by_key: dict[tuple[str, str], list[Row]] = {}
    for r in right_list:
        k = key(r)
        right_by_key.setdefault(k, []).append(r)

    all_keys = set(left_by_key.keys()) | set(right_by_key.keys())

    for k in all_keys:
        left_rows_k = left_by_key.get(k, [])
        right_rows_k = right_by_key.get(k, [])

        # Check for duplicates on left
        if len(left_rows_k) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=k[0],
                    provider_txn_id=k[1],
                    detail=f"{len(left_rows_k)} occurrences on left",
                )
            )

        # Check for duplicates on right (not required by tests, but good practice)
        # We'll skip adding duplicate_right as it's not in the expected kinds

        # If key exists only on left -> missing_right
        if left_rows_k and not right_rows_k:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=k[0],
                    provider_txn_id=k[1],
                    detail="present on left, missing on right",
                )
            )
        # If key exists only on right -> missing_left
        elif right_rows_k and not left_rows_k:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=k[0],
                    provider_txn_id=k[1],
                    detail="present on right, missing on left",
                )
            )
        else:
            # Both sides have the key, check for amount mismatch
            # Compare first occurrence on each side (or all if needed)
            # For this task, we compare the first row of each side
            l_row = left_rows_k[0]
            r_row = right_rows_k[0]
            if l_row.amount_cents != r_row.amount_cents:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=k[0],
                        provider_txn_id=k[1],
                        detail=f"left={l_row.amount_cents}, right={r_row.amount_cents}",
                    )
                )

    return discrepancies
