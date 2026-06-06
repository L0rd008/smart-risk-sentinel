"""Data access layer — query functions."""
from __future__ import annotations

from app.data.borrower_queries import (
    fetch_borrower,
    fetch_all_borrowers,
    log_risk_score,
)

__all__ = [
    "fetch_borrower",
    "fetch_all_borrowers",
    "log_risk_score",
]
