# Problem Description — Smart-Risk Sentinel

> This document is self-contained. Any team member or AI agent should be
> able to read only this file and have everything they need to start work.
> Do not summarise. Do not delete sections. If you spot something wrong,
> propose a correction in the standup rather than editing silently.

---

## 1. Project name and academic context

**Project name:** Smart-Risk Sentinel
**Team:** Pro Force (Group E)
**Institution:** University of Moratuwa, Sri Lanka
**Course context:** Undergraduate group software engineering project
**Time-box:** ~4 weeks, 5 developers
**Deliverable:** A working prototype decision-support web application —
**not** a production banking system. Every architectural decision in this
project must be justifiable against that prototype scope. We do not need
five-nines availability, multi-factor auth, real CRIB integration, or
cloud deployment. We need a clear, demoable, end-to-end story.

---

## 2. Client background

**Client organisation:** People's Leasing & Finance PLC (PLC)
**Sector:** Non-Bank Financial Institution (NBFI), Sri Lanka
**Position:** One of the largest licensed finance companies in the country,
specialising in leasing (especially motor vehicles) and gold loans.

### The macro picture
Sri Lanka's economy is recovering from the 2022 sovereign debt crisis but
remains volatile. Interest rates have eased, vehicle import restrictions
have begun to relax, and consumer credit demand has rebounded. NBFIs like
PLC have grown their portfolios aggressively in this window — and that
growth is where the risk lives.

### The NPL trend that motivates this project
The Non-Performing Loan (NPL) ratio for the NBFI sector rose from **7.7%
in 2018 to over 17.5% in 2022**. Even as the macro picture has stabilised,
PLC's own annual reports flag credit risk as the single largest exposure on
the balance sheet. Their Risk & Control Department (RCD) tracks Early
Warning Indicators (EWIs) under an Integrated Risk Management (IRM)
framework, governed by the Board's Integrated Risk Management Committee
(BIRMC) — but these signals are currently consumed at portfolio level on
**monthly reporting cycles**.

### What PLC has already said publicly
PLC's 2024/25 Annual Report names a "customer risk rating system" as a
**planned enhancement**. Smart-Risk Sentinel is a university prototype of
exactly that enhancement.

---

## 3. The exact problem being solved

PLC's existing risk infrastructure has a structural blind spot called the
**intelligence lag**:

> By the time a borrower shows up as delinquent in the monthly reporting
> cycle, the risk event is already 30–90 days old.

Concretely:
- **Pre-disbursement:** The credit officer has CRIB data, income docs, and
  vehicle valuation. A decision is made manually using the 5 Cs framework.
- **Post-disbursement:** The borrower disappears from the officer's view
  until a missed payment hits the monthly delinquency report.
- **Recovery:** By the time the case lands in the recovery queue, the
  collateral has often depreciated past the recoverable amount and the
  borrower has stopped responding.

There is no **real-time, borrower-level risk score** that a branch officer
can look at this morning and act on. RCD has the data and the framework;
the field staff have the relationships and the authority to act; nothing
connects them.

Smart-Risk Sentinel sits in that gap.

---

## 4. The proposed solution

A web application that:

1. Stores a synthetic portfolio of ~1,000 borrowers in PostgreSQL.
2. Calculates a borrower risk score (0–1000) using a hybrid expert-
   statistical scorecard built on the 5 Cs of credit.
3. Assigns a risk grade — **Low / Medium / High** (Green / Amber / Red).
4. Flags Early Warning Indicators (EWIs) when thresholds are breached.
5. Enforces hard regulatory compliance gates (CBSL LTV caps).
6. Exposes the data via a Flask REST API following a frozen contract.
7. Renders it in a React dashboard with per-borrower cards, a portfolio
   snapshot, an alert list, and a stress-test panel.

### What it explicitly is NOT
- It is not connected to PLC's real systems, CRIB, or any external API.
- It is not a production system. There is no real money at stake.
- It is not an underwriting decision engine. It is a **decision-support**
  tool — a human officer still makes every call.
- It does not use machine learning. The scorecard is rules-based and fully
  inspectable, which is deliberate (regulators require explainability).

---

## 5. Regulatory constraints

### CBSL Loan-to-Value (LTV) caps — CBSL Directions No. 03 of 2025
These are **hard regulatory limits**. The Central Bank of Sri Lanka has
issued binding directions for licensed finance companies:

| Vehicle category   | Maximum LTV |
|--------------------|-------------|
| Private motor car  | 50%         |
| Commercial vehicle | 70%         |

