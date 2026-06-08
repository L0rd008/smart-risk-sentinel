"""Validation summary (corrected orientation).

This script re-computes AUC/Gini/KS and related metrics using the correct
orientation for the system's SAFETY SCORE (higher = safer).

It produces:
- backend/reports/validation_metrics_corrected.json
- backend/reports/validation_metrics_corrected.csv

And includes a comparison to the original metrics file if present.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sys

# Resolve repo-relative paths
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parents[2]
OUTDIR = REPO_ROOT / 'backend' / 'reports'
OUTDIR.mkdir(parents=True, exist_ok=True)

# Make backend importable
BACKEND_DIR = THIS_FILE.parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.scoring.scorecard import Scorecard  # type: ignore

def find_existing_backtest() -> Path | None:
    candidates = [
        REPO_ROOT / 'backend' / 'reports' / 'backtest_full.json',
        REPO_ROOT / 'backend' / 'outputs' / 'backtest_full.json',
        REPO_ROOT / 'backtest_full.json',
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_backtest() -> pd.DataFrame:
    p = find_existing_backtest()
    if p is None:
        raise FileNotFoundError('No backtest JSON found')
    data = json.loads(p.read_text(encoding='utf-8'))
    return pd.DataFrame(data)


def delinquent_mask(df: pd.DataFrame, days: int = 30) -> pd.Series:
    return df.get('dpd_current', pd.Series(0)).fillna(0).astype(int) >= days


def binary_confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, int]:
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    return {'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn}


def precision_recall_f1(tp: int, fp: int, fn: int) -> dict[str, float]:
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return {'precision': prec, 'recall': rec, 'f1': f1}


def auc_from_scores(y_true: np.ndarray, scores: np.ndarray) -> float:
    # AUC via rank-sum (Mann-Whitney U). Assumes higher score => more likely positive.
    y_true = np.asarray(y_true)
    scores = np.asarray(scores)
    n = len(scores)
    if n == 0:
        return float('nan')
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, n + 1)
    pos = (y_true == 1)
    n_pos = int(pos.sum())
    n_neg = int((~pos).sum())
    if n_pos == 0 or n_neg == 0:
        return float('nan')
    pos_ranks_sum = ranks[pos].sum()
    auc = (pos_ranks_sum - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return float(auc)


def gini_from_auc(auc: float) -> float:
    if np.isnan(auc):
        return float('nan')
    return 2 * auc - 1


def ks_statistic(y_true: np.ndarray, scores: np.ndarray) -> float:
    pos_scores = np.sort(scores[y_true == 1])
    neg_scores = np.sort(scores[y_true == 0])
    if len(pos_scores) == 0 or len(neg_scores) == 0:
        return float('nan')
    all_scores = np.sort(np.unique(scores))
    cdf_pos = np.searchsorted(pos_scores, all_scores, side='right') / len(pos_scores)
    cdf_neg = np.searchsorted(neg_scores, all_scores, side='right') / len(neg_scores)
    return float(np.max(np.abs(cdf_pos - cdf_neg)))


def predicted_pd_from_score(scores: np.ndarray, invert: bool = True) -> np.ndarray:
    # Map safety score (higher=safer) to PD in [0,1]. If invert=True, higher safety -> lower PD.
    s = np.asarray(scores, dtype=float)
    s_min = np.nanmin(s)
    s_max = np.nanmax(s)
    if s_max == s_min:
        return np.full_like(s, 0.5, dtype=float)
    scaled = (s - s_min) / (s_max - s_min)
    if invert:
        return 1.0 - scaled
    return scaled


def compute_metrics(df: pd.DataFrame, use_inverted_for_auc: bool) -> dict[str, Any]:
    df = df.copy()
    df['delinquent'] = delinquent_mask(df, 30)
    y_true = df['delinquent'].astype(int).to_numpy()

    # scores as numeric
    scores = df['risk_score'].to_numpy(dtype=float)

    # For AUC we must ensure higher -> higher default propensity. For a safety score (higher=safe),
    # we invert the score by taking -scores or by using predicted PD mapping as 1 - scaled.
    if use_inverted_for_auc:
        # Use -scores so larger value corresponds to higher default propensity
        auc_scores = -scores
    else:
        auc_scores = scores

    auc = auc_from_scores(y_true, auc_scores)
    gini = gini_from_auc(auc) if not np.isnan(auc) else float('nan')
    ks = ks_statistic(y_true, auc_scores)

    # Binary predictions: use High band (unchanged)
    y_pred = (df.get('risk_grade', '') == 'High').astype(int).to_numpy()
    cm = binary_confusion(y_true, y_pred)
    prf = precision_recall_f1(cm['tp'], cm['fp'], cm['fn'])
    total_delinq = int(y_true.sum())
    captured = int(((y_true == 1) & (y_pred == 1)).sum())
    capture_rate = float(captured / total_delinq) if total_delinq > 0 else float('nan')

    # calibration via Brier with predicted PD derived from score (invert=True maps high safety -> low PD)
    pred_pd = predicted_pd_from_score(scores, invert=True)
    brier = float(np.mean((pred_pd - y_true) ** 2))

    return {
        'auc': auc,
        'gini': gini,
        'ks': ks,
        'confusion_matrix': cm,
        'precision_recall_f1': prf,
        'capture_rate_high_band': capture_rate,
        'brier_score': brier,
    }


def load_original_metrics() -> dict[str, Any] | None:
    p = OUTDIR / 'validation_metrics.json'
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None


def compute_model_confidence(brier: float, band_sep: float, gini_base: float, gini_stress: float) -> dict[str, Any]:
    calibration_quality = max(0.0, 1.0 - float(brier))
    separation = float(np.clip(band_sep, 0.0, 1.0))
    stability = float(max(0.0, 1.0 - abs(float(gini_base) - float(gini_stress)))) if not np.isnan(gini_base) and not np.isnan(gini_stress) else float('nan')
    w_cal, w_sep, w_stab = 0.4, 0.3, 0.3
    comps = [calibration_quality, separation, stability if not np.isnan(stability) else 0.0]
    mcs = float(np.nansum([w_cal * comps[0], w_sep * comps[1], w_stab * comps[2]]))
    mcs = float(np.clip(mcs, 0.0, 1.0))
    return {
        'calibration_quality': calibration_quality,
        'risk_band_separation': separation,
        'stress_test_stability': stability,
        'model_confidence_score': mcs,
        'weights': {'calibration': w_cal, 'separation': w_sep, 'stability': w_stab},
    }


def main() -> None:
    df = load_backtest()

    # Original metrics in the prior script used 'scores as-is' which for a SAFETY score produced inverted AUC.
    orig = load_original_metrics()

    # Compute with original orientation (scores as numeric) and corrected orientation (inverted for AUC)
    metrics_original_orientation = compute_metrics(df, use_inverted_for_auc=False)
    metrics_corrected_orientation = compute_metrics(df, use_inverted_for_auc=True)

    # compute band separation and stress stability for corrected orientation
    # band separation: mean PD(High) - mean PD(Low)
    scores = df['risk_score'].to_numpy(dtype=float)
    pred_pd = predicted_pd_from_score(scores, invert=True)
    df['pred_pd'] = pred_pd
    band_means = df.groupby('risk_grade')['pred_pd'].mean().to_dict()
    mean_high = band_means.get('High', float('nan'))
    mean_low = band_means.get('Low', float('nan'))
    band_sep = float(mean_high - mean_low) if (not np.isnan(mean_high) and not np.isnan(mean_low)) else float('nan')

    # Stress scenario: apply macro shock and re-score using the real Scorecard.calculate()
    sc = Scorecard()
    stressed_recs: list[dict] = []
    for _, row in df.iterrows():
        rec = row.to_dict()
        # apply transparent stress shock
        try:
            rec['sector_npl'] = float(rec.get('sector_npl', 0.0) or 0.0) * 1.5
        except Exception:
            rec['sector_npl'] = rec.get('sector_npl', 0.0)
        try:
            # smaller uplift to keep some records non-delinquent under stress
            rec['dpd_current'] = int(rec.get('dpd_current', 0) or 0) + 15
        except Exception:
            rec['dpd_current'] = rec.get('dpd_current', 0)
        try:
            rec['ltv_ratio'] = float(rec.get('ltv_ratio', 0.0) or 0.0) + 0.05
        except Exception:
            rec['ltv_ratio'] = rec.get('ltv_ratio', 0.0)

        # ensure customer_id exists
        if 'customer_id' not in rec:
            rec['customer_id'] = 'sim-unknown'

        # re-score using Scorecard
        try:
            r = sc.calculate(rec)
        except Exception:
            # fallback: keep original risk_score if scoring fails
            r = {'risk_score': rec.get('risk_score', np.nan), 'risk_grade': rec.get('risk_grade', None)}
        merged = {**rec, **r}
        stressed_recs.append(merged)

    stressed_df = pd.DataFrame(stressed_recs)
    stressed_scores = stressed_df['risk_score'].to_numpy(dtype=float)
    y_true_stressed = delinquent_mask(stressed_df, 30).astype(int).to_numpy()
    # compute AUC/Gini using inverted orientation (safety -> default)
    auc_stress = auc_from_scores(y_true_stressed, -stressed_scores)
    gini_stress = gini_from_auc(auc_stress) if not np.isnan(auc_stress) else float('nan')

    # compute model confidence using corrected orientation values
    mcs = compute_model_confidence(metrics_corrected_orientation['brier_score'], band_sep if not np.isnan(band_sep) else 0.0, metrics_corrected_orientation['gini'], gini_stress)

    report = {
        'original_metrics_file': str(OUTDIR / 'validation_metrics.json') if orig is not None else None,
        'original_report_snapshot': orig,
        'metrics_original_orientation': metrics_original_orientation,
        'metrics_corrected_orientation': metrics_corrected_orientation,
        'band_separation': {'mean_high_pred_pd': mean_high, 'mean_low_pred_pd': mean_low, 'band_separation': band_sep},
        'stress': {'gini_stress_proxy': gini_stress, 'auc_stress_proxy': auc_stress},
        'model_confidence_corrected': mcs,
        'notes': {
            'safety_score_interpretation': 'score near 1000 = very safe (low default risk); near 0 = very risky',
            'correction': 'AUC and Gini must be computed on a variable where larger values indicate higher default propensity; for a safety score this requires inversion (e.g. -risk_score or 1 - scaled_score)'
        }
    }

    out_json = OUTDIR / 'validation_metrics_corrected.json'
    out_csv = OUTDIR / 'validation_metrics_corrected.csv'
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, default=lambda o: (None if pd.isna(o) else o))

    # Flatten and save CSV: original vs corrected key numbers
    flat = {
        'orig_auc': metrics_original_orientation['auc'],
        'orig_gini': metrics_original_orientation['gini'],
        'orig_ks': metrics_original_orientation['ks'],
        'orig_precision': metrics_original_orientation['precision_recall_f1']['precision'],
        'orig_recall': metrics_original_orientation['precision_recall_f1']['recall'],
        'orig_f1': metrics_original_orientation['precision_recall_f1']['f1'],
        'orig_capture_rate': metrics_original_orientation['capture_rate_high_band'],
        'corr_auc': metrics_corrected_orientation['auc'],
        'corr_gini': metrics_corrected_orientation['gini'],
        'corr_ks': metrics_corrected_orientation['ks'],
        'corr_precision': metrics_corrected_orientation['precision_recall_f1']['precision'],
        'corr_recall': metrics_corrected_orientation['precision_recall_f1']['recall'],
        'corr_f1': metrics_corrected_orientation['precision_recall_f1']['f1'],
        'corr_capture_rate': metrics_corrected_orientation['capture_rate_high_band'],
        'model_confidence_corrected': mcs['model_confidence_score'],
    }
    pd.DataFrame([flat]).to_csv(out_csv, index=False)

    print('Corrected metrics written to:', out_json, out_csv)


if __name__ == '__main__':
    main()
