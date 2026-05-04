from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_list = list(left_rows)
    right_list = list(right_rows)

    # Count occurrences of each key (merchant_order_id, provider_txn_id)
    left_counts: Counter[tuple[str, str]] = Counter(
        (r.merchant_order_id, r.provider_txn_id) for r in left_list
    )
    right_counts: Counter[tuple[str, str]] = Counter(
        (r.merchant_order_id, r.provider_txn_id) for r in right_list
    )

    discrepancies: list[Discrepancy] = []

    all_keys = set(left_counts.keys()) | set(right_counts.keys())

    for key in all_keys:
        merchant_order_id, provider_txn_id = key
        left_count = left_counts[key]
        right_count = right_counts[key]

        # Find amount mismatch: if counts match but amounts differ
        if left_count == right_count and left_count > 0:
            # Check if any row with this key has different amount
            left_amounts = {r.amount_cents for r in left_list if (r.merchant_order_id, r.provider_txn_id) == key}
            right_amounts = {r.amount_cents for r in right_list if (r.merchant_order_id, r.provider_txn_id) == key}
            if left_amounts != right_amounts:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Left amounts: {sorted(left_amounts)}, Right amounts: {sorted(right_amounts)}",
                    )
                )
        else:
            # Handle duplicates and missing
            if left_count > right_count:
                # Duplicates on left
                for _ in range(left_count - right_count):
                    discrepancies.append(
                        Discrepancy(
                            kind="duplicate_left",
                            merchant_order_id=merchant_order_id,
                            provider_txn_id=provider_txn_id,
                            detail=f"Extra occurrence on left",
                        )
                    )
            if right_count > left_count:
                # Missing on left (extra on right)
                for _ in range(right_count - left_count):
                    discrepancies.append(
                        Discrepancy(
                            kind="missing_left",
                            merchant_order_id=merchant_order_id,
                            provider_txn_id=provider_txn_id,
                            detail=f"Missing on left",
                        )
                    )
            if left_count > 0 and right_count == 0:
                # Missing on right
                discrepancies.append(
                    Discrepancy(
                        kind="missing_right",
                        merchant_order_id=merchant_order_id,
                        provider_txn_id=provider_txn_id,
                        detail=f"Missing on right",
                    )
                )
            if left_count == 0 and right_count > 0:
                # Missing on left (already handled above, but for clarity)
                pass

    return discrepancies
