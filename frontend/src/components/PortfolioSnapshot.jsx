// PortfolioSnapshot — doughnut + sector table + geographic concentration.
// Owned by Member 4.

import React, { useEffect, useState } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import api from '../services/api';
import InfoTip from './common/InfoTip';
import { METRIC_TOOLTIPS } from '../constants/tooltips';

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

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

  const provinces = snapshot.by_province || [];
  const geoBarData = {
    labels: provinces.map((p) => p.province),
    datasets: [
      {
        label: 'Portfolio %',
        data: provinces.map((p) => p.pct),
        backgroundColor: '#1a73e8',
        borderRadius: 4,
      },
      {
        label: 'PLC target %',
        data: provinces.map((p) => p.plc_target_pct),
        backgroundColor: 'rgba(95, 99, 104, 0.25)',
        borderColor: '#5f6368',
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const geoBarOptions = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom' },
      tooltip: {
        callbacks: {
          label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.x.toFixed(1)}%`,
        },
      },
    },
    scales: {
      x: {
        max: 45,
        ticks: { callback: (v) => `${v}%` },
        title: { display: true, text: 'Share of portfolio' },
      },
    },
  };

  return (
    <div>
      <div style={styles.wrap}>
        <div style={styles.left}>
          <h2 style={styles.h2}>Portfolio Snapshot</h2>
          <div style={styles.metrics}>
            <Metric label="Borrowers" value={snapshot.total_borrowers} />
            <Metric label="Avg Safety Score" value={snapshot.avg_portfolio_score} />
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
                <th style={styles.th}>Avg Safety Score</th>
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

      <div style={styles.geoWrap}>
        <div style={styles.geoHeader}>
          <h3 style={styles.geoH3}>
            Geographic Concentration
            <InfoTip text={METRIC_TOOLTIPS.geoConcentration} />
          </h3>
          <p style={styles.geoSub}>
            Portfolio distribution across Sri Lankan provinces, benchmarked
            against PLC&apos;s 2024/25 concentration profile.
          </p>
        </div>
        <div style={styles.geoGrid}>
          <div style={styles.geoChartBox}>
            <Bar data={geoBarData} options={geoBarOptions} />
          </div>
          <div>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>Province</th>
                  <th style={styles.th}>Count</th>
                  <th style={styles.th}>Portfolio %</th>
                  <th style={styles.th}>PLC target %</th>
                  <th style={styles.th}>Avg Safety Score</th>
                </tr>
              </thead>
              <tbody>
                {provinces.map((p) => (
                  <tr key={p.province}>
                    <td style={styles.td}>{p.province}</td>
                    <td style={styles.td}>{p.count}</td>
                    <td style={styles.td}>{p.pct}%</td>
                    <td style={styles.td}>{p.plc_target_pct}%</td>
                    <td style={styles.td}>{p.avg_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
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
  geoWrap: {
    background: 'white',
    padding: 24,
    borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    marginBottom: 24,
  },
  geoHeader: { marginBottom: 16 },
  geoH3: {
    margin: 0,
    fontSize: 16,
    display: 'flex',
    alignItems: 'center',
  },
  geoSub: {
    margin: '6px 0 0',
    fontSize: 13,
    color: '#5f6368',
    lineHeight: 1.5,
  },
  geoGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 24,
    alignItems: 'start',
  },
  geoChartBox: { height: 360 },
};
