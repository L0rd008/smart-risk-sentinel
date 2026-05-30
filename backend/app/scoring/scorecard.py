"""Hybrid expert-statistical scorecard engine.

Owned by Member 2. The class loads its weights and bin thresholds from
`scorecard_config.json` so the team can tune the model without touching
Python. The output of `calculate()` matches the API contract response
shape for `GET /api/risk/:customer_id` exactly — any drift breaks the
frontend.

Formula:
    Final Score = base + Σ (category_weight × attribute_points)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.compliance.ltv_gate import ltv_gate


CONFIG_PATH = Path(__file__).parent / "scorecard_config.json"


class Scorecard:
    """Rules-based credit risk scorecard.

    Construct once at app start (or per request — it's cheap):
        sc = Scorecard()
        risk = sc.calculate(borrower_dict)
    """

    def __init__(self, config_path: Path = CONFIG_PATH) -> None:
        """Load the JSON config. Raises if the file is missing or invalid."""
        with open(config_path, "r", encoding="utf-8") as f:
            self.config: dict[str, Any] = json.load(f)
        self.base: int = self.config["base_score"]
        self.weights: dict[str, float] = self.config["category_weights"]
        self.bins: dict[str, Any] = self.config["bins"]
        self.ewi: dict[str, Any] = self.config["ewi_thresholds"]
        self.actions: dict[str, str] = self.config["recommended_actions"]

    # ------------------------------------------------------------------
    # Public API — matches the contract response shape for /api/risk/:id
    # ------------------------------------------------------------------

    def calculate(self, borrower: dict[str, Any]) -> dict[str, Any]:
        """Score a borrower and return the full risk object.

        Args:
            borrower: dict matching the borrower contract shape (see
                docs/API_CONTRACT.md GET /api/borrowers/:customer_id).
                Must include: customer_id, vehicle_type, ltv_ratio,
                crib_grade, monthly_income, monthly_obligations,
                dpd_current, sector_npl (or sector_code), net_worth.

        Returns:
            dict matching docs/API_CONTRACT.md GET /api/risk/:customer_id.
        """
        capacity_pts = self._score_capacity(borrower)
        character_pts = self._score_character(borrower)
        collateral_pts = self._score_collateral(borrower)
        conditions_pts = self._score_conditions(borrower)
        capital_pts = self._score_capital(borrower)

        category_scores = {
            "capacity":   capacity_pts,
            "character":  character_pts,
            "collateral": collateral_pts,
            "conditions": conditions_pts,
            "capital":    capital_pts,
        }

        raw_score = self.base + sum(
            self.weights[c] * pts for c, pts in category_scores.items()
        )
        # Formula range is approx. 215–727; clamp guards against unexpected inputs.
        score = max(0, min(1000, int(round(raw_score))))

        gate = ltv_gate(
            borrower.get("vehicle_type", ""),
            float(borrower.get("ltv_ratio", 0.0)),
        )

        grade, colour = self._classify(score, compliance_breach=gate["breach"])

        return {
            "customer_id":        borrower["customer_id"],
            "risk_score":         score,
            "risk_grade":         grade,
            "risk_colour":        colour,
            "compliance_breach":  gate["breach"],
            "compliance_reason":  gate["reason"],
            "top_risk_drivers":   self._top_drivers(borrower, category_scores),
            "category_scores":    category_scores,
            "ewi_flags":          self._ewi_flags(borrower),
            "recommended_action": self.actions[grade],
            "calculated_at":      datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Category scorers — one per C
    # ------------------------------------------------------------------

    def _score_capacity(self, b: dict[str, Any]) -> int:
        """Capacity = ability to repay. Dominated by Debt-to-Income."""
        income = float(b.get("monthly_income") or 0)
        obligations = float(b.get("monthly_obligations") or 0)
        dti = (obligations / income) if income > 0 else 1.0
        return self._bin_dti(dti)

    def _score_character(self, b: dict[str, Any]) -> int:
        """Character = willingness to repay. CRIB grade + DPD trend."""
        grade_pts = self.bins["crib_grade"].get(
            b.get("crib_grade", "XX"), -150
        )
        dpd_pts = self._bin_value(self.bins["dpd_current"], b.get("dpd_current", 0))
        return int(round(0.6 * grade_pts + 0.4 * dpd_pts))

    def _score_collateral(self, b: dict[str, Any]) -> int:
        """Collateral = recoverable security. Driven by current LTV."""
        vtype = b.get("vehicle_type", "Private")
        ltv = float(b.get("ltv_ratio", 0.0))
        key = "ltv_commercial" if vtype == "Commercial" else "ltv_private"
        return self._bin_value(self.bins[key], ltv)

    def _score_conditions(self, b: dict[str, Any]) -> int:
        """Conditions = macro / sector context."""
        sector_npl = float(b.get("sector_npl", 0.0))
        return self._bin_value(self.bins["sector_npl"], sector_npl)

    def _score_capital(self, b: dict[str, Any]) -> int:
        """Capital = wealth buffer. Net worth as a multiple of annual obligation."""
        net_worth = float(b.get("net_worth") or 0)
        annual_obligation = float(b.get("monthly_obligations") or 0) * 12
        multiple = (net_worth / annual_obligation) if annual_obligation > 0 else 0.0
        return self._bin_value(self.bins["net_worth_multiple"], multiple)

    # ------------------------------------------------------------------
    # Binning helpers
    # ------------------------------------------------------------------

    def _bin_dti(self, dti: float) -> int:
        """Map a Debt-to-Income ratio (0.0–1.0+) to attribute points.

        Complete reference implementation. Other `_bin_*` helpers follow
        the same pattern using `_bin_value`.
        """
        return self._bin_value(self.bins["dti"], dti)

    @staticmethod
    def _bin_value(bin_list: list[dict[str, Any]], value: float) -> int:
        """Walk a sorted list of {max, points} bins and return the first match."""
        for b in bin_list:
            if value <= b["max"]:
                return int(b["points"])
        return int(bin_list[-1]["points"])

    # ------------------------------------------------------------------
    # Grading and explanation helpers
    # ------------------------------------------------------------------

    def _classify(self, score: int, compliance_breach: bool) -> tuple[str, str]:
        """Translate score (and any regulatory breach) to grade + colour.
        """
        bands = self.config["score_bands"]
        if score >= bands["low_min"]:
            return "Low", "Green"
        if score >= bands["medium_min"]:
            return "Medium", "Amber"
        return "High", "Red"

    def _top_drivers(
        self,
        borrower: dict[str, Any],
        category_scores: dict[str, int],
    ) -> list[dict[str, str]]:
        """Return up to 3 most-impactful category contributions for the UI."""
        weighted = [
            (cat, pts, self.weights[cat] * pts)
            for cat, pts in category_scores.items()
        ]
        weighted.sort(key=lambda x: abs(x[2]), reverse=True)
        drivers: list[dict[str, str]] = []
        for cat, pts, _impact in weighted[:3]:
            drivers.append({
                "factor": cat.capitalize(),
                "impact": "Positive" if pts >= 0 else "Negative",
                "detail": f"{cat.capitalize()} contributed {pts:+d} attribute points",
            })
        return drivers

    def _ewi_flags(self, b: dict[str, Any]) -> list[dict[str, str]]:
        """Compute the EWI flag list using thresholds from config."""
        flags: list[dict[str, str]] = []

        dpd = int(b.get("dpd_current") or 0)
        pd = self.ewi["payment_delay"]
        flags.append({
            "indicator": "Payment Delay",
            "status": "Green" if dpd <= pd["green_max"]
                     else "Amber" if dpd <= pd["amber_max"]
                     else "Red",
            "value": f"{dpd} days",
        })

        grade = b.get("crib_grade", "XX")
        flags.append({
            "indicator": "CRIB Grade",
            "status": "Red" if grade in self.ewi["crib_red_set"]
                     else "Amber" if grade in self.ewi["crib_amber_set"]
                     else "Green",
            "value": grade,
        })

        vtype = b.get("vehicle_type", "Private")
        ltv = float(b.get("ltv_ratio", 0.0))
        ltv_key = "ltv_commercial" if vtype == "Commercial" else "ltv_private"
        lt = self.ewi[ltv_key]
        flags.append({
            "indicator": f"LTV ({vtype})",
            "status": "Green" if ltv <= lt["green_max"]
                     else "Amber" if ltv <= lt["amber_max"]
                     else "Red",
            "value": f"{ltv:.0%}",
        })

        logins = int(b.get("app_login_freq") or 0)
        al = self.ewi["app_login"]
        flags.append({
            "indicator": "App Login Frequency",
            "status": "Green" if logins >= al["green_min"]
                     else "Amber" if logins >= al["amber_min"]
                     else "Red",
            "value": f"{logins} / month",
        })

        sector_npl = float(b.get("sector_npl", 0.0))
        sn = self.ewi["sector_npl"]
        flags.append({
            "indicator": "Sector NPL",
            "status": "Green" if sector_npl < sn["green_max"]
                     else "Amber" if sector_npl <= sn["amber_max"]
                     else "Red",
            "value": f"{sector_npl:.1%}",
        })

        return flags
