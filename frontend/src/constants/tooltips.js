// Domain explanations for dashboard metrics

export const METRIC_TOOLTIPS = {
  safetyScore:
    'Safety Score from 0–1000 (base 500). Higher is better. Red = high risk (0–449), amber = medium risk (450–649), green = low risk (650–1000). LTV cap breach forces red.',
  cribGrade:
    'Credit Information Bureau (Sri Lanka) rating. A = Very Low Risk, B = Low Risk, C = Average, D = High Risk, E = Very High Risk, XX = No credit history.',
  ltv:
    'Loan-to-Value: loan amount ÷ vehicle value. CBSL caps: 50% for private vehicles, 70% for commercial. Exceeding the cap = regulatory breach.',
  dpd:
    'Days Past Due: how many days late on the current payment. >30 days = Non-Performing Loan (NPL) classification.',
  dti:
    'Debt-to-Income: total monthly obligations ÷ monthly income. Below 30% is healthy; above 50% indicates stress.',
  sectorNpl:
    "Non-Performing Loan ratio for the borrower's industry sector. Higher NPL means the sector is under economic stress.",
  appLogin:
    "Monthly logins to PLC's mobile app (PLC Touch). Declining engagement often precedes payment distress.",
  netWorth:
    'Total assets minus total liabilities.',
  fiveCs:
    'The five dimensions of creditworthiness: Capacity (ability to pay), Character (credit history), Collateral (asset backing), Conditions (sector environment), Capital (net worth).',
  ewi:
    'Early Warning Indicators: traffic-light signals (Green/Amber/Red) that flag borrowers showing signs of deterioration before they actually default.',
  scoreChange:
    'Percentage change in the Safety Score after the simulated scenario. Higher scores mean lower risk. Green = score held or improved; red = significant drop under stress.',
  geoConcentration:
    'Share of the synthetic portfolio by Sri Lankan province. Blue bars show actual distribution; grey bars show PLC\'s 2024/25 geographic concentration targets from the Risk Management Review.',
};
