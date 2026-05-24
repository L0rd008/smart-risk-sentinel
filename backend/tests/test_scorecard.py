"""Scorecard unit tests.

Owned by Member 2 (Scoring Engine) and Member 5 (Integration). Run with:
    pytest backend/tests/test_scorecard.py -v

These tests do NOT hit the database. They construct in-memory borrower
dicts that match the API contract shape and assert on Scorecard output.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Allow running pytest from the repo root by putting backend/ on sys.path.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scoring.scorecard import Scorecard  # noqa: E402
from app.compliance.ltv_gate import ltv_gate  # noqa: E402


@pytest.fixture(scope="module")
def scorecard() -> Scorecard:
    return Scorecard()


def _base_borrower(**overrides):
    """A neutral mid-spectrum borrower; tweak attributes via kwargs."""
    base = {
        "customer_id":         "test-uuid-0001",
        "name":                "Test Borrower",
        "age":                 35,
        "sector_code":         "SERVICES",
        "annual_income":       3_600_000,
        "monthly_income":      300_000,
        "monthly_obligations": 90_000,
        "crib_grade":          "B",
        "net_worth":           5_000_000,
        "app_login_freq":      10,
        "vehicle_type":        "Private",
        "vehicle_value":       8_000_000,
        "loan_amount":         3_200_000,
        "ltv_ratio":           0.40,
        "dpd_current":         0,
        "dpd_pattern":         [0, 0, 0, 0, 0, 0],
        "sector_npl":          0.045,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. LTV breach forces High/Red regardless of score
# ---------------------------------------------------------------------------

def test_ltv_breach_private_forces_red(scorecard):
    borrower = _base_borrower(
        crib_grade="A",
        monthly_obligations=30_000,     # very low DTI -> high score
        ltv_ratio=0.55,                 # but breaches 50% cap
        vehicle_type="Private",
    )
    risk = scorecard.calculate(borrower)
    assert risk["compliance_breach"] is True
    assert risk["risk_grade"] == "High"
    assert risk["risk_colour"] == "Red"
    assert "50%" in risk["compliance_reason"]


def test_ltv_breach_commercial_forces_red(scorecard):
    borrower = _base_borrower(
        crib_grade="A",
        monthly_obligations=30_000,
        vehicle_type="Commercial",
        ltv_ratio=0.72,                 # breaches 70% cap
    )
    risk = scorecard.calculate(borrower)
    assert risk["compliance_breach"] is True
    assert risk["risk_grade"] == "High"
    assert "70%" in risk["compliance_reason"]


def test_ltv_at_exact_cap_is_not_a_breach(scorecard):
    """LTV equal to the cap is allowed; only strictly greater than breaches."""
    borrower = _base_borrower(ltv_ratio=0.50, vehicle_type="Private")
    risk = scorecard.calculate(borrower)
    assert risk["compliance_breach"] is False


# ---------------------------------------------------------------------------
# 2. Grade XX (no CRIB history) yields negative character contribution
# ---------------------------------------------------------------------------

def test_crib_grade_xx_drags_score_down(scorecard):
    base = scorecard.calculate(_base_borrower(crib_grade="B"))
    xx = scorecard.calculate(_base_borrower(crib_grade="XX"))
    assert xx["risk_score"] < base["risk_score"]
    # XX should also flag CRIB as Red EWI
    crib_flag = next(f for f in xx["ewi_flags"] if f["indicator"] == "CRIB Grade")
    assert crib_flag["status"] == "Red"


# ---------------------------------------------------------------------------
# 3. Near-perfect input lands in the Low/Green band
# ---------------------------------------------------------------------------

def test_perfect_borrower_is_low_risk(scorecard):
    borrower = _base_borrower(
        crib_grade="A",
        monthly_income=500_000,
        monthly_obligations=50_000,     # DTI 10%
        ltv_ratio=0.25,                 # well under cap
        dpd_current=0,
        dpd_pattern=[0]*6,
        net_worth=60_000_000,           # 100x annual obligation
        app_login_freq=25,
        sector_npl=0.025,
    )
    risk = scorecard.calculate(borrower)
    assert risk["risk_grade"] == "Low"
    assert risk["risk_colour"] == "Green"
    assert risk["risk_score"] >= 650


# ---------------------------------------------------------------------------
# 4. Worst-case input lands in the High/Red band even without LTV breach
# ---------------------------------------------------------------------------

def test_worst_case_borrower_is_high_risk(scorecard):
    borrower = _base_borrower(
        crib_grade="E",
        monthly_income=150_000,
        monthly_obligations=130_000,    # DTI ~87%
        ltv_ratio=0.49,                 # just under cap, no breach
        dpd_current=45,
        dpd_pattern=[10, 18, 25, 35, 40, 45],
        net_worth=50_000,               # negligible
        app_login_freq=0,
        sector_npl=0.18,
    )
    risk = scorecard.calculate(borrower)
    assert risk["compliance_breach"] is False
    assert risk["risk_grade"] == "High"
    assert risk["risk_colour"] == "Red"
    assert risk["risk_score"] < 450


# ---------------------------------------------------------------------------
# 5. The response shape matches the API contract
# ---------------------------------------------------------------------------

def test_calculate_returns_full_contract_shape(scorecard):
    risk = scorecard.calculate(_base_borrower())
    expected_keys = {
        "customer_id", "risk_score", "risk_grade", "risk_colour",
        "compliance_breach", "compliance_reason",
        "top_risk_drivers", "category_scores", "ewi_flags",
        "recommended_action", "calculated_at",
    }
    assert set(risk.keys()) == expected_keys

    expected_categories = {"capacity", "character", "collateral", "conditions", "capital"}
    assert set(risk["category_scores"].keys()) == expected_categories

    # EWI list must include the 5 indicators
    indicators = {f["indicator"] for f in risk["ewi_flags"]}
    assert "Payment Delay" in indicators
    assert "CRIB Grade" in indicators
    assert "App Login Frequency" in indicators
    assert "Sector NPL" in indicators
    assert any("LTV" in i for i in indicators)

    assert 0 <= risk["risk_score"] <= 1000


# ---------------------------------------------------------------------------
# 6. LTV gate is pure and independent
# ---------------------------------------------------------------------------

def test_ltv_gate_function_directly():
    assert ltv_gate("Private", 0.50)["breach"] is False
    assert ltv_gate("Private", 0.5001)["breach"] is True
    assert ltv_gate("Commercial", 0.70)["breach"] is False
    assert ltv_gate("Commercial", 0.71)["breach"] is True
    # Unknown vehicle type -> no cap configured, no breach
    assert ltv_gate("Tractor", 0.99)["breach"] is False
