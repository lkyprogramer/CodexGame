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
                    detail=f"Found {len(left_rows_k)} rows on left",
                )
            )

        # Check for duplicates on right
        if len(right_rows_k) > 1:
            discrepancies.append(
                Discrepancy(
                    kind="duplicate_right",
                    merchant_order_id=k[0],
                    provider_txn_id=k[1],
                    detail=f"Found {len(right_rows_k)} rows on right",
                )
            )

        # Missing on left (exists on right but not on left)
        if not left_rows_k and right_rows_k:
            r = right_rows_k[0]
            discrepancies.append(
                Discrepancy(
                    kind="missing_left",
                    merchant_order_id=r.merchant_order_id,
                    provider_txn_id=r.provider_txn_id,
                    detail="Row exists on right but not on left",
                )
            )

        # Missing on right (exists on left but not on right)
        if left_rows_k and not right_rows_k:
            l = left_rows_k[0]
            discrepancies.append(
                Discrepancy(
                    kind="missing_right",
                    merchant_order_id=l.merchant_order_id,
                    provider_txn_id=l.provider_txn_id,
                    detail="Row exists on left but not on right",
                )
            )

        # Amount mismatch (both exist)
        if left_rows_k and right_rows_k:
            # Compare first row of each; if multiple, we already reported duplicates
            l = left_rows_k[0]
            r = right_rows_k[0]
            if l.amount_cents != r.amount_cents:
                discrepancies.append(
                    Discrepancy(
                        kind="amount_mismatch",
                        merchant_order_id=l.merchant_order_id,
                        provider_txn_id=l.provider_txn_id,
                        detail=f"Left: {l.amount_cents}, Right: {r.amount_cents}",
                    )
                )

    return discrepancies
