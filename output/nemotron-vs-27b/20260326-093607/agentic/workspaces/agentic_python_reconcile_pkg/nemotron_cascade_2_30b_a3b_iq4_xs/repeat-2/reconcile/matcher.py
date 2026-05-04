from __future__ import annotations

from collections import Counter
from typing import Iterable, Tuple

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    # Build lookup tables for fast access
    left_by_key = { (r.merchant_order_id, r.provider_txn_id): r for r in left_rows }
    right_by_key = { (r.merchant_order_id, r.provider_txn_id): r for r in right_rows }

    discrepancies: list[Discrepancy] = []
    seen_left: set[tuple[str, str]] = set()
    seen_right: set[tuple[str, str]] = set()

    # Process left rows
    for key, left_row in left_by_key.items():
        if key in seen_left:
            continue  # duplicate in left (should not happen with dict)
        seen_left.add(key)
        if key not in right_by_key:
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=left_row.merchant_order_id,
                    provider_txn_id=left_row.provider_txn_id,
                    detail="",
                )
            )
        else:
            right_row = right_by_key[key]
            if left_row.amount_cents != right_row.amount_cents:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=left_row.merchant_order_id,
                        provider_txn_id=left_row.provider_txn_id,
                        detail="",
                    )
                )

    # Process right rows for missing left
    for key, right_row in right_by_key.items():
        if key in seen_right:
            continue
        seen_right.add(key)
        if key not in left_by_key:
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=right_row.merchant_order_id,
                    provider_txn_id=right_row.provider_txn_id,
                    detail="",
                )
            )
        elif key in seen_left:
            # duplicate in right (key already seen in left processing)
            # we count it as duplicate_left only once
            pass

    # Detect duplicate left rows (more than one row with same merchant_order_id+provider_txn_id)
    # Since we used a dict, duplicates are collapsed; we need to count original occurrences.
    # Re‑scan left rows to find actual duplicates.
    from collections import defaultdict
    left_counts: dict[tuple[str, str], int] = defaultdict(int)
    for r in left_rows:
        left_counts[(r.merchant_order_id, r.provider_txn_id)] += 1
    for (merchant_order_id, provider_txn_id), cnt in left_counts.items():
        if cnt > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_left",
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    detail="",
                )
            )

    return discrepancies
