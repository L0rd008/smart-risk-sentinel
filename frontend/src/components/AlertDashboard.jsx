// AlertDashboard — filterable list of Amber/Red borrowers sorted by severity.
// Owned by Member 4.

import React, { useEffect, useMemo, useState } from 'react';
import api from '../services/api';

const GRADE_SEVERITY = { High: 0, Medium: 1, Low: 2 };
const GRADE_COLOURS = {
  Low:    '#34a853',
  Medium: '#f9ab00',
  High:   '#ea4335',
};

export default function AlertDashboard({ onBorrowerClick, onStressTestClick }) {
  const [borrowers, setBorrowers] = useState([]);
  const [filter, setFilter] = useState('atRisk');     // 'all' | 'atRisk' | 'High'
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listBorrowers()
      .then((data) => setBorrowers(data.borrowers || []))
      .catch((e) => setError(e.message || 'Failed to load borrowers'))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    const filtered = borrowers.filter((b) => {
      if (filter === 'all') return true;
      if (filter === 'atRisk') return b.risk_grade !== 'Low';
      return b.risk_grade === filter;
    });
    return filtered.sort((a, b) => {
      const sevA = GRADE_SEVERITY[a.risk_grade] ?? 99;
      const sevB = GRADE_SEVERITY[b.risk_grade] ?? 99;
      if (sevA !== sevB) return sevA - sevB;
      return a.risk_score - b.risk_score;
    });
  }, [borrowers, filter]);

  if (error) return <div style={styles.error}>Error: {error}</div>;

  return (
    <div style={styles.wrap}>
      <header style={styles.header}>
        <h2 style={styles.h2}>Alert Dashboard</h2>
        <div style={styles.filters}>
          {['atRisk', 'High', 'Medium', 'all'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                ...styles.filterBtn,
                background: filter === f ? '#1a73e8' : 'white',
                color: filter === f ? 'white' : '#1a1a1a',
              }}
            >
              {f === 'atRisk' ? 'At-risk only' : f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>
      </header>

      {loading ? (
        <div>Loading borrowers...</div>
      ) : visible.length === 0 ? (
        <div style={styles.empty}>No borrowers match this filter.</div>
      ) : (
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Borrower</th>
              <th style={styles.th}>Province</th>
              <th style={styles.th}>Sector</th>
              <th style={styles.th}>Score</th>
              <th style={styles.th}>Grade</th>
              <th style={styles.th}></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((b) => (
              <tr key={b.customer_id} style={styles.row}>
                <td style={styles.td}>{b.name}</td>
                <td style={styles.td}>{b.province || '—'}</td>
                <td style={styles.td}>{b.sector}</td>
                <td style={styles.td}>{b.risk_score}</td>
                <td style={styles.td}>
                  <span
                    style={{
                      ...styles.badge,
                      background: GRADE_COLOURS[b.risk_grade] || '#999',
                    }}
                  >
                    {b.risk_grade}
                  </span>
                </td>
                <td style={styles.td}>
                  <button
                    style={styles.actionBtn}
                    onClick={() => onBorrowerClick && onBorrowerClick(b.customer_id)}
                  >
                    Open
                  </button>
                  <button
                    style={{ ...styles.actionBtn, marginLeft: 6 }}
                    onClick={() =>
                      onStressTestClick && onStressTestClick(b.customer_id)
                    }
                  >
                    Stress test
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const styles = {
  wrap: {
    background: 'white', padding: 24, borderRadius: 8,
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  header: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: 16,
  },
  h2: { margin: 0 },
  filters: { display: 'flex', gap: 6 },
  filterBtn: {
    padding: '6px 12px', border: '1px solid #ddd',
    borderRadius: 4, cursor: 'pointer', fontSize: 13,
  },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { textAlign: 'left', padding: '8px', borderBottom: '2px solid #ddd', fontSize: 12 },
  td: { padding: '8px', borderBottom: '1px solid #eee', fontSize: 13 },
  row: {},
  badge: {
    color: 'white', padding: '3px 8px',
    borderRadius: 12, fontSize: 11, fontWeight: 700,
  },
  actionBtn: {
    padding: '4px 10px', fontSize: 12,
    border: '1px solid #1a73e8', background: 'white',
    color: '#1a73e8', borderRadius: 4, cursor: 'pointer',
  },
  empty: { padding: 24, textAlign: 'center', opacity: 0.6 },
  error: { padding: 16, background: '#fce8e6', color: '#a50e0e' },
};
