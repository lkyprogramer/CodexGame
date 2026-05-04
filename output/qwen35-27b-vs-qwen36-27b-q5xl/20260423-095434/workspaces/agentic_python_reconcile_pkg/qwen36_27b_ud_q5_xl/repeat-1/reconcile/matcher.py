from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    # Build lookup by (merchant_order_id, provider_txn_id)
    left_map: dict[tuple[str, str], list[Row]] = {}
    for row in left_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        left_map.setdefault(key, []).append(row)

    right_map: dict[tuple[str, str], list[Row]] = {}
    for row in right_list:
        key = (row.merchant_order_id, row.provider_txn_id)
        right_map.setdefault(key, []).append(row)

    discrepancies: list[Discrepancy] = []

    all_keys = set(left_map.keys()) | set(right_map.keys())

    for key in all_keys:
        left_entries = left_map.get(key, [])
        right_entries = right_map.get(key, [])

        # Detect duplicates on left
        if len(left_entries) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"{len(left_entries)} occurrences on left",
                )
            )

        # Detect duplicates on right
        if len(right_entries) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_right",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail=f"{len(right_entries)} occurrences on right",
                )
            )

        # Missing on right (present in left but not in right)
        if left_entries and not right_entries:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail="present in left but not in right",
                )
            )

        # Missing on left (present in right but not in left)
        if right_entries and not left_entries:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=key[0],
                    provider_txn_id=key[1],
                    detail="present in right but not in left",
                )
            )

        # Amount mismatch (both present, compare first entries)
        if left_entries and right_entries:
            left_amount = left_entries[0].amount_cents
            right_amount = right_entries[0].amount_cents
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
