from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    left_by_order = {r.merchant_order_id: r for r in left_rows}
    right_by_order = {r.merchant_order_id: r for r in right_rows}
    
    discrepancies = []
    
    # Check for missing_left and amount_mismatch
    for oid, left_row in left_by_order.items():
        if oid not in right_by_order:
            discrepancies.append(Discrepancy(
                kind="missing_left",
                merchant_order_id=oid,
                provider_txn_id=left_row.provider_txn_id,
                detail=f"Missing in right: {left_row.provider_txn_id}"
            ))
        else:
            right_row = right_by_order[oid]
            if left_row.amount_cents != right_row.amount_cents:
                discrepancies.append(Discrepancy(
                    kind="amount_mismatch",
                    merchant_order_id=oid,
                    provider_txn_id=left_row.provider_txn_id,
                    detail=f"Amount mismatch: {left_row.amount_cents} vs {right_row.amount_cents}"
                ))
    
    # Check for missing_right
    for oid, right_row in right_by_order.items():
        if oid not in left_by_order:
            discrepancies.append(Discrepancy(
                kind="missing_right",
                merchant_order_id=oid,
                provider_txn_id=right_row.provider_txn_id,
                detail=f"Missing in left: {right_row.provider_txn_id}"
            ))
    
    # Check for duplicate_left (same merchant_order_id and provider_txn_id appearing more than once in left)
    left_counts = Counter(r.merchant_order_id for r in left_rows)
    for oid, count in left_counts.items():
        if count > 1:
            discrepancies.append(Discrepancy(
                kind="duplicate_left",
                merchant_order_id=oid,
                provider_txn_id="",
                detail=f"Duplicate merchant_order_id: {oid}"
            ))
    
    return discrepancies


def render_summary(discrepancies: list[Discrepancy]) -> str:
    counts = Counter(d.kind for d in discrepancies)
    parts = []
    for kind, count in sorted(counts.items()):
        parts.append(f"{kind}={count}")
    if parts:
        return "; ".join(parts)
    return "no discrepancies"