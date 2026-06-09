# Roles & Workstreams — Smart-Risk Sentinel

> Five members, five branches, one frozen API contract between them.
> Every file in the repo is owned by exactly one member. If you find
> yourself wanting to edit a file outside your column, ask first.

---

## Branching workflow

```
main          ← protected, only Member 5 merges here after demo
  └── dev     ← integration branch, all features merge here first
        ├── feature/database         (Member 1)
        ├── feature/scoring-engine   (Member 2)
        ├── feature/flask-api        (Member 3)
        ├── feature/react-dashboard  (Member 4)
        └── feature/integration      (Member 5)
```

- Branch from `dev`, PR back into `dev`.
- Never push to `main` directly.
- The merge order at the end of the sprint is fixed:
  `database → scoring-engine → flask-api → react-dashboard → integration`.
  Earlier merges have to wait if a later branch depends on a contract change.

---

## Member 1 — Database & Data Layer

| Field           | Value                                               |
|-----------------|-----------------------------------------------------|
| Student         | S.M.P.U. Senevirathne                               |
| Student ID      | 220599M                                             |
| Branch          | `feature/database`                                  |
| Primary files   | `backend/data/schema.sql`, `backend/data/seed_data.py`, `backend/app/db_connect.py` |

### Deliverables
- PostgreSQL schema for 5 tables: `borrowers`, `lease_agreements`,
  `market_valuations`, `sector_reference`, `risk_scores_log`.
- Seed script generating **1,000 synthetic borrower records** using `Faker`
  combined with manual persona logic from the persona list below.
- Distribution requirement: **≥10% obvious High Risk**, **≥10% obvious Low
  Risk**, the rest spread realistically across the middle.
- A `db_connect.py` utility in `backend/app/` that returns a `psycopg2`
  connection using the env vars in `.env`.

### Persona types to simulate (minimum coverage)
1. **Prime salaried employee** — CRIB A, low DPD, LTV ~35%
2. **SME delivery truck operator** — CRIB B/C, LTV ~65%, moderate DTI
3. **Subprime entrepreneur** — high volatile income, LTV exactly at 70% cap
4. **Strategic defaulter** — pays day 29 every month, widening DPD trend
5. **New-to-credit (Grade XX)** — no CRIB history, leans on collateral
6. **Tourism sector borrower** — high sector NPL exposure
7. **Recovering distressed** — was Red, DPD pattern now improving

### Dependencies
None. **You work first.** Nothing in this project runs until the DB is seeded.

### Hand-off
To **Member 3** (Flask API needs the connection and the schema).
To **Member 2** (the borrower dict shape consumed by `Scorecard.calculate`
must match the columns you write).

---

## Member 2 — Scoring Engine

| Field           | Value                                                            |
|-----------------|------------------------------------------------------------------|
| Student         | M.S.I. Weerawansa                                                |
| Student ID      | 220690J                                                          |
| Branch          | `feature/scoring-engine`                                         |
| Primary files   | `backend/app/scoring/scorecard.py`, `backend/app/scoring/scorecard_config.json` |
| Secondary files | `backend/tests/test_scorecard.py` (shared with Member 5)        |

### Deliverables
- A `Scorecard` Python class with a `calculate(borrower_dict) -> dict`
  method that returns **the full risk object matching the API contract**
  response shape for `GET /api/risk/:customer_id`.
- Binning logic for all 5 categories: DTI, CRIB grade, LTV, sector NPL,
  net worth.
- **All weights and bin thresholds live in `scorecard_config.json`** so
  they can be tuned without touching code.
- The LTV compliance gate must **import** `backend/app/compliance/ltv_gate.py`
  rather than re-implementing the cap check.
- At least **5 unit tests** in `backend/tests/test_scorecard.py` covering:
  LTV breach, CRIB grade XX, perfect score, guaranteed Red, an Amber
  edge case at exactly 419/420 and 619/620.

### Dependencies
None for the class itself — you can develop against any dict matching the
contract's borrower shape. You depend on Member 3 only at integration time,
when your class is wired into the Flask route.

### Hand-off
To **Member 3** (Flask routes import the `Scorecard` class).

---

## Member 3 — Flask API Layer

| Field           | Value                                                                                              |
|-----------------|----------------------------------------------------------------------------------------------------|
| Student         | G.M.A.M. Abhayawickrama                                                                            |
| Student ID      | 220011G                                                                                            |
| Branch          | `feature/flask-api`                                                                                |
| Primary files   | `backend/app/routes/risk_routes.py`, `backend/app/compliance/ltv_gate.py`, `backend/run.py`, `backend/app/__init__.py`, `backend/app/config.py` |

### Deliverables
- All **5 API endpoints** from `API_CONTRACT.md`, returning exactly the
  shapes documented there.
- `ltv_gate(vehicle_type, ltv_ratio) -> {"breach": bool, "reason": str | None}`
  function — small, pure, well-tested. Member 2 will import this.
- Flask app factory in `app/__init__.py` with CORS enabled for
  `http://localhost:3000` (the React dev server).
- `config.py` that reads DB credentials from `.env` via `python-dotenv`.
- The `POST /api/stress-test` endpoint must: load the borrower from DB,
  merge in the request `overrides`, call `Scorecard.calculate`, return the
  resulting risk object. **Nothing is persisted.**

### Dependencies
- **Member 1** — DB schema must exist and be seeded before your routes
  return real data.
