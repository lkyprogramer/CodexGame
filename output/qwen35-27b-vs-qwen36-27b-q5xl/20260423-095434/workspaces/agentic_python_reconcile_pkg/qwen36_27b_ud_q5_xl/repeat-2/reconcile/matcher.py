from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    # Build key -> list of rows for both sides
    left_map: dict[str, list[Row]] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        left_map.setdefault(key, []).append(row)

    right_map: dict[str, list[Row]] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        right_map.setdefault(key, []).append(row)

    discrepancies: list[Discrepancy] = []

    all_keys = set(left_map.keys()) | set(right_map.keys())

    for key in all_keys:
        left_entries = left_map.get(key, [])
        right_entries = right_map.get(key, [])

        # Check for duplicates on left
        if len(left_entries) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"Found {len(left_entries)} entries on left",
                )
            )

        # Check for duplicates on right
        if len(right_entries) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_right",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"Found {len(right_entries)} entries on right",
                )
            )

        # Missing from one side
        if not left_entries:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail="Present on right but not on left",
                )
            )
        elif not right_entries:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail="Present on left but not on right",
                )
            )
        else:
            # Both sides have entries; check for amount mismatches
            # Compare first entries (or all if needed)
            for lr, rr in zip(left_entries, right_entries):
                if lr.amount_cents != rr.amount_cents:
                    discrepancies.append(
                        Discrepancy(
                            kind="amount_mismatch",
                            merchant_order_id=key[0],
                            provider_txn_id=key[1],
                            detail=f"Left: {lr.amount_cents}, Right: {rr.amount_cents}",
                        )
                    )

    return discrepancies
