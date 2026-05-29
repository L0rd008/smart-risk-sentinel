// StressTestPanel — override LTV / DPD / CRIB / app login and re-score.
// Owned by Member 4 with input from Member 5 (Integration & Stress Testing).

import React, { useEffect, useState } from 'react';
import api from '../services/api';

const GRADE_COLOURS = {
  Low:    '#34a853',
  Medium: '#f9ab00',
  High:   '#ea4335',
};
const CRIB_OPTIONS = ['A', 'B', 'C', 'D', 'E', 'XX'];

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

        <div style={styles.grid}>
          <Field label={`LTV ratio: ${(overrides.ltv_ratio * 100).toFixed(0)}%`}>
            <input
              type="range" min={0.1} max={1.0} step={0.01}
              value={overrides.ltv_ratio}
              onChange={(e) =>
                updateOverride('ltv_ratio', parseFloat(e.target.value))
              }
            />
          </Field>

          <Field label={`DPD (current): ${overrides.dpd_current} days`}>
            <input
              type="range" min={0} max={90} step={1}
              value={overrides.dpd_current}
              onChange={(e) =>
                updateOverride('dpd_current', parseInt(e.target.value, 10))
              }
            />
          </Field>

          <Field label={`CRIB grade: ${overrides.crib_grade}`}>
            <select
              value={overrides.crib_grade}
              onChange={(e) => updateOverride('crib_grade', e.target.value)}
            >
              {CRIB_OPTIONS.map((g) => (
                <option key={g} value={g}>{g}</option>
              ))}
            </select>
          </Field>

          <Field label={`App login frequency: ${overrides.app_login_freq}/month`}>
            <input
              type="range" min={0} max={30} step={1}
              value={overrides.app_login_freq}
              onChange={(e) =>
                updateOverride('app_login_freq', parseInt(e.target.value, 10))
              }
            />
          </Field>
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
          <RiskPanel title="After" risk={result} />
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label style={styles.field}>
      <span style={styles.fieldLabel}>{label}</span>
      {children}
    </label>
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
        {risk.risk_grade}
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
  h2: { margin: '0 0 4px 0' },
  sub: { marginTop: 0, opacity: 0.7, fontSize: 13 },
  grid: {
    display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: 16, marginTop: 16,
  },
  field: { display: 'flex', flexDirection: 'column', gap: 4 },
  fieldLabel: { fontSize: 13, fontWeight: 600 },
  runBtn: {
    marginTop: 20, padding: '10px 20px',
    background: '#1a73e8', color: 'white',
    border: 'none', borderRadius: 4,
    cursor: 'pointer', fontSize: 14,
  },
  compare: {
    display: 'grid', gridTemplateColumns: '1fr 1fr',
    gap: 16, marginTop: 24,
  },
  panel: {
    background: '#f4f6f8', padding: 16, borderRadius: 6,
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
  action: { marginTop: 12, fontSize: 13 },
  placeholder: { opacity: 0.6, fontSize: 13 },
  error: { padding: 16, background: '#fce8e6', color: '#a50e0e' },
};
