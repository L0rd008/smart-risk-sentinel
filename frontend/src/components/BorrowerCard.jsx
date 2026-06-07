// BorrowerCard — colour-coded card showing one borrower's risk profile.
// Owned by Member 4.

import React, { useEffect, useState } from 'react';
import api from '../services/api';
import InfoTip from './common/InfoTip';
import ScoreLegend from './common/ScoreLegend';
import { safetyTierLabel } from '../constants/safetyScore';
import { METRIC_TOOLTIPS } from '../constants/tooltips';

const COLOURS = {
  Green:  { bg: '#e6f4ea', border: '#34a853', badge: '#0d5a23' },
  Amber:  { bg: '#fef7e0', border: '#f9ab00', badge: '#7a5300' },
  Red:    { bg: '#fce8e6', border: '#ea4335', badge: '#c5221f' },
};

const NEUTRAL = {
  text: '#1a1a1a',
  muted: '#5f6368',
  border: '#e8eaed',
  surface: '#ffffff',
};

function formatLkr(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A';
  return `LKR ${Number(value).toLocaleString()}`;
}

function formatDti(income, obligations) {
  const inc = Number(income);
  if (!inc) return 'N/A';
  return `${((Number(obligations) / inc) * 100).toFixed(1)}%`;
}

function formatPct(ratio) {
  if (ratio == null || Number.isNaN(Number(ratio))) return 'N/A';
  return `${(Number(ratio) * 100).toFixed(1)}%`;
}

function formatSectorNpl(npl) {
  if (npl == null || npl === '') return 'N/A';
  const num = Number(npl);
  if (Number.isNaN(num)) return 'N/A';
  const pct = num <= 1 ? num * 100 : num;
  return `${pct.toFixed(1)}%`;
}

function formatDpdPattern(pattern) {
  if (!pattern?.length) return 'N/A';
  return pattern.join(' → ');
}

function buildProfileCategories(borrower) {
  return [
    {
      name: 'Capacity',
      weight: '35%',
      rows: [
        { label: 'Monthly Income', value: formatLkr(borrower.monthly_income) },
        {
          label: 'Monthly Obligations',
          value: formatLkr(borrower.monthly_obligations),
        },
        {
          label: 'DTI Ratio',
          value: formatDti(borrower.monthly_income, borrower.monthly_obligations),
          tip: METRIC_TOOLTIPS.dti,
        },
      ],
    },
    {
      name: 'Character',
      weight: '30%',
      rows: [
        {
          label: 'CRIB Grade',
          value: borrower.crib_grade ?? 'N/A',
          tip: METRIC_TOOLTIPS.cribGrade,
        },
        {
          label: 'Days Past Due (Current)',
          value: borrower.dpd_current ?? 'N/A',
          tip: METRIC_TOOLTIPS.dpd,
        },
        {
          label: 'DPD History (6 months)',
          value: formatDpdPattern(borrower.dpd_pattern),
        },
        {
          label: 'App Logins/Month',
          value: borrower.app_login_freq ?? 'N/A',
          tip: METRIC_TOOLTIPS.appLogin,
        },
      ],
    },
    {
      name: 'Collateral',
      weight: '20%',
      rows: [
        { label: 'Vehicle Type', value: borrower.vehicle_type ?? 'N/A' },
        { label: 'Vehicle Value', value: formatLkr(borrower.vehicle_value) },
        { label: 'Loan Amount', value: formatLkr(borrower.loan_amount) },
        {
          label: 'LTV Ratio',
          value: formatPct(borrower.ltv_ratio),
          tip: METRIC_TOOLTIPS.ltv,
        },
      ],
    },
    {
      name: 'Conditions',
      weight: '10%',
      rows: [
        { label: 'Sector', value: borrower.sector_code ?? 'N/A' },
        {
          label: 'Sector NPL',
          value: formatSectorNpl(borrower.sector_npl),
          tip: METRIC_TOOLTIPS.sectorNpl,
        },
      ],
    },
    {
      name: 'Capital',
      weight: '5%',
      rows: [
        {
          label: 'Net Worth',
          value:
            borrower.net_worth != null
              ? formatLkr(borrower.net_worth)
              : 'N/A',
          tip: METRIC_TOOLTIPS.netWorth,
        },
      ],
    },
  ];
}

