// ScoreLegend — Green / Amber / Red bands on the 0–1000 score scale.

import React from 'react';

const BANDS = [
  { color: '#34a853', grade: 'Low', range: '1000-650' },
  { color: '#f9ab00', grade: 'Med', range: '649-450' },
  { color: '#ea4335', grade: 'High', range: '449-0' },
];

export default function ScoreLegend() {
  return (
    <div style={styles.wrap} aria-label="Risk score bands">
      <div style={styles.grid}>
        {BANDS.map((band) => (
          <div key={band.grade} style={styles.col}>
            <div style={{ ...styles.bar, background: band.color }} />
            <span style={styles.grade}>{band.grade}</span>
            <span style={styles.range}>{band.range}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  wrap: { marginTop: 10, width: '100%' },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
  },
  col: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 2,
  },
  bar: {
    width: '100%',
    height: 8,
    borderRadius: 4,
    marginBottom: 2,
  },
  grade: {
    fontSize: 10,
    fontWeight: 700,
    color: '#5f6368',
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  range: {
    fontSize: 11,
    fontWeight: 600,
    color: '#5f6368',
    whiteSpace: 'nowrap',
  },
};
