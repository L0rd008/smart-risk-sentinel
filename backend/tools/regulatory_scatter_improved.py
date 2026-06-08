"""Improved regulatory scatter visualization using the canonical LTV gate.

This script loads an existing backtest JSON (if present), re-evaluates
compliance using the single source of truth in `app.compliance.ltv_gate`,
and produces two improved charts in `backend/reports`:

- `regulatory_scatter_improved_facets.png` — one subplot per vehicle type
  with the correct vehicle-specific LTV threshold drawn and breaches
  highlighted.
- `regulatory_scatter_improved_combined.png` — all borrowers on one plot
  with threshold lines for each category and breaches highlighted.

Also writes `regulatory_scatter_breach_mismatches.csv` listing any rows
where the JSON's stored `compliance_breach` disagrees with the gate.

This is a non-production analysis tool and intentionally does not modify
application code.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from app.compliance.ltv_gate import ltv_gate, LTV_CAPS


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


def load_backtest() -> pd.DataFrame:
    p = find_existing_backtest()
    if not p:
        raise SystemExit("No backtest JSON found in known locations. Run the backtest first or place backtest_full.json under backend/reports.")
    data = json.loads(p.read_text(encoding="utf-8"))
    df = pd.DataFrame(data)
    # ensure expected columns exist
    if "ltv_ratio" not in df.columns:
        raise SystemExit("backtest JSON missing 'ltv_ratio' column")
    return df


def recompute_breaches(df: pd.DataFrame) -> pd.DataFrame:
    # apply canonical ltv_gate over the dataset
    def _check(row: Any) -> bool:
        vt = row.get("vehicle_type")
        ltv = float(row.get("ltv_ratio", 0.0))
        return ltv_gate(vt, ltv)["breach"]

    df = df.copy()
    df["recalc_breach"] = df.apply(_check, axis=1)
    return df


def plot_facets(df: pd.DataFrame, outpath: Path) -> None:
    vehicle_types = sorted(df["vehicle_type"].fillna("Unknown").unique())
    # keep only categories with data
    n = len(vehicle_types)
    cols = min(3, n)
    rows = int(np.ceil(n / cols))

    colours = {"Low": "#2ca02c", "Medium": "#ff7f0e", "High": "#d62728"}

    fig, axes = plt.subplots(rows, cols, figsize=(6 * cols, 4 * rows), squeeze=False)
    axes_flat = axes.flatten()

    for i, vt in enumerate(vehicle_types):
        ax = axes_flat[i]
        sub = df[df["vehicle_type"] == vt]
        for g, subg in sub.groupby("risk_grade"):
            ax.scatter(subg["ltv_ratio"], subg["risk_score"], label=g, c=colours.get(g, "#777"), alpha=0.7, edgecolor="k", linewidth=0.2)

        breaches = sub[sub["recalc_breach"] == True]
        if not breaches.empty:
            ax.scatter(breaches["ltv_ratio"], breaches["risk_score"], facecolors="none", edgecolors="black", s=80, linewidth=1.2, label="Breach")

        # draw category-specific threshold if known
        cap = LTV_CAPS.get(vt)
        if cap is not None:
            ax.axvline(cap, color="black", linestyle="--", label=f"LTV cap ({int(cap*100)}%)")

        ax.set_title(f"{vt} (n={len(sub)})")
        ax.set_xlabel("LTV ratio")
        ax.set_ylabel("Final score")
        ax.set_xlim(left=0)
        ax.set_ylim(0, 1000)
        ax.legend()

    # hide unused axes
    for j in range(i + 1, len(axes_flat)):
        fig.delaxes(axes_flat[j])

    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def plot_combined(df: pd.DataFrame, outpath: Path) -> None:
    colours = {"Low": "#2ca02c", "Medium": "#ff7f0e", "High": "#d62728"}
    fig, ax = plt.subplots(figsize=(10, 6))
    for g, sub in df.groupby("risk_grade"):
        ax.scatter(sub["ltv_ratio"], sub["risk_score"], label=g, c=colours.get(g, "#777"), alpha=0.6, edgecolor="k", linewidth=0.2)

    breaches = df[df["recalc_breach"] == True]
    if not breaches.empty:
        ax.scatter(breaches["ltv_ratio"], breaches["risk_score"], facecolors="none", edgecolors="black", s=80, linewidth=1.2, label="Breach")

    # draw threshold lines for each known category
    for vt, cap in LTV_CAPS.items():
        ax.axvline(cap, linestyle="--", label=f"{vt} cap = {int(cap*100)}%")

    ax.set_xlabel("LTV ratio")
    ax.set_ylabel("Final score")
    ax.set_title("Regulatory scatter — correct category-specific LTV caps")
    ax.set_xlim(left=0)
    ax.set_ylim(0, 1000)
    ax.legend()
    fig.tight_layout()
    fig.savefig(outpath, dpi=150)
    plt.close(fig)


def write_mismatches(df: pd.DataFrame, outpath: Path) -> int:
    # Compare original compliance flag to recalculated gate
    if "compliance_breach" not in df.columns:
        df["compliance_breach"] = None
    mismatches = df[df["compliance_breach"].fillna(False) != df["recalc_breach"].fillna(False)]
    mismatches.to_csv(outpath, index=False)
    return len(mismatches)


def main() -> None:
    outdir = REPO_ROOT / "backend" / "reports"
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_backtest()
    df = recompute_breaches(df)

    # summary
    vehicle_types = sorted(df["vehicle_type"].unique())
    print("Vehicle categories found:", vehicle_types)
    print("LTV caps from canonical gate:")
    for k, v in LTV_CAPS.items():
        print(f"  - {k}: {v:.2%}")

    mismatches_count = write_mismatches(df, outdir / "regulatory_scatter_breach_mismatches.csv")
    print(f"Mismatches between stored compliance_breach and ltv_gate: {mismatches_count}")

    # plots
    plot_facets(df, outdir / "regulatory_scatter_improved_facets.png")
    plot_combined(df, outdir / "regulatory_scatter_improved_combined.png")

    print("Improved charts written to:")
    print(outdir / "regulatory_scatter_improved_facets.png")
    print(outdir / "regulatory_scatter_improved_combined.png")
    print(outdir / "regulatory_scatter_breach_mismatches.csv")


if __name__ == "__main__":
    main()
