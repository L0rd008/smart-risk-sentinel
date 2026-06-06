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

from app.data import fetch_borrower, fetch_all_borrowers, log_risk_score
from app.scoring import Scorecard


risk_bp = Blueprint("risk", __name__)
_scorecard = Scorecard()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(code: str, message: str, http_status: int):
    """Uniform error response per the API contract."""
    return jsonify({"error": code, "message": message}), http_status


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@risk_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "1.0"})


@risk_bp.route("/borrowers", methods=["GET"])
def list_borrowers():
    """List all borrowers (summary only).

    Uses a single batch query (fetch_all_borrowers) to avoid the N+1
    pattern. Scores are computed in-memory which is fast for ~1k records.
    """
    all_rows = fetch_all_borrowers()

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
    borrower = fetch_borrower(customer_id)
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

    # New fields required by frontend
    "net_worth":           float(borrower["net_worth"] or 0),
    "province":            borrower.get("province", "Unknown"),
    "tenure_months":       int(borrower.get("tenure_months") or 48),
    "sector_npl":          float(borrower.get("sector_npl") or 0),
})


@risk_bp.route("/risk/<customer_id>", methods=["GET"])
def get_risk(customer_id: str):
    """Full risk assessment for one borrower — runs the scoring engine.

    Also writes to risk_scores_log for audit trail purposes.
    """
    borrower = fetch_borrower(customer_id)
    if borrower is None:
        return _error("not_found", f"borrower {customer_id} not found", 404)

    risk = _scorecard.calculate(borrower)

    # Audit log — best-effort, never blocks the response.
    log_risk_score(
        customer_id=customer_id,
        score=risk["risk_score"],
        grade=risk["risk_grade"],
        breach=risk["compliance_breach"],
    )

    return jsonify(risk)


@risk_bp.route("/portfolio/snapshot", methods=["GET"])
def portfolio_snapshot():
    """Aggregate view powering the dashboard doughnut + sector table.

    Uses a single batch query (fetch_all_borrowers) to avoid the N+1
    pattern. With ~1k rows, this is fast enough for the demo.
    """
    all_rows = fetch_all_borrowers()

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

    borrower = fetch_borrower(cid)
    if borrower is None:
        return _error("not_found", f"borrower {cid} not found", 404)

    overrides = body.get("overrides") or {}
    allowed_keys = {"ltv_ratio", "dpd_current", "crib_grade", "app_login_freq"}
    for k, v in overrides.items():
        if k in allowed_keys:
            borrower[k] = v

    return jsonify(_scorecard.calculate(borrower))


@risk_bp.route("/calculate-risk", methods=["POST"])
def calculate_risk():
    """Calculate a risk score directly from request JSON."""

    body = request.get_json(silent=True) or {}

    # ------------------------------------------------------------------
    # Required fields
    # ------------------------------------------------------------------
    required_fields = [
        "customer_id",
        "monthly_income",
        "monthly_obligations",
        "crib_grade",
        "dpd_current",
        "vehicle_type",
        "ltv_ratio",
        "sector_npl",
        "net_worth",
        "app_login_freq",
    ]

    missing = [f for f in required_fields if f not in body]

    if missing:
        return _error(
            "bad_request",
            f"missing required fields: {', '.join(missing)}",
            400,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    # vehicle type
    if body["vehicle_type"] not in {"Private", "Commercial"}:
        return _error(
            "bad_request",
            "vehicle_type must be Private or Commercial",
            400,
        )

    # CRIB grade
    valid_crib = {"A", "B", "C", "D", "E", "XX"}
    if body["crib_grade"] not in valid_crib:
        return _error(
            "bad_request",
            "invalid crib_grade",
            400,
        )

    try:
        monthly_income = float(body["monthly_income"])
        monthly_obligations = float(body["monthly_obligations"])
        ltv_ratio = float(body["ltv_ratio"])
        sector_npl = float(body["sector_npl"])
        net_worth = float(body["net_worth"])

        dpd_current = int(body["dpd_current"])
        app_login_freq = int(body["app_login_freq"])

    except (TypeError, ValueError):
        return _error(
            "bad_request",
            "invalid numeric field types",
            400,
        )

    # numeric validations
    if monthly_income <= 0:
        return _error(
            "bad_request",
            "monthly_income must be > 0",
            400,
        )

    if monthly_obligations < 0:
        return _error(
            "bad_request",
            "monthly_obligations must be >= 0",
            400,
        )

    if ltv_ratio <= 0 or ltv_ratio > 2:
        return _error(
            "bad_request",
            "ltv_ratio must be between 0 and 2",
            400,
        )

    if dpd_current < 0:
        return _error(
            "bad_request",
            "dpd_current must be >= 0",
            400,
        )

    if sector_npl < 0:
        return _error(
            "bad_request",
            "sector_npl must be >= 0",
            400,
        )

    if net_worth < 0:
        return _error(
            "bad_request",
            "net_worth must be >= 0",
            400,
        )

    if app_login_freq < 0:
        return _error(
            "bad_request",
            "app_login_freq must be >= 0",
            400,
        )

    # ------------------------------------------------------------------
    # Build borrower object
    # ------------------------------------------------------------------
    borrower = {
        "customer_id": body["customer_id"],
        "monthly_income": monthly_income,
        "monthly_obligations": monthly_obligations,
        "crib_grade": body["crib_grade"],
        "dpd_current": dpd_current,
        "vehicle_type": body["vehicle_type"],
        "ltv_ratio": ltv_ratio,
        "sector_npl": sector_npl,
        "net_worth": net_worth,
        "app_login_freq": app_login_freq,
    }

    # ------------------------------------------------------------------
    # Calculate risk
    # ------------------------------------------------------------------
    risk = _scorecard.calculate(borrower)

    return jsonify(risk)

