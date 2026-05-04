from __future__ import annotations

import csv
from pathlib import Path

from .matcher import find_discrepancies
from .models import Row
from .report import render_summary


def load_rows(path: Path) -> list[Row]:
    rows: list[Row] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            if not raw:
                continue
            merchant_order_id = (raw.get("merchant_order_id") or "").strip()
            provider_txn_id = (raw.get("provider_txn_id") or "").strip()
            if not merchant_order_id and not provider_txn_id:
                continue
            rows.append(
                Row(
                    merchant_order_id=merchant_order_id,
                    provider_txn_id=provider_txn_id,
                    amount_cents=int(raw["amount_cents"]),
                    status=(raw.get("status") or "").strip(),
                )
            )
    return rows


def run(left_path: Path, right_path: Path) -> str:
    discrepancies = find_discrepancies(load_rows(left_path), load_rows(right_path))
    return render_summary(discrepancies)
