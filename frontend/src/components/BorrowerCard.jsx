// BorrowerCard — colour-coded card showing one borrower's risk profile.
// Owned by Member 4.

import React, { useEffect, useState } from 'react';
import api from '../services/api';

const COLOURS = {
  Green:  { bg: '#e6f4ea', border: '#34a853', text: '#0d5a23' },
  Amber:  { bg: '#fef7e0', border: '#f9ab00', text: '#7a5300' },
  Red:    { bg: '#fce8e6', border: '#ea4335', text: '#a50e0e' },
};

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
        &larr; Back to dashboard
      </button>

      <div
        style={{
          ...styles.card,
          background: palette.bg,
          borderLeft: `8px solid ${palette.border}`,
          color: palette.text,
        }}
      >
        <header style={styles.cardHeader}>
          <div>
            <h2 style={styles.name}>{borrower.name}</h2>
            <div style={styles.meta}>
              {borrower.sector_code} · {borrower.vehicle_type} ·{' '}
              CRIB {borrower.crib_grade}
            </div>
          </div>
          <div style={styles.scoreBlock}>
            <div style={styles.scoreNumber}>{risk.risk_score}</div>
            <div style={styles.grade}>{risk.risk_grade}</div>
          </div>
        </header>

        {risk.compliance_breach && (
          <div style={styles.breach}>
            REGULATORY BREACH: {risk.compliance_reason}
          </div>
        )}

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
          <p>{risk.recommended_action}</p>
        </section>

        <button style={styles.stressBtn} onClick={onStressTest}>
          Run stress test &rarr;
        </button>
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
    padding: 24, borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
  },
  cardHeader: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'flex-start', marginBottom: 16,
  },
  name: { margin: 0, fontSize: 24 },
  meta: { fontSize: 13, opacity: 0.8, marginTop: 4 },
  scoreBlock: { textAlign: 'right' },
  scoreNumber: { fontSize: 42, fontWeight: 700, lineHeight: 1 },
  grade: { fontSize: 14, textTransform: 'uppercase', letterSpacing: 1 },
  breach: {
    background: '#a50e0e', color: 'white', padding: '8px 12px',
    borderRadius: 4, fontWeight: 600, marginBottom: 16,
  },
  section: { marginTop: 16 },
  h3: { margin: '0 0 8px 0', fontSize: 14, textTransform: 'uppercase' },
  list: { margin: 0, paddingLeft: 20 },
  ewiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 8,
  },
  ewi: {
    background: 'rgba(255,255,255,0.7)',
    border: '2px solid', borderRadius: 6, padding: 10,
  },
  ewiLabel: { fontSize: 12, opacity: 0.7 },
  ewiValue: { fontSize: 16, fontWeight: 600, marginTop: 2 },
  ewiStatus: { fontSize: 12, fontWeight: 700, marginTop: 4 },
  stressBtn: {
    marginTop: 20, padding: '8px 16px',
    background: '#1a73e8', color: 'white',
    border: 'none', borderRadius: 4, cursor: 'pointer',
  },
  error: { padding: 16, background: '#fce8e6', color: '#a50e0e' },
};
