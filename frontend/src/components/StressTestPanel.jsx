// StressTestPanel — override LTV / DPD / CRIB / app login and re-score.
// Owned by Member 4 with input from Member 5 (Integration & Stress Testing).

import React, { useEffect, useState } from 'react';
import api from '../services/api';
import InfoTip from './common/InfoTip';
import { safetyTierLabel } from '../constants/safetyScore';
import { METRIC_TOOLTIPS } from '../constants/tooltips';

const GRADE_COLOURS = {
  Low:    '#34a853',
  Medium: '#f9ab00',
  High:   '#ea4335',
};
const CHANGE_COLOURS = {
  Green:  { bg: '#e6f4ea', border: '#34a853', text: '#0d5a23' },
  Amber:  { bg: '#fef7e0', border: '#f9ab00', text: '#7a5300' },
  Red:    { bg: '#fce8e6', border: '#ea4335', text: '#c5221f' },
};
const CRIB_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'XX'];

function calcScoreChangePct(prevScore, newScore) {
  const prev = Number(prevScore);
  const next = Number(newScore);
  if (!prev || Number.isNaN(prev) || Number.isNaN(next)) return null;
  return ((next - prev) / prev) * 100;
}

function formatScoreChangePct(pct) {
  if (pct == null || Number.isNaN(pct)) return 'N/A';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
}

function getScoreChangeColour(pct) {
  if (pct == null || Number.isNaN(pct)) return CHANGE_COLOURS.Amber;
  if (pct >= 0) return CHANGE_COLOURS.Green;
  if (pct >= -15) return CHANGE_COLOURS.Amber;
  return CHANGE_COLOURS.Red;
}

