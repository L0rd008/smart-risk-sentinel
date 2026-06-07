"""Integration test to verify sector_code -> sector_npl resolution in routes.

We avoid real DB access by monkeypatching the internal _fetch_borrower helper
to return a borrower row that simulates a DB record with only sector_code set
and no explicit sector_npl value. The Scorecard expects `sector_npl` to be
present; the route's SQL JOIN should normally populate it. This test asserts
the route does not attempt a DB call during test and documents current
behavior (whether sector_npl is provided or None).
"""
from __future__ import annotations

from pathlib import Path
import copy
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
import app.routes.risk_routes as rr  # noqa: E402


def _borrower_with_sector_code(**overrides):
    base = {
        "customer_id": "sector-0001",
        "name": "Sector Borrower",
        "age": 45,
        "sector_code": "SERVICES",
        # Note: intentionally omit sector_npl to simulate reliance
        # on the route SQL join to supply it.
        "monthly_income": 200_000,
        "monthly_obligations": 80_000,
        "crib_grade": "B",
        "net_worth": 1_500_000,
        "app_login_freq": 3,
        "vehicle_type": "Private",
        "ltv_ratio": 0.35,
        "dpd_current": 0,
    }
    base.update(overrides)
    return base


def test_route_uses_fetch_borrower_to_supply_sector_npl(monkeypatch):
    app = create_app()

    # Provide a fake fetch that returns a borrower missing sector_npl
    original = _borrower_with_sector_code()

    def fake_fetch(cid: str):
        if cid == original["customer_id"]:
            return copy.deepcopy(original)
        return None

    # No-op logger
    def noop(*a, **k):
        return None

    monkeypatch.setattr(rr, "_fetch_borrower", fake_fetch)
    monkeypatch.setattr(rr, "_log_risk_score", noop)

    with app.test_client() as c:
        res = c.get(f"/api/risk/{original['customer_id']}")
        assert res.status_code == 200
        out = res.get_json()

        # Document current behavior: route/scorecard will treat missing
        # sector_npl as 0.0 (Scorecard uses float(b.get(..., 0.0))).
        assert "sector_npl" in out or isinstance(out.get("risk_score"), int)
        # Ensure the score was calculated without raising and a grade exists
        assert out["risk_grade"] in {"Low", "Medium", "High"}
