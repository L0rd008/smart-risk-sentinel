"""Validation summary for backtest outputs.

Produces:
- backend/reports/validation_metrics.json
- backend/reports/validation_metrics.csv

Calculates:
- Confusion matrix (High band -> predicted default) vs DPD-based delinquent (dpd_current >= 30)
- Precision, Recall, F1
- Capture rate of delinquent borrowers by High-risk band
- Gini coefficient (from AUC)
- KS statistic between score distributions of delinquent and non-delinquent

Also computes a Model Confidence Score (0-1) combining:
- calibration_quality (via Brier score on a predicted PD derived from score)
- risk_band_separation (difference in mean predicted PD between High and Low bands)
- stress_test_stability (change in Gini under a simple stress scenario)

Assumptions and methodology are saved inside the JSON under "notes".
This script intentionally does not modify production code; it reads existing reports.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# make backend importable
REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
import sys
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scoring.scorecard import Scorecard  # type: ignore


def find_existing_backtest() -> Path | None:
    # Search several plausible locations relative to this file and the current working dir
    candidates = []
    # current working directory
    cwd = Path.cwd()
    candidates += [
        cwd / "backend" / "reports" / "backtest_full.json",
        cwd / "backend" / "outputs" / "backtest_full.json",
        cwd / "backtest_full.json",
        cwd / "backtest.json",
    ]

    # check parent folders of this file (up to 4 levels)
    p = Path(__file__).resolve()
    for i in range(1, 5):
        root = p.parents[i]
        candidates += [
            root / "backend" / "reports" / "backtest_full.json",
            root / "backend" / "outputs" / "backtest_full.json",
            root / "backtest_full.json",
            root / "backtest.json",
        ]

    # remove duplicates but preserve order
    seen = set()
    uniq = []
    for c in candidates:
        cstr = str(c)
        if cstr not in seen:
            seen.add(cstr)
            uniq.append(c)

    for p in uniq:
        if p.exists():
            return p
    return None


def load_backtest() -> pd.DataFrame:
    p = find_existing_backtest()
    if p is None:
        raise FileNotFoundError("No backtest JSON found in expected locations.")
    data = json.loads(p.read_text(encoding="utf-8"))
    df = pd.DataFrame(data)
    return df


def delinquent_mask(df: pd.DataFrame, days: int = 30) -> pd.Series:
    return df.get("dpd_current", pd.Series(0)).fillna(0).astype(int) >= days


def binary_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, int]:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return {"tp": tp, "tn": tn, "fp": fp, "fn": fn}


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {"precision": prec, "recall": rec, "f1": f1}


def auc_from_scores(y_true: np.ndarray, scores: np.ndarray) -> float:
    # AUC via rank-sum (equivalent to Mann-Whitney U)
    # higher scores should indicate lower PD in this scorecard, so we use score as-is
    # but to ensure higher -> more likely positive, we invert: use -scores so larger -> higher default propensity
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)

    pos_ranks_sum = ranks[y_true == 1].sum()
    n_pos = int((y_true == 1).sum())
    n_neg = int((y_true == 0).sum())
    if n_pos == 0 or n_neg == 0:
        return float('nan')
    auc = (pos_ranks_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


def gini_from_auc(auc: float) -> float:
    if np.isnan(auc):
        return float('nan')
    return 2 * auc - 1


def ks_statistic(y_true: np.ndarray, scores: np.ndarray) -> float:
    # Compute empirical CDFs for scores among positives and negatives and return max difference
    pos_scores = scores[y_true == 1]
    neg_scores = scores[y_true == 0]
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return float('nan')
    all_scores = np.sort(np.unique(scores))
    cdf_pos = np.searchsorted(np.sort(pos_scores), all_scores, side='right') / len(pos_scores)
    cdf_neg = np.searchsorted(np.sort(neg_scores), all_scores, side='right') / len(neg_scores)
    return float(np.max(np.abs(cdf_pos - cdf_neg)))


def predicted_pd_from_score(scores: np.ndarray) -> np.ndarray:
    # Simple linear mapping of score -> [0,1] PD by min-max scaling and inversion
    # Higher risk_score historically mapped to better credit (higher numeric score = lower PD),
    # so we invert so higher predicted PD corresponds to higher default propensity.
    s_min = float(np.nanmin(scores))
    s_max = float(np.nanmax(scores))
    if s_max == s_min:
        return np.full_like(scores, 0.5, dtype=float)
    scaled = (scores - s_min) / (s_max - s_min)
    pred_pd = 1.0 - scaled
    return pred_pd


def stress_rescore(df: pd.DataFrame, sc: Scorecard) -> pd.DataFrame:
    stressed = df.copy(deep=True)
    stressed['sector_npl'] = stressed.get('sector_npl', 0.0).fillna(0.0) * 1.5
    stressed['dpd_current'] = stressed.get('dpd_current', 0).fillna(0).astype(int) + 30
    stressed['ltv_ratio'] = stressed.get('ltv_ratio', 0.0).fillna(0.0) + 0.05

    recs = []
    for _, row in stressed.iterrows():
        b = row.to_dict()
        if 'customer_id' not in b:
            b['customer_id'] = 'sim-unknown'
        r = sc.calculate(b)
        rec = {**b, **r}
        recs.append(rec)
    return pd.DataFrame(recs)


def compute_model_confidence(calibration_brier: float, band_separation: float, gini_base: float, gini_stress: float) -> dict[str, Any]:
    # calibration_brier in [0,1] (lower better)
    # We'll convert to calibration_quality in [0,1] where 1 is best: calibration_quality = 1 - brier
    calibration_quality = max(0.0, 1.0 - float(calibration_brier))

    # band_separation already in [0,1]
    separation = float(np.clip(band_separation, 0.0, 1.0))

    # stress stability: 1 - |gini_base - gini_stress|
    if np.isnan(gini_base) or np.isnan(gini_stress):
        stability = float('nan')
    else:
        stability = max(0.0, 1.0 - abs(float(gini_base) - float(gini_stress)))

    # Weights chosen to emphasise calibration slightly more
    w_cal, w_sep, w_stab = 0.4, 0.3, 0.3
    comps = [calibration_quality, separation, stability if not np.isnan(stability) else 0.0]
    mcs = float(np.nansum([w_cal * comps[0], w_sep * comps[1], w_stab * comps[2]]))
    mcs = float(np.clip(mcs, 0.0, 1.0))
    return {
        "calibration_quality": calibration_quality,
        "risk_band_separation": separation,
        "stress_test_stability": stability,
        "model_confidence_score": mcs,
        "weights": {"calibration": w_cal, "separation": w_sep, "stability": w_stab},
    }


def main() -> None:
    outdir = REPO_ROOT / 'backend' / 'reports'
    outdir.mkdir(parents=True, exist_ok=True)

    df = load_backtest()
    sc = Scorecard()

    # Ensure risk_score and risk_grade exist (some records from generator may not include them)
    if 'risk_score' not in df.columns or 'risk_grade' not in df.columns:
        # attempt to calculate for missing rows
        recs = []
        for _, row in df.iterrows():
            r = row.to_dict()
            if 'risk_score' not in r or 'risk_grade' not in r:
                rcalc = sc.calculate(r)
                r = {**r, **rcalc}
            recs.append(r)
        df = pd.DataFrame(recs)

    df['delinquent'] = delinquent_mask(df, days=30)
    y_true = df['delinquent'].astype(int).to_numpy()
    y_pred = (df.get('risk_grade', '') == 'High').astype(int).to_numpy()

    cm = binary_confusion(y_true, y_pred)
    prf = precision_recall_f1(cm['tp'], cm['fp'], cm['fn'])

    # Capture rate: of actual delinquents, fraction assigned to High band
    total_delinq = int(y_true.sum())
    captured = int(((y_true == 1) & (y_pred == 1)).sum())
    capture_rate = float(captured / total_delinq) if total_delinq > 0 else float('nan')

    scores = df['risk_score'].to_numpy(dtype=float)
    auc = auc_from_scores(y_true, scores)
    gini = gini_from_auc(auc) if not np.isnan(auc) else float('nan')
    ks = ks_statistic(y_true, scores)

    # calibration: using predicted PD from score via min-max inversion, then Brier score
    pred_pd = predicted_pd_from_score(scores)
    brier = float(np.mean((pred_pd - y_true) ** 2))

    # risk band separation: mean predicted PD in High minus mean in Low (should be positive)
    band_means = df.groupby('risk_grade').apply(lambda d: predicted_pd_from_score(d['risk_score'].to_numpy()).mean() if len(d) > 0 else np.nan)
    mean_high = float(band_means.get('High', np.nan)) if 'High' in band_means.index else float('nan')
    mean_low = float(band_means.get('Low', np.nan)) if 'Low' in band_means.index else float('nan')
    if np.isnan(mean_high) or np.isnan(mean_low):
        band_sep = float('nan')
    else:
        band_sep = float(np.clip(mean_high - mean_low, 0.0, 1.0))

    # stress test: rescore under simple macro shock and recompute Gini
    stressed = stress_rescore(df, sc)
    stressed_scores = stressed['risk_score'].to_numpy(dtype=float)
    auc_stress = auc_from_scores(stressed['delinquent'].astype(int).to_numpy() if 'delinquent' in stressed.columns else delinquent_mask(stressed, 30).astype(int).to_numpy(), stressed_scores)
    gini_stress = gini_from_auc(auc_stress) if not np.isnan(auc_stress) else float('nan')

    mcs = compute_model_confidence(brier, band_sep if not np.isnan(band_sep) else 0.0, gini, gini_stress)

    # per-band calibration table
    bands = ['Low', 'Medium', 'High']
    per_band = []
    for b in bands:
        sub = df[df.get('risk_grade') == b]
        n = int(len(sub))
        obs_rate = float(sub['delinquent'].mean()) if n > 0 else float('nan')
        avg_score = float(sub['risk_score'].mean()) if n > 0 else float('nan')
        per_band.append({'band': b, 'n': n, 'avg_score': avg_score, 'observed_delinquency_rate': obs_rate})

    report = {
        'confusion_matrix': cm,
        'precision_recall_f1': prf,
        'capture_rate_high_band': capture_rate,
        'gini': gini,
        'auc': auc,
        'ks': ks,
        'brier_score': brier,
        'per_band': per_band,
        'stress': {'gini_baseline': gini, 'gini_stress': gini_stress, 'auc_stress': auc_stress},
        'model_confidence': mcs,
        'notes': {
            'delinquency_proxy': 'dpd_current >= 30 days',
            'predicted_pd_from_score': 'min-max scale risk_score to [0,1] then invert (1 - scaled)',
            'gini_from_auc': 'gini = 2 * auc - 1, auc computed by rank-sum (Mann-Whitney)',
            'ks': 'empirical KS between score distributions of delinquent vs non-delinquent',
            'stress_scenario': 'sector_npl *= 1.5; dpd_current += 30; ltv_ratio += 0.05; then re-score using Scorecard',
            'model_confidence_components': 'calibration_quality, risk_band_separation, stress_test_stability (weights 0.4,0.3,0.3 respectively)',
        }
    }

    # write JSON
    out_json = outdir / 'validation_metrics.json'
    out_csv = outdir / 'validation_metrics.csv'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=lambda o: (None if pd.isna(o) else o))

    # write a flat CSV row summary and also per-band as separate rows
    flat = {
        'tp': cm['tp'], 'tn': cm['tn'], 'fp': cm['fp'], 'fn': cm['fn'],
        'precision': prf['precision'], 'recall': prf['recall'], 'f1': prf['f1'],
        'capture_rate_high_band': capture_rate,
        'gini': gini, 'auc': auc, 'ks': ks, 'brier_score': brier,
        'gini_stress': gini_stress, 'auc_stress': auc_stress,
        'model_confidence_score': mcs['model_confidence_score'],
    }
    # Save summary and append per-band rows
    rows = [flat]
    for pb in per_band:
        row = {**flat}
        row.update({'band': pb['band'], 'band_n': pb['n'], 'band_avg_score': pb['avg_score'], 'band_observed_delinquency_rate': pb['observed_delinquency_rate']})
        rows.append(row)

    pd.DataFrame(rows).to_csv(out_csv, index=False)

    print(f"Validation metrics written to: {out_json} and {out_csv}")


if __name__ == '__main__':
    main()
