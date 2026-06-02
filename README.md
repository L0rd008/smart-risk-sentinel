# Smart-Risk Sentinel

A real-time borrower risk decision-support web application — university
prototype built for People's Leasing & Finance PLC (PLC), Sri Lanka.

> **Status:** University prototype, not a production banking system.
> See [`docs/PROBLEM_DESCRIPTION.md`](docs/PROBLEM_DESCRIPTION.md) for full context.

---

## Team

| Name                          | Student ID | Role                              | Branch                    |
|-------------------------------|------------|-----------------------------------|---------------------------|
| S.M.P.U. Senevirathne         | 220599M    | Database & Data Layer             | `feature/database`        |
| M.S.I. Weerawansa             | 220690J    | Scoring Engine                    | `feature/scoring-engine`  |
| G.M.A.M. Abhayawickrama       | 220011G    | Flask API Layer                   | `feature/flask-api`       |
| Himani M.K.K.                 | 220231F    | React Frontend / Dashboard        | `feature/react-dashboard` |
| Rebeka K.K.M.                 | 220534L    | Integration & Stress Testing      | `feature/integration`     |

See [`docs/ROLES.md`](docs/ROLES.md) for the full file-ownership map.

---

## Prerequisites

- **Python 3.11+**
- **Node 18+** with npm
- **PostgreSQL 15** running locally on port 5432
- **Git**

---

## Local setup

### 1. Clone and enter the repo
```bash
git clone https://github.com/L0rd008/smart-risk-sentinel.git
cd smart-risk-sentinel
```

### 2. Backend — create venv and install
```bash
cd backend
python -m venv venv
# Windows PowerShell:
venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment
Copy the template and fill in your local PostgreSQL password:
```bash
cd backend
cp .env.example .env
# Edit .env with your DB_PASSWORD
```

### 4. Create the database
```bash
# In a psql shell:
CREATE DATABASE smart_risk_sentinel;
\c smart_risk_sentinel
\i backend/data/schema.sql
```

### 5. Seed the database
```bash
# From the repo root, with the venv active:
python backend/data/seed_data.py
```
This generates ~1,000 synthetic borrowers across all persona types.

### 6. Run the backend
```bash
cd backend
python run.py
# Flask listens on http://localhost:<FLASK_PORT> (default: 5000)
```

### 7. Run the frontend (in a new terminal)
```bash
cd frontend
npm install
npm start
# React dev server opens http://localhost:3000
```

The backend port comes from `FLASK_PORT` in `backend/.env`, defaulting to
`5000`. The frontend reads its API base URL from `REACT_APP_API_URL`, or builds
one from `REACT_APP_API_PORT`, also defaulting to `5000`. If you change
`FLASK_PORT`, set the same port in `frontend/.env.local`:

```bash
REACT_APP_API_PORT=5001
```

---

## Running tests

```bash
# From the backend/ directory (recommended):
cd backend
pytest tests/ -v

# Or from the repo root:
pytest backend/tests/ -v
```

The `backend/pytest.ini` ensures `app` is importable from either location.

---

## Branch workflow

```
main          ← protected, demo cut here only
  └── dev     ← integration branch
        ├── feature/database
        ├── feature/scoring-engine
        ├── feature/flask-api
        ├── feature/react-dashboard
        └── feature/integration
```

- **Always** branch from `dev`.
- **Always** PR back into `dev`, never into `main`.
- Member 5 owns the final cut from `dev` to `main` after demo readiness.
- Merge order at end of sprint:
  `database → scoring-engine → flask-api → react-dashboard → integration`.

---

## API reference

See [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md). The contract is **frozen
at v1.0** — no silent shape changes.

---

## Project structure

```
smart-risk-sentinel/
├── backend/
│   ├── app/
│   │   ├── compliance/      LTV gate (regulatory hard rule)
│   │   ├── models/          DB row dataclasses (optional, kept minimal)
│   │   ├── routes/          Flask blueprints (the 5 API endpoints)
│   │   ├── scoring/         Scorecard engine + tunable config JSON
│   │   ├── __init__.py      Flask app factory
│   │   ├── config.py        Loads .env
│   │   └── db_connect.py    psycopg2 connection helper
│   ├── data/
│   │   ├── schema.sql       PostgreSQL DDL for all 5 tables
│   │   └── seed_data.py     Generates ~1,000 synthetic borrowers
│   ├── tests/
│   │   └── test_scorecard.py
│   ├── .env.example         Template — copy to .env and fill in
│   ├── pytest.ini           Test runner config (pythonpath)
│   ├── requirements.txt
│   └── run.py
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AlertDashboard.jsx
│   │   │   ├── BorrowerCard.jsx
│   │   │   ├── PortfolioSnapshot.jsx
│   │   │   └── StressTestPanel.jsx
│   │   ├── services/
│   │   │   └── api.js       Axios calls to the Flask API
│   │   ├── App.jsx
│   │   ├── index.css        CSS reset + design tokens
│   │   └── index.js
│   ├── public/
│   │   └── index.html
│   └── package.json
├── docs/
│   ├── API_CONTRACT.md      Frozen REST contract
│   ├── DATA_SCHEMA.md       Database reference
│   ├── PROBLEM_DESCRIPTION.md  Full project context
│   └── ROLES.md             Who owns what
├── .gitignore
└── README.md
```

---

## Out of scope

Explicitly **not** built in this prototype:

- Real CRIB / PLC API integration (all data is synthetic)
- Multi-factor authentication, user management
- Machine learning / scikit-learn models
- Mobile app, PWA
- Docker / Kubernetes / cloud deployment
- CI/CD pipelines
- Email / SMS notifications

See [`docs/PROBLEM_DESCRIPTION.md`](docs/PROBLEM_DESCRIPTION.md) §12 for the full list.

---

## Demo instructions

1. `python backend/data/seed_data.py` — seed the synthetic portfolio.
2. `python backend/run.py` — start the Flask API.
3. `npm start` in `frontend/` — start the React dashboard.
4. Open `http://localhost:3000` and follow the 5-beat demo script in
   `docs/PROBLEM_DESCRIPTION.md` §13.