export default function StressTestPanel({
  customerId,
  onBack,
  backLabel = 'Back to alerts',
}) {
  const [borrower, setBorrower] = useState(null);
  const [baseline, setBaseline] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([api.getBorrower(customerId), api.getRisk(customerId)])
      .then(([b, r]) => {
        setBorrower(b);
        setBaseline(r);
        setOverrides({
          ltv_ratio: b.ltv_ratio,
          dpd_current: b.dpd_current,
          crib_grade: b.crib_grade,
          app_login_freq: b.app_login_freq,
        });
      })
      .catch((e) => setError(e.message || 'Failed to load'));
  }, [customerId]);

  const updateOverride = (key, value) => {
    setOverrides({ ...overrides, [key]: value });
  };

  const runTest = async () => {
    setSubmitting(true);
    try {
      const res = await api.stressTest(customerId, overrides);
      setResult(res);
    } catch (e) {
      setError(e.message || 'Stress test failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (error) return <div style={styles.error}>Error: {error}</div>;
  if (!borrower || !baseline) return <div>Loading...</div>;

  return (
    <div>
      <button onClick={onBack} style={styles.backBtn}>
        &larr; {backLabel}
      </button>

      <div style={styles.wrap}>
        <h2 style={styles.h2}>Stress Test — {borrower.name}</h2>
        <p style={styles.sub}>
          Adjust the inputs below to simulate a risk event. Nothing is saved.
        </p>
        <p style={styles.howItWorks}>
          <strong>What is a stress test?</strong> A stress test simulates
          &ldquo;what-if&rdquo; scenarios. Adjust the sliders below to see how
          the borrower&apos;s safety score would change if their financial
          situation deteriorated — for example, if vehicle values dropped
          (higher LTV) or they missed payments (higher DPD). A higher score
          means lower risk. Nothing is saved
          to the database — this is a simulation only.
        </p>
        <div style={styles.controlsCard}>
        <div style={styles.grid}>
          <Field
            label={`LTV ratio: ${(overrides.ltv_ratio * 100).toFixed(0)}%`}
            tip={METRIC_TOOLTIPS.ltv}
          >
            <input
              type="range" min={0.1} max={1.0} step={0.01}
              value={overrides.ltv_ratio}
              onChange={(e) =>
                updateOverride('ltv_ratio', parseFloat(e.target.value))
              }
            />
          </Field>

          <Field
            label={`DPD (current): ${overrides.dpd_current} days`}
            tip={METRIC_TOOLTIPS.dpd}
          >
            <input
              type="range" min={0} max={90} step={1}
              value={overrides.dpd_current}
              onChange={(e) =>
                updateOverride('dpd_current', parseInt(e.target.value, 10))
              }
            />
          </Field>

          <Field
            label={`CRIB grade: ${overrides.crib_grade}`}
            tip={METRIC_TOOLTIPS.cribGrade}
          >
            <select
              value={overrides.crib_grade}
              onChange={(e) => updateOverride('crib_grade', e.target.value)}
            >
              {CRIB_OPTIONS.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </Field>

          <Field
            label={`App login frequency: ${overrides.app_login_freq}/month`}
            tip={METRIC_TOOLTIPS.appLogin}
          >
            <input
              type="range" min={0} max={30} step={1}
              value={overrides.app_login_freq}
              onChange={(e) =>
                updateOverride('app_login_freq', parseInt(e.target.value, 10))
              }
            />
          </Field>
        </div>
        </div>

        <button
          style={styles.runBtn}
          onClick={runTest}
          disabled={submitting}
        >
          {submitting ? 'Running...' : 'Run stress test'}
        </button>

        <div style={styles.compare}>
          <RiskPanel title="Before" risk={baseline} />
          {result && (
            <ScoreChangeBanner
              prevScore={baseline.risk_score}
              newScore={result.risk_score}
            />
          )}
          <RiskPanel title="After" risk={result} />
        </div>
      </div>
    </div>
  );
}

function Field({ label, tip, children }) {
  return (
    <label style={styles.field}>
      <span style={styles.fieldLabel}>
        {label}
        {tip && <InfoTip text={tip} />}
      </span>
      {children}
    </label>
  );
}

function ScoreChangeBanner({ prevScore, newScore }) {
  const pct = calcScoreChangePct(prevScore, newScore);
  const palette = getScoreChangeColour(pct);
  const delta = newScore - prevScore;

  return (
    <div
      style={{
        ...styles.changeBanner,
        background: palette.bg,
        borderColor: palette.border,
      }}
    >
      <div style={styles.changeLabel}>
        Safety Score Change
        <InfoTip text={METRIC_TOOLTIPS.scoreChange} />
      </div>
      <div style={{ ...styles.changeValue, color: palette.text }}>
        {formatScoreChangePct(pct)}
      </div>
      <div style={styles.changeDetail}>
        {prevScore} → {newScore}
        {delta !== 0 && (
          <span style={{ color: palette.border }}>
            {' '}
            ({delta > 0 ? '+' : ''}
            {delta} pts)
          </span>
        )}
      </div>
      <div style={{ ...styles.changeHint, color: palette.text }}>
        {pct == null
          ? 'Unable to calculate change'
          : pct >= 0
            ? 'Safety score held or improved'
            : pct >= -15
              ? 'Moderate drop in safety score'
              : 'Significant drop in safety score'}
      </div>
    </div>
  );
}

function RiskPanel({ title, risk }) {
  if (!risk) {
    return (
      <div style={styles.panel}>
        <h3 style={styles.h3}>{title}</h3>
        <div style={styles.placeholder}>Run a test to see the result</div>
      </div>
    );
  }
  const colour = GRADE_COLOURS[risk.risk_grade] || '#999';
  return (
    <div style={styles.panel}>
      <h3 style={styles.h3}>{title}</h3>
      <div style={{ ...styles.score, color: colour }}>
        {risk.risk_score}
      </div>
      <div style={{ ...styles.gradeBadge, background: colour }}>
        {safetyTierLabel(risk.risk_grade)} Safety
      </div>
      {risk.compliance_breach && (
        <div style={styles.breach}>
          BREACH: {risk.compliance_reason}
        </div>
      )}
      <div style={styles.action}>
        <strong>Action:</strong> {risk.recommended_action}
      </div>
    </div>
  );
}

const styles = {
  backBtn: {
    marginBottom: 12, padding: '6px 12px',
    background: 'transparent', border: '1px solid #aaa',
    borderRadius: 4, cursor: 'pointer',
  },
  wrap: {
    background: 'white', padding: 24, borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  h2: { margin: '0 0 8px 0', fontSize: 22 },
  sub: {
    marginTop: 0,
    marginBottom: 0,
    fontSize: 14,
    lineHeight: 1.5,
    color: '#444',
  },
  howItWorks: {
    margin: '14px 0 0',
    padding: '14px 16px',
    background: '#eef3fc',
    borderLeft: '4px solid #1a73e8',
    borderRadius: 4,
    fontSize: 14,
    lineHeight: 1.6,
    color: '#1a1a1a',
  },
  controlsCard: {
    marginTop: 20,
    padding: '18px 20px',
    background: '#ffffff',
    border: '1px solid #dadce0',
    borderRadius: 8,
    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
  },
  grid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: 16, marginTop: 16,
  },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  fieldLabel: {
    fontSize: 14,
    fontWeight: 600,
    color: '#1a1a1a',
    display: 'flex',
    alignItems: 'center',
  },
  runBtn: {
    marginTop: 20, padding: '10px 20px',
    background: '#1a73e8', color: 'white',
    border: 'none', borderRadius: 4,
    cursor: 'pointer', fontSize: 14,
  },
  compare: {
    display: 'grid',
    gridTemplateColumns: '1fr auto 1fr',
    gap: 16,
    marginTop: 24,
    alignItems: 'stretch',
  },
  changeBanner: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    alignItems: 'center',
    textAlign: 'center',
    padding: '16px 20px',
    borderRadius: 8,
    border: '2px solid',
    minWidth: 160,
  },
  changeLabel: {
    fontSize: 12,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: '#5f6368',
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  changeValue: {
    fontSize: 32,
    fontWeight: 700,
    lineHeight: 1.2,
    marginTop: 6,
  },
  changeDetail: {
    fontSize: 13,
    color: '#5f6368',
    marginTop: 6,
  },
  changeHint: {
    fontSize: 12,
    marginTop: 8,
    lineHeight: 1.4,
    maxWidth: 180,
  },
  panel: {
    background: '#f4f6f8',
    padding: '16px 16px 18px',
    borderRadius: 6,
  },
  h3: { margin: '0 0 12px 0' },
  score: { fontSize: 48, fontWeight: 700, lineHeight: 1 },
  gradeBadge: {
    display: 'inline-block', color: 'white',
    padding: '4px 12px', borderRadius: 4,
    fontSize: 12, fontWeight: 700, marginTop: 6,
  },
  breach: {
    background: '#a50e0e', color: 'white',
    padding: '6px 10px', borderRadius: 4,
    fontSize: 12, fontWeight: 600, marginTop: 8,
  },
  action: {
    marginTop: 12,
    fontSize: 13,
    lineHeight: 1.55,
    color: '#333',
  },
  placeholder: { opacity: 0.6, fontSize: 13 },
  error: { padding: 16, background: '#fce8e6', color: '#a50e0e' },
};
