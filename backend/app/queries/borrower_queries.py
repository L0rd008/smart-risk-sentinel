"""Borrower queries — all DB queries for borrower-related operations.

Owned by Member 3 (Flask API Layer). Isolates SQL from route handlers.
"""
from __future__ import annotations

from typing import Any

from app.db_connect import get_connection, dict_cursor


def fetch_borrower(customer_id: str) -> dict[str, Any] | None:
    """Read a single borrower joined with their latest lease + sector NPL.

    The shape returned matches the borrower contract in API_CONTRACT.md
    so Scorecard.calculate works directly.
    """
    sql = """
        SELECT
            b.customer_id::text AS customer_id,
            b.name,
            b.age,
            b.sector_code,
            b.annual_income,
            b.monthly_income,
            b.monthly_obligations,
            b.crib_grade,
            b.net_worth,
            b.app_login_freq,
            b.province,
            la.vehicle_type,
            la.vehicle_value,
            la.loan_amount,
            la.ltv_ratio,
            la.dpd_current,
            la.dpd_pattern,
            la.tenure_months,
            s.npl_ratio AS sector_npl,
            s.sector_name AS sector
        FROM borrowers b
        LEFT JOIN lease_agreements la ON la.customer_id = b.customer_id
        LEFT JOIN sector_reference s   ON s.sector_code = b.sector_code
        WHERE b.customer_id = %s
        LIMIT 1
    """
    with get_connection() as conn, dict_cursor(conn) as cur:
        cur.execute(sql, (customer_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def fetch_all_borrowers() -> list[dict[str, Any]]:
    """Batch-fetch ALL borrowers with lease + sector data in a single query.

    Eliminates the N+1 pattern: instead of 1 + N individual queries,
    this runs one JOIN and returns all rows at once. Each row has the
    same shape as fetch_borrower so Scorecard.calculate works directly.
    """
    sql = """
        SELECT
            b.customer_id::text AS customer_id,
            b.name,
            b.age,
            b.sector_code,
            b.annual_income,
            b.monthly_income,
            b.monthly_obligations,
            b.crib_grade,
            b.net_worth,
            b.app_login_freq,
            b.province,
            b.created_at,
            la.vehicle_type,
            la.vehicle_value,
            la.loan_amount,
            la.ltv_ratio,
            la.dpd_current,
            la.dpd_pattern,
            la.tenure_months,
            s.npl_ratio AS sector_npl,
            s.sector_name AS sector
        FROM borrowers b
        LEFT JOIN lease_agreements la ON la.customer_id = b.customer_id
        LEFT JOIN sector_reference s   ON s.sector_code = b.sector_code
        ORDER BY b.name
    """
    with get_connection() as conn, dict_cursor(conn) as cur:
        cur.execute(sql)
        return [dict(r) for r in cur.fetchall()]


def log_risk_score(
    customer_id: str,
    score: int,
    grade: str,
    breach: bool,
) -> None:
    """Write an entry to risk_scores_log for audit trail purposes.

    Called on individual risk assessments (GET /risk/:id). Batch
    endpoints (list, snapshot) do NOT log to avoid flooding the table.
    Failures are silently ignored — logging must never break scoring.
    """
    sql = """
        INSERT INTO risk_scores_log
            (customer_id, score, grade, compliance_breach)
        VALUES (%s, %s, %s, %s)
    """
    try:
        with get_connection() as conn, dict_cursor(conn) as cur:
            cur.execute(sql, (customer_id, score, grade, breach))
    except Exception:
        # Audit logging is best-effort; never let it break a request.
        pass
