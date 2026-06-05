"""Generate validation visualizations from backtest output.

Behavior:
- If a full backtest JSON exists under common locations, it will be loaded.
- Otherwise the script will generate a  sample using existing backtest helpers
  (this regenerates the synthetic dataset only if no saved output is found).

Produces PNGs in the output directory (default: backend/reports).

Usage:
    python backend/tools/validation_reports.py --count 1000 --seed 42 --outdir backend/reports
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import shutil
import sys
from typing import Any

# Make backend importable when running from repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.scoring.scorecard import Scorecard  # type: ignore


def find_existing_backtest() -> Path | None:
    candidates = [
        REPO_ROOT / "backend" / "reports" / "backtest_full.json",
        REPO_ROOT / "backend" / "outputs" / "backtest_full.json",
        REPO_ROOT / "backtest_full.json",
        REPO_ROOT / "backtest.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _simple_persona_generator(n: int, seed: int | None = 42) -> list[dict[str, Any]]:
    """Lightweight generator that creates borrower-like dicts without DB access.

    This mirrors only the fields used by the Scorecard to avoid importing
    `backend/data/seed_data.py` (which depends on psycopg2). Fields are
    intentionally simple but realistic enough for validation plots.
    """
    import random
    from faker import Faker

    fake = Faker()
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    vehicle_types = ["Private", "Commercial"]
    crib_grades = ["A1", "A2", "B1", "C3", "D1", "E3", "XX"]
    records: list[dict[str, Any]] = []
    for i in range(n):
        income = random.randint(30000, 300000)
        obligations = int(income * random.uniform(0.10, 0.65))
        ltv = round(random.uniform(0.05, 0.9), 3)
        sector_npl = round(random.uniform(0.02, 0.12), 4)
        dpd = random.choice([0] * 70 + [15] * 10 + [30] * 8 + [60] * 7 + [120] * 5)
        net_worth = int(income * random.uniform(6, 60))
        rec = {
            "customer_id": f"gen-{i:06d}",
            "vehicle_type": random.choice(vehicle_types),
            "ltv_ratio": ltv,
            "crib_grade": random.choice(crib_grades),
            "monthly_income": income,
            "monthly_obligations": obligations,
            "dpd_current": int(dpd),
            "sector_npl": sector_npl,
            "net_worth": net_worth,
        }
        records.append(rec)
    return records


def generate_or_load(count: int, seed: int, outdir: Path) -> list[dict[str, Any]]:
    # Try to load existing
    existing = find_existing_backtest()
    if existing:
        print(f"Loading existing backtest from: {existing}")
        return json.loads(existing.read_text(encoding="utf-8"))

    print("No existing backtest file found — generating sample (lightweight generator).")
    sample = _simple_persona_generator(count, seed)
    sc = Scorecard()
    results: list[dict[str, Any]] = []

    for b in sample:
        r = sc.calculate(b)
        merged = {**b, **r}
        # normalise numeric types
        for k in ("ltv_ratio", "sector_npl", "monthly_income", "monthly_obligations", "net_worth"):
            if k in merged:
                try:
                    merged[k] = float(merged[k])
                except Exception:
                    pass
        results.append(merged)

    # Save a copy for reproducibility
    outdir.mkdir(parents=True, exist_ok=True)
    save_path = outdir / "backtest_full.json"
    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved generated backtest to {save_path}")
    return results


def simulate_stress(df: pd.DataFrame, sc: Scorecard) -> pd.DataFrame:
    """Apply a simple macro shock and re-score borrowers.

    The shock is intentionally modest and transparent:
    - sector_npl *= 1.5
    - dpd_current += 30 days
    - ltv_ratio += 0.05 (5 percentage points)
    """
    stressed = df.copy(deep=True)
    stressed["sector_npl"] = stressed["sector_npl"].fillna(0.0) * 1.5
    stressed["dpd_current"] = stressed["dpd_current"].fillna(0).astype(int) + 30
    stressed["ltv_ratio"] = stressed["ltv_ratio"].fillna(0.0) + 0.05

    # Re-score
    recs = []
    for _, row in stressed.iterrows():
        b = row.to_dict()
        # keep the required borrower shape
        if "customer_id" not in b:
            b["customer_id"] = f"sim-unknown"
        r = sc.calculate(b)
        rec = {**b, **r}
        recs.append(rec)
    return pd.DataFrame(recs)


def grade_migration_chart(df: pd.DataFrame, stressed_df: pd.DataFrame, outpath: Path) -> None:
    counts_base = df["risk_grade"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)
    counts_stress = stressed_df["risk_grade"].value_counts().reindex(["Low", "Medium", "High"]).fillna(0)

    x = np.arange(len(counts_base))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(x - width / 2, counts_base.values, width, label="Baseline", color=["#2ca02c", "#ff7f0e", "#d62728"])
    ax.bar(x + width / 2, counts_stress.values, width, label="Stress", alpha=0.8, color=["#98df8a", "#ffbb78", "#ff9896"])

    ax.set_xticks(x)
    ax.set_xticklabels(counts_base.index)
    ax.set_ylabel("Count")
    ax.set_title("Grade migration — baseline vs stress scenario")
    for i, (b, s) in enumerate(zip(counts_base.values, counts_stress.values)):
        ax.text(i - width / 2, b + max(1, len(df) * 0.005), str(int(b)), ha="center", va="bottom")
        ax.text(i + width / 2, s + max(1, len(df) * 0.005), str(int(s)), ha="center", va="bottom")

    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def default_calibration_curve(df: pd.DataFrame, outpath: Path, sc: Scorecard) -> None:
    # define delinquency proxy: dpd_current >= 30 days
    df["delinquent"] = df["dpd_current"].fillna(0).astype(int) >= 30

    # Use score bands from config to show calibration per risk band
    bands = sc.config.get("score_bands", {"low_min": 650, "medium_min": 450})
    def risk_band(score: int) -> str:
        if score >= bands["low_min"]:
            return "Low"
        if score >= bands["medium_min"]:
            return "Medium"
        return "High"

    df["score_band"] = df["risk_score"].apply(risk_band)
    agg = df.groupby("score_band").agg(
        avg_score=("risk_score", "mean"),
        delinquency_rate=("delinquent", lambda x: 100 * x.mean()),
        n=("risk_score", "count"),
    ).reindex(["Low", "Medium", "High"]).fillna(0)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(agg["avg_score"], agg["delinquency_rate"], marker="o")
    for i, row in agg.iterrows():
        ax.text(row["avg_score"], row["delinquency_rate"] + 0.2, f"n={int(row['n'])}")
    ax.set_xlabel("Average score (band)")
    ax.set_ylabel("Observed delinquency rate (%)")
    ax.set_title("Default calibration: observed delinquency vs score bands")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def regulatory_scatter(df: pd.DataFrame, outpath: Path) -> None:
    colours = {"Low": "#2ca02c", "Medium": "#ff7f0e", "High": "#d62728"}
    fig, ax = plt.subplots(figsize=(8, 6))

    for g, sub in df.groupby("risk_grade"):
        ax.scatter(sub["ltv_ratio"], sub["risk_score"], label=g, c=colours.get(g, "#777"), alpha=0.7, edgecolor="k", linewidth=0.2)

    # Highlight compliance breaches
    breaches = df[df["compliance_breach"] == True]
    if not breaches.empty:
        ax.scatter(breaches["ltv_ratio"], breaches["risk_score"], facecolors="none", edgecolors="black", s=80, linewidth=1.2, label="Compliance breach")

    ax.axvline(0.5, color="black", linestyle="--", label="LTV = 50% threshold")
    ax.set_xlabel("LTV ratio")
    ax.set_ylabel("Final score")
    ax.set_title("Regulatory boundary: LTV vs final score (colour = risk band)")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 1000)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", type=str, default="backend/reports")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    records = generate_or_load(args.count, args.seed, outdir)
    df = pd.DataFrame(records)

    sc = Scorecard()

    stressed_df = simulate_stress(df, sc)

    # Chart 1
    p1 = outdir / "grade_migration.png"
    grade_migration_chart(df, stressed_df, p1)

    # Chart 2
    p2 = outdir / "default_calibration.png"
    default_calibration_curve(df, p2, sc)

    # Chart 3
    p3 = outdir / "regulatory_scatter.png"
    regulatory_scatter(df, p3)

    print("Charts saved:")
    print(p1)
    print(p2)
    print(p3)


if __name__ == "__main__":
    main()
