// Maps API risk_grade (High/Medium/Low risk) to safety-tier labels for the UI.
// Red = low safety, green = high safety — matches ScoreLegend.

export const SAFETY_TIER = {
  High:   'Low',
  Medium: 'Medium',
  Low:    'High',
};

export function safetyTierLabel(riskGrade) {
  return SAFETY_TIER[riskGrade] ?? riskGrade;
}

// Filter value = API risk_grade; label = safety tier shown in the table.
export const ALERT_FILTERS = [
  { value: 'atRisk', label: 'At-risk only' },
  { value: 'High', label: 'Low' },
  { value: 'Medium', label: 'Medium' },
  { value: 'all', label: 'All' },
];

export const SAFETY_COLOURS = {
  High:   '#ea4335', // low safety
  Medium: '#f9ab00', // med safety
  Low:    '#34a853', // high safety
};
