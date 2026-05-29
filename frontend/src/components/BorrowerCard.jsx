// BorrowerCard — colour-coded card showing one borrower's risk profile.
// Owned by Member 4.

import React, { useEffect, useState } from 'react';
import api from '../services/api';

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
        ['Monthly Income', formatLkr(borrower.monthly_income)],
        ['Monthly Obligations', formatLkr(borrower.monthly_obligations)],
        [
          'DTI Ratio',
          formatDti(borrower.monthly_income, borrower.monthly_obligations),
        ],
      ],
    },
    {
      name: 'Character',
      weight: '30%',
      rows: [
        ['CRIB Grade', borrower.crib_grade ?? 'N/A'],
        ['Days Past Due (Current)', borrower.dpd_current ?? 'N/A'],
        ['DPD History (6 months)', formatDpdPattern(borrower.dpd_pattern)],
        ['App Logins/Month', borrower.app_login_freq ?? 'N/A'],
      ],
    },
    {
      name: 'Collateral',
      weight: '20%',
      rows: [
        ['Vehicle Type', borrower.vehicle_type ?? 'N/A'],
        ['Vehicle Value', formatLkr(borrower.vehicle_value)],
        ['Loan Amount', formatLkr(borrower.loan_amount)],
        ['LTV Ratio', formatPct(borrower.ltv_ratio)],
      ],
    },
    {
      name: 'Conditions',
      weight: '10%',
      rows: [
        ['Sector', borrower.sector_code ?? 'N/A'],
        ['Sector NPL', formatSectorNpl(borrower.sector_npl)],
      ],
    },
    {
      name: 'Capital',
      weight: '5%',
      rows: [
        [
          'Net Worth',
          borrower.net_worth != null
            ? formatLkr(borrower.net_worth)
            : 'N/A',
        ],
      ],
    },
  ];
}

function BorrowerProfile({ borrower }) {
  const categories = buildProfileCategories(borrower);

  return (
    <section style={styles.section}>
      <h3 style={styles.h3}>Borrower Profile</h3>
      <div style={styles.profileGrid}>
        {categories.map((cat) => (
          <div key={cat.name} style={styles.profileCard}>
            <div style={styles.profileCardHeader}>
              {cat.name} ({cat.weight})
            </div>
            <dl style={styles.profileDl}>
              {cat.rows.map(([label, value]) => (
                <div key={label} style={styles.profileRow}>
                  <dt style={styles.profileLabel}>{label}</dt>
                  <dd style={styles.profileValue}>{value}</dd>
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
      <button onClick={onBack} style={styles.backBtn}>
        &larr; Back to alerts
      </button>

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
              {borrower.sector_code} · {borrower.vehicle_type} ·{' '}
              CRIB {borrower.crib_grade}
            </div>
          </div>
          <div style={styles.scoreBlock}>
            <div style={{ ...styles.scoreNumber, color: palette.border }}>
              {risk.risk_score}
            </div>
            <div
              style={{
                ...styles.gradeBadge,
                background: palette.border,
                color: '#fff',
              }}
            >
              {risk.risk_grade}
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
          <h3 style={styles.h3}>Early Warning Indicators</h3>
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
          <p style={styles.actionText}>{risk.recommended_action}</p>
        </section>

        <button style={styles.stressBtn} onClick={onStressTest}>
          Run stress test &rarr;
        </button>
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
  card: {
    borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
    overflow: 'hidden',
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
  scoreBlock: { textAlign: 'right' },
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
  profileGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 12,
  },
  profileCard: {
    background: '#f8f9fa',
    border: `1px solid ${NEUTRAL.border}`,
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
