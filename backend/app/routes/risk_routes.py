"""Risk API blueprint — owned by Member 3.

Implements the 5 endpoints defined in docs/API_CONTRACT.md:
    GET  /api/health
    GET  /api/borrowers
    GET  /api/borrowers/<customer_id>
    GET  /api/risk/<customer_id>
    GET  /api/portfolio/snapshot
    POST /api/stress-test

The routes are thin: they read from the DB, hand the borrower dict to
`Scorecard.calculate`, and return the result. No business logic here.
"""
from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request

from app.db_connect import get_connection, dict_cursor
from app.scoring import Scorecard


risk_bp = Blueprint("risk", __name__)
_scorecard = Scorecard()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(code: str, message: str, http_status: int):
    """Uniform error response per the API contract."""
    return jsonify({"error": code, "message": message}), http_status


def _fetch_borrower(customer_id: str) -> dict[str, Any] | None:
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
            la.vehicle_type,
            la.vehicle_value,
            la.loan_amount,
            la.ltv_ratio,
            la.dpd_current,
            la.dpd_pattern,
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


def _fetch_all_borrowers() -> list[dict[str, Any]]:
    """Batch-fetch ALL borrowers with lease + sector data in a single query.

    Eliminates the N+1 pattern: instead of 1 + N individual queries,
    this runs one JOIN and returns all rows at once. Each row has the
    same shape as _fetch_borrower so Scorecard.calculate works directly.
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
            b.created_at,
            la.vehicle_type,
            la.vehicle_value,
            la.loan_amount,
            la.ltv_ratio,
            la.dpd_current,
            la.dpd_pattern,
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


def _log_risk_score(
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@risk_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0"})


@risk_bp.route("/borrowers", methods=["GET"])
def list_borrowers():
    """List all borrowers (summary only).

    Uses a single batch query (_fetch_all_borrowers) to avoid the N+1
    pattern. Scores are computed in-memory which is fast for ~1k records.
    """
    all_rows = _fetch_all_borrowers()

    borrowers = []
    for row in all_rows:
        risk = _scorecard.calculate(row)
        borrowers.append({
            "customer_id":  row["customer_id"],
            "name":         row["name"],
            "risk_grade":   risk["risk_grade"],
            "risk_score":   risk["risk_score"],
            "sector":       row.get("sector"),
            "last_updated": row["created_at"].isoformat() if row.get("created_at") else None,
        })

    return jsonify({"borrowers": borrowers, "total": len(borrowers)})


@risk_bp.route("/borrowers/<customer_id>", methods=["GET"])
def get_borrower(customer_id: str):
    """Single borrower profile (raw data, no scoring)."""
    borrower = _fetch_borrower(customer_id)
    if borrower is None:
        return _error("not_found", f"borrower {customer_id} not found", 404)

    return jsonify({
        "customer_id":         borrower["customer_id"],
        "name":                borrower["name"],
        "age":                 borrower["age"],
        "sector_code":         borrower["sector_code"],
        "annual_income":       float(borrower["annual_income"] or 0),
        "crib_grade":          borrower["crib_grade"],
        "vehicle_type":        borrower["vehicle_type"],
        "loan_amount":         float(borrower["loan_amount"] or 0),
        "vehicle_value":       float(borrower["vehicle_value"] or 0),
        "ltv_ratio":           float(borrower["ltv_ratio"] or 0),
        "dpd_current":         int(borrower["dpd_current"] or 0),
        "dpd_pattern":         borrower["dpd_pattern"] or [],
        "app_login_freq":      int(borrower["app_login_freq"] or 0),
        "monthly_income":      float(borrower["monthly_income"] or 0),
        "monthly_obligations": float(borrower["monthly_obligations"] or 0),
    })


@risk_bp.route("/risk/<customer_id>", methods=["GET"])
def get_risk(customer_id: str):
    """Full risk assessment for one borrower — runs the scoring engine.

    Also writes to risk_scores_log for audit trail purposes.
    """
    borrower = _fetch_borrower(customer_id)
    if borrower is None:
        return _error("not_found", f"borrower {customer_id} not found", 404)

    risk = _scorecard.calculate(borrower)

    # Audit log — best-effort, never blocks the response.
    _log_risk_score(
        customer_id=customer_id,
        score=risk["risk_score"],
        grade=risk["risk_grade"],
        breach=risk["compliance_breach"],
    )

    return jsonify(risk)


@risk_bp.route("/portfolio/snapshot", methods=["GET"])
def portfolio_snapshot():
    """Aggregate view powering the dashboard doughnut + sector table.

    Uses a single batch query (_fetch_all_borrowers) to avoid the N+1
    pattern. With ~1k rows, this is fast enough for the demo.
    """
    all_rows = _fetch_all_borrowers()

    by_grade = {"Low": 0, "Medium": 0, "High": 0}
    by_sector: dict[str, dict[str, Any]] = {}
    breaches = 0
    total_score = 0
    counted = 0

    for row in all_rows:
        risk = _scorecard.calculate(row)
        by_grade[risk["risk_grade"]] += 1
        if risk["compliance_breach"]:
            breaches += 1
        sector = row.get("sector") or "Unknown"
        entry = by_sector.setdefault(sector, {"sector": sector, "count": 0, "_sum_score": 0})
        entry["count"] += 1
        entry["_sum_score"] += risk["risk_score"]
        total_score += risk["risk_score"]
        counted += 1

    sectors_out = [
        {
            "sector":    e["sector"],
            "count":     e["count"],
            "avg_score": int(round(e["_sum_score"] / e["count"])) if e["count"] else 0,
        }
        for e in by_sector.values()
    ]

    return jsonify({
        "total_borrowers":     counted,
        "by_grade":            by_grade,
        "by_sector":           sectors_out,
        "compliance_breaches": breaches,
        "avg_portfolio_score": int(round(total_score / counted)) if counted else 0,
    })


@risk_bp.route("/stress-test", methods=["POST"])
def stress_test():
    """Inject overrides on top of a borrower's DB record and re-score.

    Nothing is persisted. The request body is validated minimally — bad
    keys in `overrides` are simply ignored.
    """
    body = request.get_json(silent=True) or {}
    cid = body.get("customer_id")
    if not cid:
        return _error("bad_request", "customer_id is required", 400)

    borrower = _fetch_borrower(cid)
    if borrower is None:
        return _error("not_found", f"borrower {cid} not found", 404)

    overrides = body.get("overrides") or {}
    allowed_keys = {"ltv_ratio", "dpd_current", "crib_grade", "app_login_freq"}
    for k, v in overrides.items():
        if k in allowed_keys:
            borrower[k] = v

    return jsonify(_scorecard.calculate(borrower))