**System rule:** If a borrower's LTV exceeds the cap for their vehicle
type, the system grades them **Red regardless of their numeric score**.
This gate is non-negotiable and lives in `backend/app/compliance/ltv_gate.py`.
Both the API route and the scoring engine must consult it; neither may
re-implement it.

### IFRS 9 staging awareness
The Sri Lankan Financial Reporting Standard 9 classifies loans into three
stages by credit-risk deterioration:

- **Stage I** — performing, no significant increase in credit risk (SICR)
- **Stage II** — SICR observed, lifetime expected credit loss recognised
- **Stage III** — credit-impaired (typically 90+ days past due)

Our risk grades are intentionally aligned: Low ≈ Stage I, Medium ≈ Stage
II (an early warning), High ≈ Stage III risk. We do not compute expected
credit loss; we only colour the borrower so the officer knows where they
sit. This alignment is for explainability when presenting to the client.

---

## 6. The scoring model

### Formula
```
Final Score = Base Score (500) + Σ (Category Weight × Attribute Points)
```

Score range: 0–1000, with 500 as the neutral starting point. Each of the
five categories produces an attribute-points value (typically -300 to
+300), which is multiplied by the category weight and added to the base.

### The 5 Cs and their weights

| Category   | Weight | Key metrics                                       |
|------------|--------|---------------------------------------------------|
| Capacity   | 35%    | Debt-to-Income ratio, monthly cash flow velocity  |
| Character  | 30%    | CRIB Grade, payment drift (DPD pattern over 6 mo) |
| Collateral | 20%    | Current LTV, asset type, resale liquidity         |
| Conditions | 10%    | Sector NPL ratio, macro/GDP outlook               |
| Capital    | 5%     | Net worth, savings balance                        |

Weights sum to 100%. They live in `backend/app/scoring/scorecard_config.json`
so the team can tune without code changes.

### Score bands
- **650–1000** → Low Risk (Green)
- **450–649** → Medium Risk (Amber)
- **0–449** → High Risk (Red)

### Worked example
A salaried customer applying for a private motor car lease:
- DTI 28% → Capacity contributes +200 points × 35% weight = +70
- CRIB Grade B → Character contributes +150 × 30% = +45
- LTV 38% (Private, under the 50% cap) → Collateral contributes +100 × 20% = +20
- Sector NPL 4.5% (transport) → Conditions contributes +50 × 10% = +5
- Net worth 8× annual obligation → Capital contributes +100 × 5% = +5
- Base 500 + 70 + 45 + 20 + 5 + 5 = **645 → Medium / Amber**

The exact attribute-point bins live in `scorecard_config.json`. The above
numbers are illustrative; the config file is the source of truth.

---

## 7. The Early Warning Indicator (EWI) framework

These thresholds drive the `ewi_flags` array returned by `/api/risk/:id`
and are also used by `AlertDashboard.jsx` to highlight at-risk borrowers.

| Metric                    | Green             | Amber                            | Red                                |
|---------------------------|-------------------|----------------------------------|------------------------------------|
| Payment delay (current)   | ≤2 days late      | 3–10 days, 3 consecutive months  | >15 days or repeated partials      |
| CRIB Grade                | A, B, C           | D                                | E, or "XX" (no history)            |
| LTV (Private vehicle)     | ≤40%              | 41–49%                           | ≥50% (regulatory breach)           |
| LTV (Commercial vehicle)  | ≤60%              | 61–69%                           | ≥70% (regulatory breach)           |
| App login frequency       | Daily / weekly    | -50% drop over 30 days           | No login for 60 days / bounced     |
| Sector NPL ratio          | <5%               | 6–10%                            | >10%                               |

A single Red flag does not auto-Red the borrower (unless it is a regulatory
LTV breach), but it should be surfaced prominently in the BorrowerCard.

---

## 8. The data strategy

**All data is synthetic.** There is no real customer data in this repo at
any point — neither in seed scripts nor in test fixtures.

### Why PostgreSQL
- Free, mature, runs locally.
- Realistic SQL surface area (joins, window functions, JSON columns) if we
  decide we need them later. We are not using an ORM — `psycopg2` straight
  to SQL, which keeps the data layer transparent for a small team.

### Persona coverage (~1,000 records)
The seed script must generate a realistic spread. At minimum:

