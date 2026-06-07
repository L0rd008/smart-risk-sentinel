"""Integration tests for the /api/stress-test endpoint.

These tests do not touch a real database. They monkeypatch the
`_fetch_borrower` helper in `app.routes.risk_routes` so requests use a
fresh in-memory borrower dict per request (simulating a persistent DB).

They also monkeypatch `_log_risk_score` to a no-op so audit logging
doesn't attempt DB writes.
"""
from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
import app.routes.risk_routes as rr  # noqa: E402


def _base_borrower(**overrides: Any) -> dict[str, Any]:
    base = {
        "customer_id":         "stress-test-0001",
        "name":                "Scenario Borrower",
        "age":                 40,
        "sector_code":         "SERVICES",
        "annual_income":       6_000_000,
        "monthly_income":      500_000,
        "monthly_obligations": 100_000,
        "crib_grade":          "A",
        "net_worth":           20_000_000,
        "app_login_freq":      20,
        "vehicle_type":        "Private",
        "vehicle_value":       10_000_000,
        "loan_amount":         3_500_000,
        "ltv_ratio":           0.35,
        "dpd_current":         0,
        "dpd_pattern":         [0, 0, 0, 0, 0, 0],
        "sector_npl":          0.03,
    }
    base.update(overrides)
    return base


@pytest.fixture
def client(monkeypatch):
    """Create Flask test client with DB helpers patched to use an in-memory borrower."""
    app = create_app()

    # Keep an original borrower and ensure each call returns a fresh copy
    original = _base_borrower()

    def fake_fetch_borrower(cid: str):
        # Return a deep copy so per-request mutations don't leak
        if cid == original["customer_id"]:
            return copy.deepcopy(original)
        return None

    # No-op logger to avoid DB writes during tests
    def noop_log(*args, **kwargs):
        return None

    monkeypatch.setattr(rr, "_fetch_borrower", fake_fetch_borrower)
    monkeypatch.setattr(rr, "_log_risk_score", noop_log)

    with app.test_client() as c:
        yield c


def test_stress_test_scenario_and_db_integrity(client):
    cid = "stress-test-0001"

    # 1) Get baseline risk (should be Low/Green for our base borrower)
    r = client.get(f"/api/risk/{cid}")
    assert r.status_code == 200
    baseline = r.get_json()
    assert baseline["risk_colour"] == "Green"

    # 2) Run the stress test overrides described in the scenario
    overrides = {
        "ltv_ratio": 0.52,     # 52%
        "dpd_current": 12,
        "crib_grade": "D",
        "app_login_freq": 0,   # no logins
    }

    sr = client.post("/api/stress-test", json={"customer_id": cid, "overrides": overrides})
    assert sr.status_code == 200
    stressed = sr.get_json()

    # Score should drop significantly
    assert stressed["risk_score"] < baseline["risk_score"]

    # Risk colour should change Green -> Red
    assert baseline["risk_colour"] == "Green"
    assert stressed["risk_colour"] == "Red"

    # Compliance breach due to LTV override must be present
    assert stressed["compliance_breach"] is True
    assert "Private LTV 52% exceeds CBSL cap of 50%" in stressed["compliance_reason"]

    # The codebase does not currently include an explicit "hard_override" flag
    # in the scoring response; instead LTV breaches set `compliance_breach`.
    # Assert the flag is not present (documenting the gap) and the breach exists.
    assert "hard_override" not in stressed

    # 3) Ensure the persisted borrower (simulated DB) is unchanged by the stress test
    r2 = client.get(f"/api/risk/{cid}")
    assert r2.status_code == 200
    after = r2.get_json()

    # Risk after stress test must equal baseline (no DB mutation)
    assert after["risk_score"] == baseline["risk_score"]
    assert after["compliance_breach"] == baseline["compliance_breach"]


@pytest.mark.parametrize("ltv,expected_breach", [
    (0.49, False),
    (0.50, False),
    (0.51, True),
    (0.52, True),
])
def test_ltv_boundary_behavior(client, ltv, expected_breach):
    cid = "stress-test-0001"

    sr = client.post("/api/stress-test", json={
        "customer_id": cid,
        "overrides": {"ltv_ratio": ltv}
    })
    assert sr.status_code == 200
    out = sr.get_json()
    assert out["compliance_breach"] is expected_breach
