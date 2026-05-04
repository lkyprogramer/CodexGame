from __future__ import annotations

from collections import Counter
from typing import Iterable

from .models import Discrepancy, Row


def find_discrepancies(left_rows: Iterable[Row], right_rows: Iterable[Row]) -> list[Discrepancy]:
    # TODO: implement real matching logic.
    return []