- **Prime salaried employee** — stable income, CRIB A, low DPD, LTV ~35%
- **SME delivery truck operator** — moderate DTI, CRIB B/C, LTV ~65%
- **Subprime entrepreneur** — high but volatile income, LTV exactly at 70% cap
- **Strategic defaulter** — pays on day 29 every month, widening DPD trend
- **New-to-credit (Grade XX)** — no CRIB history, relies on collateral
- **Tourism sector borrower** — high sector NPL exposure, otherwise OK
- **Recovering distressed** — was High, DPD pattern now improving

The mix must include at least ~10% obvious High Risk and ~10% obvious Low
Risk so the dashboard is visually interesting from the first frame.

---

## 9. The tech stack and why

| Layer        | Choice                              | Why                                                                |
|--------------|--------------------------------------|--------------------------------------------------------------------|
| Database     | PostgreSQL 15 (local)               | Mature SQL, runs offline, no cloud cost                            |
| Backend      | Python 3.11+, Flask 3, psycopg2      | Tiny surface area, easy onboarding for the 5-dev team              |
| Scoring      | Pure Python, no ML libs              | Explainability is a regulatory requirement; rules > black boxes    |
| Frontend     | React 18 (Create React App)          | Standard, well-documented, easy to demo                            |
| Charts       | Chart.js via react-chartjs-2         | Lightweight, declarative, enough for doughnut/bar/line             |
| HTTP client  | axios                                | Standard pick, plays well with the frozen API contract             |
| Packaging    | pip + npm                            | Standard, no Docker required for a local prototype                 |

Deliberately rejected:
- **No SQLAlchemy / Marshmallow** — adds boilerplate for no benefit at this scale.
- **No Redux / Zustand** — `useState`/`useContext` is enough; one dev, one dashboard.
- **No JWT / OAuth** — single "staff" user is in scope, real auth is not.
- **No Docker / Kubernetes** — local prototype, not a deployment exercise.

---

## 10. The API contract

The frozen REST contract between Flask and React lives in
[`API_CONTRACT.md`](API_CONTRACT.md). It is **immutable** at v1.0 for the
duration of this sprint. Every change costs both members on either side of
the boundary, so we treat it as a hard interface. If a change is genuinely
needed, raise it in standup, bump the version, and notify everyone.

The frontend may mock the contract during development. The backend must
return exactly what the contract specifies, including field names and
nesting.

---

## 11. The 4-week sprint plan

| Week | Theme                          | Outputs                                                                                          |
|------|--------------------------------|--------------------------------------------------------------------------------------------------|
| 1    | Foundations & data             | Repo scaffolded (this commit), DB schema live, seed script runs, 1000 records inserted          |
| 2    | Scoring engine & API           | Scorecard class returns full risk objects, all 5 Flask endpoints live and contract-compliant     |
| 3    | Frontend dashboard             | BorrowerCard, PortfolioSnapshot, AlertDashboard rendering real data from the local Flask server  |
| 4    | Stress testing & demo polish   | StressTestPanel working end-to-end, integration tests green, 5-row demo script rehearsed         |

Slippage protocol: lower-priority features (stress testing, then charts)
are reduced or omitted to preserve a working end-to-end demo. We never
ship a partial vertical slice.

---

## 12. Out of scope

These are explicitly **not** being built. If a team member is tempted to
work on one of these, stop and pair on a Must-Have feature instead.

- Real CRIB / PLC API integration
- Multi-factor authentication, role-based access, user management
- Machine learning models (scikit-learn, neural networks, anything)
- Mobile app or PWA
- Docker / Kubernetes / any container orchestration
- Cloud deployment (AWS, Azure, GCP, anywhere)
- CI/CD pipelines (GitHub Actions etc.)
- Email / SMS notifications
- Audit logging beyond what `risk_scores_log` already captures
- Multi-tenant / multi-branch data isolation
- Internationalisation
- Dark mode, accessibility audit, performance budgets

---

## 13. Definition of done (demo readiness)

The prototype is "done" when a non-technical observer can watch a 5-minute
demo and follow this story:

1. The presenter opens the dashboard. The portfolio snapshot shows the
   grade distribution (e.g. 70% Green, 20% Amber, 10% Red).
2. The presenter clicks an Amber borrower. The BorrowerCard shows the
   score, the top 3 risk drivers, and the active EWI flags.
3. The presenter opens the StressTestPanel for that borrower and bumps
   their LTV from 45% to 52%. The card flips to Red with the compliance
   reason "Private LTV 52% exceeds CBSL cap of 50%".
4. The presenter shows the AlertDashboard, filtered to Red borrowers,
   sorted by severity.
5. The presenter runs the "2022-shock" stress scenario from Member 5's
   integration test and shows the grade migration in the snapshot.

If all five beats land cleanly, we ship.
