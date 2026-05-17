// Smart-Risk Sentinel — API client.
// Owned by Member 4 (React Frontend).
// One function per endpoint defined in docs/API_CONTRACT.md.
// Base URL comes from REACT_APP_API_URL (set in .env.local for overrides).

import axios from 'axios';

const BASE_URL =
  process.env.REACT_APP_API_URL || 'http://localhost:5000/api';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ---------------------------------------------------------------------------
// Endpoint wrappers (return response.data so callers don't unwrap)
// ---------------------------------------------------------------------------

export async function getHealth() {
  const { data } = await client.get('/health');
  return data;
}

export async function listBorrowers() {
  const { data } = await client.get('/borrowers');
  return data;
}

export async function getBorrower(customerId) {
  const { data } = await client.get(`/borrowers/${customerId}`);
  return data;
}

export async function getRisk(customerId) {
  const { data } = await client.get(`/risk/${customerId}`);
  return data;
}

export async function getPortfolioSnapshot() {
  const { data } = await client.get('/portfolio/snapshot');
  return data;
}

export async function stressTest(customerId, overrides) {
  const { data } = await client.post('/stress-test', {
    customer_id: customerId,
    overrides,
  });
  return data;
}

const api = {
  getHealth,
  listBorrowers,
  getBorrower,
  getRisk,
  getPortfolioSnapshot,
  stressTest,
};

export default api;