- **Member 2** — `Scorecard.calculate` must exist before
  `/api/risk/:customer_id` and `/api/stress-test` can return.

You can develop against Member 2's stub (which already returns a
contract-shaped dict) before their real binning is in.

### Hand-off
To **Member 4** (the frontend calls these endpoints).

---

## Member 4 — React Frontend / Dashboard

| Field           | Value                                                  |
|-----------------|--------------------------------------------------------|
| Student         | Himani M.K.K.                                          |
| Student ID      | 220231F                                                |
| Branch          | `feature/react-dashboard`                              |
| Primary files   | All files under `frontend/src/`                        |

### Deliverables
- `BorrowerCard.jsx` — displays name, score, grade as a colour-coded card
  (Red/Amber/Green background); lists **top 3 risk drivers** and the
  active **EWI flags**.
- `PortfolioSnapshot.jsx` — doughnut chart (Chart.js) of grade
  distribution, plus a sector table with average scores.
- `AlertDashboard.jsx` — filterable list of all Amber/Red borrowers,
  sorted by severity (Red first, then Amber, then by descending score
  delta from the threshold).
- `StressTestPanel.jsx` — sliders / inputs for overriding LTV, DPD, CRIB
  grade; calls `POST /api/stress-test`; shows **before / after** score
  comparison side by side.
- `services/api.js` — all axios calls to the backend, one function per
  endpoint, base URL from env var `REACT_APP_API_URL`
  (defaults to `http://localhost:5000/api`).
- `App.jsx` — simple state-based routing between views (dashboard /
  borrower detail / stress test). No `react-router` needed.

### Dependencies
- **Member 3** — backend endpoints must be running for real integration.
  You can develop against hardcoded JSON in `services/api.js` (matching the
  contract shapes) until then.

### Hand-off
To **Member 5** (integration testing).

---

## Member 5 — Integration, Stress Testing & Merge Coordination

| Field           | Value                                                  |
|-----------------|--------------------------------------------------------|
| Student         | Rebeka K.K.M.                                          |
| Student ID      | 220534L                                                |
| Branch          | `feature/integration`                                  |
| Primary files   | `backend/tests/` (shared with Member 2), final merges  |

### Deliverables
- **Integration test script** that spins up Flask, seeds the DB, calls all
  5 endpoints, and asserts response shapes match `API_CONTRACT.md`.
- **2022-shock stress scenario**: simulate a sector-wide economic shock —
  bump every borrower's LTV by +20%, DPD by +15 days, drop CRIB grades by
  2 letters. Assert that **≥80% of the portfolio migrates to Medium or
  High risk**. This is the headline demo number.
- Document any integration bugs with clear reproduction steps in
  `backend/tests/INTEGRATION_NOTES.md`.
- **Final merge** of all branches into `dev` in the required order:
  `feature/database → feature/scoring-engine → feature/flask-api →
  feature/react-dashboard → feature/integration`.
- Prepare a **5-row Demo Script** (markdown table): borrower name,
  initial grade, injected event, resulting grade, action triggered.

### Dependencies
- **Everyone.** You merge last and validate end-to-end.

### Hand-off
To the demo. You are the closer.

---

## File ownership map (no file is unassigned)

| File / directory                                  | Owner    |
|---------------------------------------------------|----------|
| `backend/data/schema.sql`                         | Member 1 |
| `backend/data/seed_data.py`                       | Member 1 |
| `backend/app/db_connect.py`                       | Member 1 |
| `backend/app/scoring/scorecard.py`                | Member 2 |
| `backend/app/scoring/scorecard_config.json`       | Member 2 |
| `backend/app/scoring/__init__.py`                 | Member 2 |
| `backend/app/__init__.py`                         | Member 3 |
| `backend/app/config.py`                           | Member 3 |
| `backend/app/routes/risk_routes.py`               | Member 3 |
| `backend/app/routes/__init__.py`                  | Member 3 |
| `backend/app/compliance/ltv_gate.py`              | Member 3 |
| `backend/app/compliance/__init__.py`              | Member 3 |
| `backend/app/models/__init__.py`                  | Member 3 |
| `backend/run.py`                                  | Member 3 |
| `backend/requirements.txt`                        | Member 3 |
| `backend/tests/test_scorecard.py`                 | Member 2 (with Member 5) |
| `backend/tests/test_integration.py` (to be added) | Member 5 |
| `backend/tests/__init__.py`                       | Member 5 |
| `frontend/package.json`                           | Member 4 |
| `frontend/public/index.html`                      | Member 4 |
| `frontend/src/index.js`                           | Member 4 |
| `frontend/src/App.jsx`                            | Member 4 |
| `frontend/src/components/BorrowerCard.jsx`        | Member 4 |
| `frontend/src/components/PortfolioSnapshot.jsx`   | Member 4 |
| `frontend/src/components/AlertDashboard.jsx`      | Member 4 |
| `frontend/src/components/StressTestPanel.jsx`     | Member 4 (with Member 5) |
| `frontend/src/services/api.js`                    | Member 4 |
| `docs/PROBLEM_DESCRIPTION.md`                     | Shared, no silent edits |
| `docs/API_CONTRACT.md`                            | Shared, **frozen** — needs team consensus |
| `docs/DATA_SCHEMA.md`                             | Member 1 |
| `docs/ROLES.md`                                   | Shared   |
| `README.md`                                       | Shared   |
| `.gitignore`                                      | Shared   |
