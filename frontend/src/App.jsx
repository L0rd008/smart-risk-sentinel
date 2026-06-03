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
  ALERTS:     'alerts',
  BORROWER:   'borrower',
  STRESSTEST: 'stress',
};

const TABS = [
  { id: VIEWS.DASHBOARD, label: 'Dashboard' },
  { id: VIEWS.ALERTS,    label: 'Alerts' },
  { id: VIEWS.STRESSTEST, label: 'Stress Test' },
];

/** Which header tab should appear selected for the current view. */
function activeTabFor(view) {
  // Map each view to the header tab that should be highlighted.
  if (view === VIEWS.ALERTS) return VIEWS.ALERTS;
  if (view === VIEWS.STRESSTEST) return VIEWS.STRESSTEST;
  if (view === VIEWS.BORROWER) return VIEWS.DASHBOARD;
  return VIEWS.DASHBOARD;
}

export default function App() {
  const [view, setView] = useState(VIEWS.DASHBOARD);
  const [selectedId, setSelectedId] = useState(null);
  const [returnView, setReturnView] = useState(VIEWS.ALERTS);
  const [apiReachable, setApiReachable] = useState(null);

  const activeTab = activeTabFor(view);

  useEffect(() => {
    api
      .getHealth()
      .then(() => setApiReachable(true))
      .catch(() => setApiReachable(false));
  }, []);

  const goToTab = (tabId) => setView(tabId);

  const openBorrower = (customerId) => {
    setSelectedId(customerId);
    setView(VIEWS.BORROWER);
  };

  const openStressTest = (customerId, fromView = VIEWS.ALERTS) => {
    setSelectedId(customerId);
    setReturnView(fromView);
    setView(VIEWS.STRESSTEST);
  };

  return (
    <div style={styles.app}>
      <header style={styles.header}>
        <h1 style={styles.title}>Smart-Risk Sentinel</h1>
        <nav style={styles.nav} aria-label="Main navigation">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              style={{
                ...styles.tabBtn,
                ...(activeTab === tab.id ? styles.tabBtnActive : {}),
              }}
              onClick={() => goToTab(tab.id)}
              aria-current={activeTab === tab.id ? 'page' : undefined}
            >
              {tab.label}
            </button>
          ))}
          <span
            style={styles.apiStatus}
            title={
              apiReachable === null
                ? 'API: checking...'
                : apiReachable
                ? 'API: connected'
                : 'API: unreachable'
            }
            aria-live="polite"
          >
            <span
              style={{
                ...styles.statusDot,
                background:
                  apiReachable === null ? '#9aa4b2' : apiReachable ? '#34a853' : '#ea4335',
              }}
              aria-hidden="true"
            />
            <span style={styles.statusLabel}>API</span>
          </span>
        </nav>
      </header>

      <main style={styles.main}>
        {view === VIEWS.BORROWER && (
          <nav style={styles.breadcrumb} aria-label="Breadcrumb">
            <button
              type="button"
              style={styles.breadcrumbLink}
              onClick={() => setView(VIEWS.DASHBOARD)}
            >
              Dashboard
            </button>
            <span style={styles.breadcrumbSep}>&gt;</span>
            <span style={styles.breadcrumbCurrent}>Borrower Detail</span>
          </nav>
        )}

        {view === VIEWS.DASHBOARD && <PortfolioSnapshot />}

        {view === VIEWS.ALERTS && (
          <AlertDashboard
            onBorrowerClick={openBorrower}
            onStressTestClick={(id) => openStressTest(id, VIEWS.ALERTS)}
          />
        )}

        {view === VIEWS.BORROWER && selectedId && (
          <BorrowerCard
            customerId={selectedId}
            onStressTest={() => openStressTest(selectedId, VIEWS.BORROWER)}
            // When viewing a borrower, the header/tab should remain Dashboard
            // but the back action should return the user to Alerts (where they
            // typically arrived from).
            onBack={() => setView(VIEWS.ALERTS)}
          />
        )}

        {view === VIEWS.STRESSTEST && selectedId && (
          <>
            <nav style={styles.breadcrumb} aria-label="Breadcrumb">
              <button
                type="button"
                style={styles.breadcrumbLink}
                onClick={() => setView(VIEWS.DASHBOARD)}
              >
                Dashboard
              </button>
              {returnView === VIEWS.BORROWER && (
                <>
                  <span style={styles.breadcrumbSep}>&gt;</span>
                  <button
                    type="button"
                    style={styles.breadcrumbLink}
                    onClick={() => setView(VIEWS.BORROWER)}
                  >
                    Borrower Detail
                  </button>
                </>
              )}
              <span style={styles.breadcrumbSep}>&gt;</span>
              <span style={styles.breadcrumbCurrent}>Stress Test</span>
            </nav>
            <StressTestPanel
              customerId={selectedId}
              onBack={() => setView(returnView)}
              backLabel={
                returnView === VIEWS.BORROWER
                  ? 'Back to borrower detail'
                  : 'Back to alerts'
              }
            />
          </>
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
    flexWrap: 'wrap',
    gap: 12,
  },
  title: { margin: 0, fontSize: '20px' },
  nav: { display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' },
  tabBtn: {
    padding: '6px 14px',
    borderRadius: 4,
    border: '1px solid transparent',
    background: 'transparent',
    color: 'rgba(255,255,255,0.85)',
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
  },
  tabBtnActive: {
    background: 'white',
    color: '#1a73e8',
    fontWeight: 600,
    borderColor: 'white',
  },
  apiStatus: { fontSize: '12px', opacity: 0.85, marginLeft: 8 },
  statusDot: {
    display: 'inline-block',
    width: 10,
    height: 10,
    borderRadius: 10,
    marginRight: 8,
    verticalAlign: 'middle',
    boxShadow: '0 0 0 2px rgba(255,255,255,0.12) inset',
  },
  statusLabel: { fontSize: 12, color: 'rgba(255,255,255,0.9)', opacity: 0.85 },
  main: { padding: '24px' },
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 16,
    fontSize: 14,
  },
  breadcrumbLink: {
    background: 'none',
    border: 'none',
    padding: 0,
    color: '#1a73e8',
    cursor: 'pointer',
    fontSize: 14,
    textDecoration: 'underline',
  },
  breadcrumbSep: { color: '#666' },
  breadcrumbCurrent: { color: '#444', fontWeight: 600 },
};
