// Smart-Risk Sentinel — top-level App.
// Owned by Member 4 (React Frontend). Simple state-based routing — no
// react-router needed for a three-view dashboard.

import React, { useState, useEffect } from 'react';
import api from './services/api';
import PortfolioSnapshot from './components/PortfolioSnapshot';
import AlertDashboard from './components/AlertDashboard';
import BorrowerCard from './components/BorrowerCard';
import StressTestPanel from './components/StressTestPanel';

const VIEWS = {
  DASHBOARD:  'dashboard',
  BORROWER:   'borrower',
  STRESSTEST: 'stress',
};

export default function App() {
  const [view, setView] = useState(VIEWS.DASHBOARD);
  const [selectedId, setSelectedId] = useState(null);
  const [apiReachable, setApiReachable] = useState(null);

  useEffect(() => {
    api
      .getHealth()
      .then(() => setApiReachable(true))
      .catch(() => setApiReachable(false));
  }, []);

  const openBorrower = (customerId) => {
    setSelectedId(customerId);
    setView(VIEWS.BORROWER);
  };

  const openStressTest = (customerId) => {
    setSelectedId(customerId);
    setView(VIEWS.STRESSTEST);
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>Smart-Risk Sentinel</h1>
        <nav style={styles.nav}>
          <button onClick={() => setView(VIEWS.DASHBOARD)}>Dashboard</button>
          <span style={styles.apiStatus}>
            API:{' '}
            {apiReachable === null
              ? 'checking...'
              : apiReachable
              ? 'connected'
              : 'unreachable'}
          </span>
        </nav>
      </header>

      <main style={styles.main}>
        {view === VIEWS.DASHBOARD && (
          <>
            <PortfolioSnapshot />
            <AlertDashboard
              onBorrowerClick={openBorrower}
              onStressTestClick={openStressTest}
            />
          </>
        )}

        {view === VIEWS.BORROWER && selectedId && (
          <BorrowerCard
            customerId={selectedId}
            onStressTest={() => setView(VIEWS.STRESSTEST)}
            onBack={() => setView(VIEWS.DASHBOARD)}
          />
        )}

        {view === VIEWS.STRESSTEST && selectedId && (
          <StressTestPanel
            customerId={selectedId}
            onBack={() => setView(VIEWS.DASHBOARD)}
          />
        )}
      </main>
    </div>
  );
}

const styles = {
  app: {
    fontFamily: 'system-ui, -apple-system, sans-serif',
    color: '#1a1a1a',
    minHeight: '100vh',
    background: '#f4f6f8',
  },
  header: {
    background: '#1a73e8',
    color: 'white',
    padding: '12px 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: { margin: 0, fontSize: '20px' },
  nav: { display: 'flex', gap: '16px', alignItems: 'center' },
  apiStatus: { fontSize: '12px', opacity: 0.85 },
  main: { padding: '24px' },
};
