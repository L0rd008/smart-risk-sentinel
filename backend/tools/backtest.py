"""Backtest / calibration harness for the Scorecard.

Generates synthetic borrowers (in-memory) using the existing
`backend/data/seed_data.py` generators and runs `Scorecard.calculate`
over the sample. Outputs grade distribution, average scores, and a
small sample of records per grade. This script does NOT write to the DB.

Usage (from repo root with venv activated):
    python backend/tools/backtest.py --count 1000 --seed 42
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any

# Ensure backend/ is importable when running from repo root
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scoring.scorecard import Scorecard  # noqa: E402
from data.seed_data import generate_persona, _weighted_persona_pick  # noqa: E402


def sample_borrowers(n: int, seed: int | None = None):
    if seed is not None:
        random.seed(seed)
    borrowers = []
    used = set()
    for _ in range(n):
        persona = _weighted_persona_pick()
        borrowers.append(generate_persona(persona, used))
    return borrowers


def run_backtest(count: int = 1000, seed: int | None = 42) -> dict[str, Any]:
    sc = Scorecard()
    sample = sample_borrowers(count, seed)

    results: list[dict[str, Any]] = []
    for b in sample:
        # Scorecard.calculate expects a customer_id key in the borrower dict
        if "customer_id" not in b:
            b["customer_id"] = f"sim-{random.randrange(10**9):09d}"
        r = sc.calculate(b)
        results.append(r)

    by_grade = {"Low": [], "Medium": [], "High": []}
    for r in results:
        by_grade[r["risk_grade"]].append(r["risk_score"])

    report = {
        "count": count,
        "distribution": {g: len(v) for g, v in by_grade.items()},
        "distribution_pct": {g: round(100 * len(v) / count, 1) for g, v in by_grade.items()},
        "avg_score_by_grade": {g: (int(round(statistics.mean(v))) if v else None) for g, v in by_grade.items()},
    }

    # include small samples
    samples = {}
    for g, scores in by_grade.items():
        samples[g] = sorted(scores)[:3] + (sorted(scores)[-3:] if len(scores) >= 3 else [])
    report["example_scores"] = samples

    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    rep = run_backtest(args.count, args.seed)
    if args.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f"Backtest sample count: {rep['count']}")
        print("Distribution (counts):")
        for g, c in rep["distribution"].items():
            print(f"  {g}: {c} ({rep['distribution_pct'][g]}%)")
        print("Average score by grade:")
        for g, a in rep["avg_score_by_grade"].items():
            print(f"  {g}: {a}")
        print("Example scores (low..high):")
        for g, s in rep["example_scores"].items():
            print(f"  {g}: {s}")


if __name__ == "__main__":
    main()
