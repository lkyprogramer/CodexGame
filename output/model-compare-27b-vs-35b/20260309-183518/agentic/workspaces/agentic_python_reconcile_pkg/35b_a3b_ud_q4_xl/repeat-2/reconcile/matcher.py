from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    discrepancies: list[Discrepancy] = []

    left_list = list(left_rows)
    right_list = list(right_rows)

    # Count occurrences of each key
    left_counts: Counter[tuple[str, str]] = Counter(
        (r.merchant_order_id, r.provider_txn_id) for r in left_list
    )
    right_counts: Counter[tuple[str, str]] = Counter(
        (r.merchant_order_id, r.provider_txn_id) for r in right_list
    )

    all_keys = set(left_counts.keys()) | set(right_counts.keys())

    for key in all_keys:
        merchant_order_id, provider_txn_id = key
        left_count = left_counts[key]
        right_count = right_counts[key]

        # Find rows with this key
        left_rows_for_key = [r for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key]
        right_rows_for_key = [r for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key]

        if left_count > right_count:
            # Duplicates on left
            for _ in range(left_count - right_count):
                discrepancies.append(
                    Discrepancy(
                        kind="duplicate_left",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Found {left_count} on left, {right_count} on right",
                    )
                )
        elif right_count > left_count:
            # Missing on left
            for _ in range(right_count - left_count):
                discrepancies.append(
                    Discrepancy(
                        kind="missing_left",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Found {right_count} on right, {left_count} on left",
                    )
                )

        if left_count > 0 and right_count > 0:
            # Check for amount mismatch
            left_amounts = {r.amount_cents for r in left_rows_for_key}
            right_amounts = {r.amount_cents for r in right_rows_for_key}
            if left_amounts != right_amounts:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Left amounts: {sorted(left_amounts)}, Right amounts: {sorted(right_amounts)}",
                    )
                )

        if left_count == 0 and right_count > 0:
            # Missing on left (already handled above, but ensure missing_right is captured)
            pass
        elif right_count == 0 and left_count > 0:
            # Missing on right
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail=f"Found {left_count} on left, 0 on right",
                )
            )

    return discrepancies
