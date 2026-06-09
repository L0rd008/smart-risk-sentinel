// Risk grade colours and labels for the UI.
// Red = High risk (low score), green = Low risk (high score).

export const GRADE_COLOURS = {
  Low:    '#34a853',
  Medium: '#f9ab00',
  High:   '#ea4335',
};

export function riskGradeLabel(riskGrade) {
  return riskGrade ? `${riskGrade} Risk` : '';
}

export const ALERT_FILTERS = [
  { value: 'atRisk', label: 'At-risk only' },
  { value: 'High', label: 'High' },
  { value: 'Medium', label: 'Medium' },
  { value: 'all', label: 'All' },
];
