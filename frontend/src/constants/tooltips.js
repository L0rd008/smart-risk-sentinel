// Domain explanations for dashboard metrics

export const METRIC_TOOLTIPS = {
  riskScore:
    'Composite risk rating from 0–1000 (base 500). 650–1000 = Low (Green), 450–649 = Medium (Amber), 0–449 = High (Red). LTV cap breach forces Red.',
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
  geoConcentration:
    'Share of the synthetic portfolio by Sri Lankan province. Blue bars show actual distribution; grey bars show PLC\'s 2024/25 geographic concentration targets from the Risk Management Review.',
};
