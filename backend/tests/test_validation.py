"""Validation-focused unit tests.

These tests assert how the Scorecard currently behaves when given
invalid or out-of-range inputs. The intent is to document current
behavior rather than change production code.
"""
from __future__ import annotations

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scoring.scorecard import Scorecard  # noqa: E402


def _base_borrower(**overrides):
    b = {
        "customer_id": "val-0001",
        "vehicle_type": "Private",
        "ltv_ratio": 0.40,
        "crib_grade": "B",
        "monthly_income": 200_000,
        "monthly_obligations": 50_000,
        "dpd_current": 0,
        "sector_npl": 0.04,
        "net_worth": 2_000_000,
        "age": 35,
        "tenure_months": 24,
    }
    b.update(overrides)
    return b


def test_invalid_crib_grade_is_handled_by_scorecard():
    """Scorecard should not raise on unexpected crib strings; it will
    look up bins and fall back to the configured default (-150) when
    missing. Document the current behavior.
    """
    sc = Scorecard()
    # Use an explicitly invalid grade 'Z' (not in config). We expect the
    # score to be lower than the equivalent borrower with a strong 'A' grade
    # because unknown grades fall back to a negative contribution.
    borrower = _base_borrower(crib_grade="Z")
    out = sc.calculate(borrower)

    assert isinstance(out["risk_score"], int)
    ref = sc.calculate(_base_borrower(crib_grade="A"))
    assert out["risk_score"] < ref["risk_score"]


def test_invalid_age_range_ignored_by_scorecard():
    """Age is part of borrower shape but not used in scoring. The
    scorecard currently ignores out-of-range ages rather than validating.
    """
    sc = Scorecard()
    young = _base_borrower(age=10)
    old = _base_borrower(age=150)
    o1 = sc.calculate(young)
    o2 = sc.calculate(old)
    assert isinstance(o1["risk_score"], int)
    assert isinstance(o2["risk_score"], int)


def test_invalid_ltv_values_coerced_or_used_directly():
    """Scorecard expects a numeric ltv_ratio. Non-numeric inputs should
    either be coerced by float() where used (and may raise), but the
    route code normalizes types before saving. Document current behavior.
    """
    sc = Scorecard()
    # A string that looks numeric is accepted via float() conversion
    b1 = _base_borrower(ltv_ratio="0.45")
    out1 = sc.calculate(b1)
    assert isinstance(out1["risk_score"], int)

    # A completely invalid string will raise when float() is called; we
    # assert that Scorecard currently will raise a ValueError in that case.
    b2 = _base_borrower(ltv_ratio="not-a-number")
    try:
        sc.calculate(b2)
        raised = False
    except Exception:
        raised = True
    assert raised is True


def test_invalid_tenure_is_ignored_by_scorecard():
    """Tenure is not a scoring input; passing negative or extreme
    tenure values is currently ignored by the Scorecard (no validation).
    """
    sc = Scorecard()
    b = _base_borrower(tenure_months=-12)
    out = sc.calculate(b)
    assert isinstance(out["risk_score"], int)
