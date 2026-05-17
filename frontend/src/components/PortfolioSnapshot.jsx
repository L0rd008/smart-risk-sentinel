// PortfolioSnapshot — doughnut + sector table for the dashboard landing view.
// Owned by Member 4.

import React, { useEffect, useState } from 'react';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import { Doughnut } from 'react-chartjs-2';
import api from '../services/api';

ChartJS.register(ArcElement, Tooltip, Legend);

const GRADE_COLOURS = {
  Low:    '#34a853',
  Medium: '#f9ab00',
  High:   '#ea4335',
};

export default function PortfolioSnapshot() {
  const [snapshot, setSnapshot] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .getPortfolioSnapshot()
      .then(setSnapshot)
      .catch((e) => setError(e.message || 'Failed to load snapshot'));
  }, []);

  if (error) return <div style={styles.error}>Error: {error}</div>;
  if (!snapshot) return <div>Loading portfolio snapshot...</div>;

  const grades = snapshot.by_grade || { Low: 0, Medium: 0, High: 0 };
  const doughnutData = {
    labels: Object.keys(grades),
    datasets: [
      {
        data: Object.values(grades),
        backgroundColor: Object.keys(grades).map((g) => GRADE_COLOURS[g]),
        borderWidth: 2,
        borderColor: '#fff',
      },
    ],
  };

  return (
    <div style={styles.wrap}>
      <div style={styles.left}>
        <h2 style={styles.h2}>Portfolio Snapshot</h2>
        <div style={styles.metrics}>
          <Metric label="Borrowers" value={snapshot.total_borrowers} />
          <Metric label="Avg Score" value={snapshot.avg_portfolio_score} />
          <Metric
            label="Compliance Breaches"
            value={snapshot.compliance_breaches}
            highlight={snapshot.compliance_breaches > 0}
          />
        </div>
        <div style={styles.chartBox}>
          <Doughnut data={doughnutData} />
        </div>
      </div>

      <div style={styles.right}>
        <h3 style={styles.h3}>By Sector</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Sector</th>
              <th style={styles.th}>Count</th>
              <th style={styles.th}>Avg Score</th>
            </tr>
          </thead>
          <tbody>
            {(snapshot.by_sector || []).map((s) => (
              <tr key={s.sector}>
                <td style={styles.td}>{s.sector}</td>
                <td style={styles.td}>{s.count}</td>
                <td style={styles.td}>{s.avg_score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Metric({ label, value, highlight }) {
  return (
    <div style={styles.metric}>
      <div style={styles.metricLabel}>{label}</div>
      <div
        style={{
          ...styles.metricValue,
          color: highlight ? '#ea4335' : '#1a1a1a',
        }}
      >
        {value}
      </div>
    </div>
  );
}

const styles = {
  wrap: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 24,
    background: 'white',
    padding: 24,
    borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    marginBottom: 24,
  },
  left: {},
  right: {},
  h2: { margin: '0 0 12px 0' },
  h3: { margin: '0 0 12px 0', fontSize: 16 },
  metrics: { display: 'flex', gap: 16, marginBottom: 16 },
  metric: { background: '#f4f6f8', padding: 12, borderRadius: 6, flex: 1 },
  metricLabel: { fontSize: 12, opacity: 0.7 },
  metricValue: { fontSize: 22, fontWeight: 700, marginTop: 4 },
  chartBox: { maxWidth: 320 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '6px 8px', borderBottom: '2px solid #ddd', fontSize: 12 },
  td: { padding: '6px 8px', borderBottom: '1px solid #eee', fontSize: 13 },
  error: { padding: 16, background: '#fce8e6', color: '#a50e0e' },
};
