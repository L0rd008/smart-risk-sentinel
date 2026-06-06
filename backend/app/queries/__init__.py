"""Query layer — database query functions."""
from __future__ import annotations

from app.queries.borrower_queries import (
    fetch_borrower,
    fetch_all_borrowers,
    log_risk_score,
)

__all__ = [
    "fetch_borrower",
    "fetch_all_borrowers",
    "log_risk_score",
]
