from dataclasses import dataclass

@dataclass(frozen=True)
class Row:
    merchant_order_id: str
    provider_txn_id: str
    amount_cents: int
    status: str


@dataclass(frozen=True)
class Discrepancy:
    kind: str
    merchant_order_id: str
    provider_txn_id: str
    detail: str
