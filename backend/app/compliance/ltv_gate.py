"""CBSL Loan-to-Value (LTV) compliance gate.

Owned by Member 3. This file is the single source of truth for the LTV
cap rule — both `risk_routes.py` and the `Scorecard` engine import from
here. **Do not re-implement the cap check elsewhere.**

Source: CBSL Directions No. 03 of 2025 (Loan-to-Value Ratios for Credit
Facilities Granted in Respect of Motor Vehicles), issued to all licensed
finance companies.
"""
from typing import Optional, TypedDict

LTV_CAPS: dict[str, float] = {
    "Private": 0.50,
    "Commercial": 0.70,
}


class LtvGateResult(TypedDict):
    breach: bool
    reason: Optional[str]


def ltv_gate(vehicle_type: str, ltv_ratio: float) -> LtvGateResult:
    """Return whether a given LTV breaches the CBSL cap for the vehicle type.

    Args:
        vehicle_type: 'Private' or 'Commercial' (anything else returns no breach).
        ltv_ratio: decimal LTV, e.g. 0.45 for 45%.

    Returns:
        {"breach": True,  "reason": "<human-readable reason>"} on breach
        {"breach": False, "reason": None} otherwise
    """
    cap = LTV_CAPS.get(vehicle_type)
    if cap is not None and ltv_ratio > cap:
        return {
            "breach": True,
            "reason": (
                f"{vehicle_type} LTV {ltv_ratio:.0%} "
                f"exceeds CBSL cap of {cap:.0%}"
            ),
        }
    return {"breach": False, "reason": None}