function MetricLabel({ label, tip }) {
  return (
    <>
      {label}
      {tip && <InfoTip text={tip} />}
    </>
  );
}

function BorrowerProfile({ borrower }) {
  const categories = buildProfileCategories(borrower);

  return (
    <section style={styles.section}>
      <h3 style={styles.h3}>
        Borrower Profile
        <InfoTip text={METRIC_TOOLTIPS.fiveCs} />
      </h3>
      <div style={styles.profileGrid}>
        {categories.map((cat) => (
          <div key={cat.name} style={styles.profileCard}>
            <div style={styles.profileCardHeader}>
              {cat.name} ({cat.weight})
            </div>
            <dl style={styles.profileDl}>
              {cat.rows.map((row) => (
                <div key={row.label} style={styles.profileRow}>
                  <dt style={styles.profileLabel}>
                    <MetricLabel label={row.label} tip={row.tip} />
                  </dt>
                  <dd style={styles.profileValue}>{row.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function BorrowerCard({ customerId, onStressTest, onBack }) {
  const [borrower, setBorrower] = useState(null);
  const [risk, setRisk] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([api.getBorrower(customerId), api.getRisk(customerId)])
      .then(([b, r]) => {
        setBorrower(b);
        setRisk(r);
      })
      .catch((e) => setError(e.message || 'Failed to load'));
  }, [customerId]);

  if (error) return <div style={styles.error}>Error: {error}</div>;
  if (!borrower || !risk) return <div>Loading borrower {customerId}...</div>;

  const palette = COLOURS[risk.risk_colour] || COLOURS.Amber;

  return (
    <div>
      <div style={styles.topRow}>
        <button onClick={onBack} style={styles.backBtn}>
          &larr; Back to alerts
        </button>
        <div style={styles.topRightControls}>
          <button style={styles.stressBtnHeader} onClick={onStressTest}>
            Run stress test
          </button>
        </div>
      </div>

      <div
        style={{
          ...styles.card,
          background: NEUTRAL.surface,
          borderLeft: `8px solid ${palette.border}`,
          color: NEUTRAL.text,
        }}
      >
        <header
          style={{
            ...styles.cardHeader,
            background: palette.bg,
            borderBottom: `1px solid ${NEUTRAL.border}`,
          }}
        >
          <div>
            <h2 style={styles.name}>{borrower.name}</h2>
            <div style={styles.meta}>
              {borrower.province} · {borrower.sector_code} · {borrower.vehicle_type}{' '}
              · CRIB {borrower.crib_grade}
            </div>
          </div>
          <div style={styles.scoreBlock}>
            <div style={styles.scoreLabel}>
              Safety Score
              <InfoTip text={METRIC_TOOLTIPS.safetyScore} />
            </div>
            <div style={{ ...styles.scoreNumber, color: palette.border }}>
              {risk.risk_score}
            </div>
            <ScoreLegend />
            <div
              style={{
                ...styles.gradeBadge,
                background: palette.border,
                color: '#fff',
              }}
            >
              {safetyTierLabel(risk.risk_grade)} Safety
            </div>
          </div>
        </header>

        <div style={styles.cardBody}>

        {risk.compliance_breach && (
          <div style={styles.breach}>
            REGULATORY BREACH: {risk.compliance_reason}
          </div>
        )}

        <BorrowerProfile borrower={borrower} />

        <section style={styles.section}>
          <h3 style={styles.h3}>Top Risk Drivers</h3>
          <ul style={styles.list}>
            {risk.top_risk_drivers.map((d, i) => (
              <li key={i}>
                <strong>{d.factor}</strong> ({d.impact}) — {d.detail}
              </li>
            ))}
          </ul>
        </section>

        <section style={styles.section}>
          <h3 style={styles.h3}>
            Early Warning Indicators
            <InfoTip text={METRIC_TOOLTIPS.ewi} />
          </h3>
          <div style={styles.ewiGrid}>
            {risk.ewi_flags.map((f, i) => (
              <div
                key={i}
                style={{
                  ...styles.ewi,
                  borderColor: COLOURS[f.status].border,
                }}
              >
                <div style={styles.ewiLabel}>{f.indicator}</div>
                <div style={styles.ewiValue}>{f.value}</div>
                <div
                  style={{
                    ...styles.ewiStatus,
                    color: COLOURS[f.status].border,
                  }}
                >
                  {f.status}
                </div>
              </div>
            ))}
          </div>
        </section>

        <section style={styles.section}>
  <h3 style={styles.h3}>Recommended Action</h3>

  <div style={styles.actionBox}>
    <p style={styles.actionText}>
      {risk.recommended_action}
    </p>
  </div>
</section>

        </div>
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
  topRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  topRightControls: { display: 'flex', gap: 8 },
  stressBtnHeader: {
    padding: '6px 12px',
    background: '#1a73e8',
    color: 'white',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
  },
  card: {
    borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    overflow: 'visible',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '20px 24px',
  },
  cardBody: { padding: '20px 24px 24px' },
  name: { margin: 0, fontSize: 24, color: NEUTRAL.text },
  meta: { fontSize: 13, color: NEUTRAL.muted, marginTop: 4 },
  scoreBlock: {
    textAlign: 'right',
    minWidth: 220,
    flexShrink: 0,
  },
  scoreLabel: {
    fontSize: 12,
    color: NEUTRAL.muted,
    marginBottom: 4,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
  },
  scoreNumber: { fontSize: 42, fontWeight: 700, lineHeight: 1 },
  gradeBadge: {
    display: 'inline-block',
    marginTop: 6,
    padding: '4px 10px',
    borderRadius: 4,
    fontSize: 12,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  breach: {
    background: '#a50e0e', color: 'white', padding: '8px 12px',
    borderRadius: 4, fontWeight: 600, marginBottom: 16,
  },
  section: { marginTop: 20 },
  h3: {
    margin: '0 0 10px 0',
    fontSize: 12,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    color: NEUTRAL.muted,
  },
  actionBox: {
    background: '#e8edf6',
    borderLeft: '5px solid #1a73e8',
    borderRadius: 4,
    padding: '14px 18px',
  },
  actionText: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.7,
    color: NEUTRAL.text,
  },
  profileGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 12,
  },
  profileCard: {
    background: '#f8f9fa',
    border: '1px solid #1a73e8',
    borderRadius: 6,
    padding: 12,
  },
  profileCardHeader: {
    fontSize: 12,
    fontWeight: 700,
    marginBottom: 8,
    paddingBottom: 6,
    borderBottom: `1px solid ${NEUTRAL.border}`,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    color: NEUTRAL.text,
  },
  actionText: {
    margin: 0,
    fontSize: 14,
    lineHeight: 1.5,
    color: NEUTRAL.text,
  },
  profileDl: { margin: 0 },
  profileRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    fontSize: 13,
    padding: '5px 0',
    borderBottom: `1px solid ${NEUTRAL.border}`,
  },
  profileLabel: { margin: 0, color: NEUTRAL.muted, flex: 1 },
  profileValue: {
    margin: 0,
    fontWeight: 600,
    color: NEUTRAL.text,
    textAlign: 'right',
    flexShrink: 0,
  },
  list: { margin: 0, paddingLeft: 20, color: NEUTRAL.text, lineHeight: 1.6 },
  ewiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 8,
  },
  ewi: {
    background: NEUTRAL.surface,
    border: '2px solid',
    borderRadius: 6,
    padding: 10,
  },
  ewiLabel: { fontSize: 12, color: NEUTRAL.muted },
  ewiValue: {
    fontSize: 16,
    fontWeight: 600,
    marginTop: 2,
    color: NEUTRAL.text,
  },
  ewiStatus: { fontSize: 12, fontWeight: 700, marginTop: 4 },
  stressBtn: {
    marginTop: 20, padding: '8px 16px',
    background: '#1a73e8', color: 'white',
    border: 'none', borderRadius: 4, cursor: 'pointer',
  },
  error: { padding: 16, background: '#fce8e6', color: '#a50e0e' },
};
