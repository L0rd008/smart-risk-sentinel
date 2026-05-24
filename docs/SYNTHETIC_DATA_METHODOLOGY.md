# Synthetic Data Methodology — Smart-Risk Sentinel

> This document explains the domain rationale behind every design
> decision in `backend/data/seed_data.py`. It is intended for credit
> risk professionals, academic evaluators, and team members who need to
> understand **why** the synthetic data looks the way it does — not how
> the code works mechanically.

---

## 1. Objective

The seed script generates **1,000 synthetic borrower records** that model
the customer portfolio of People's Leasing & Finance PLC (PLC), one of
Sri Lanka's largest Non-Bank Financial Institutions (NBFIs). The data
must be:

- **Financially plausible** — every numeric range maps to real Sri Lankan
  economic conditions as of 2024/2025.
- **Operationally defensible** — every field represents data that PLC
  could realistically collect through its existing systems.
- **Scoreable** — the data must produce a meaningful distribution
  (~70% Low Risk, ~20% Medium Risk, ~10% High Risk) when processed by
  the scoring engine.
- **Reproducible** — deterministic seeding (`random.seed(42)`,
  `Faker.seed(42)`) ensures identical output across runs.

---

## 2. Borrower Names — Sri Lankan Localisation

### Decision

We use a curated list of common **Sinhalese, Tamil, and Muslim** names
rather than Faker's default English locale.

### Rationale

PLC operates 109 branches across Sri Lanka and serves a multi-ethnic
customer base. Generating names like "John Smith" or "Emily Davis" for
a Sri Lankan leasing company would undermine the prototype's credibility
in any evaluation or demo. The approximate ethnic distribution used
(~60% Sinhalese, ~25% Tamil, ~15% Muslim) is a rough demographic
approximation and has **zero impact on scoring** — it affects only the
`name` column.

### Limitation

The name list (~100 first names, ~50 last names) will produce some
repeated name combinations across 1,000 records. In a real PLC portfolio,
duplicate names are common (e.g., multiple "Perera" or "Fernando"
customers), so this is not unrealistic. A production system would use
NIC (National Identity Card) numbers for unique identification, which is
out of scope for this prototype.

---

## 3. CRIB Grade System — A, B, C, D, E, XX

### Decision

We use **five letter grades (A through E) plus XX**, which map to the
Credit Information Bureau of Sri Lanka's (CRIB) five risk tiers.

### How CRIB Actually Works

CRIB assigns every borrower with sufficient credit history:

1. A **numerical score** (250–900), inversely correlated with default
   probability.
2. An **alphanumeric risk grade** structured as 5 tiers × 3 sub-grades:
   - **A1, A2, A3** — Very Low Risk
   - **B1, B2, B3** — Low Risk
   - **C1, C2, C3** — Average Risk
   - **D1, D2, D3** — High Risk
   - **E1, E2, E3** — Very High Risk
3. **"XX"** for borrowers with insufficient data to compute a score.

*(Source: [CRIB Score Report Reference Guide](https://www.crib.lk/images/pdfs/crib-score-reference-guide.pdf))*

### Why We Simplified to 5 Single-Letter Grades

Modelling all 15 sub-grades (A1–E3) would require 15 distinct bins in
the scoring engine, each needing calibrated point values. For a
prototype with synthetic data, the sub-grade granularity does not
meaningfully improve the scoring output — the difference between A1 and
A3 is too fine-grained to demonstrate in a decision-support tool.

Instead, we collapse each tier to its letter: **A** (Very Low Risk),
**B** (Low Risk), **C** (Average Risk), **D** (High Risk),
**E** (Very High Risk), and **XX** (No History). This preserves the
real CRIB risk hierarchy while keeping the scoring engine tractable.

### What We Discarded

An earlier design used grades A through H (8 grades). This was
abandoned because:

- CRIB does not use grades F, G, or H. They do not correspond to any
  real risk tier.
- An evaluator consulting the [CRIB reference guide](https://www.crib.lk/images/pdfs/crib-score-reference-guide.pdf)
  would immediately identify the discrepancy.
- The 8-grade system could not be traced to any authoritative source.

### Score Calibration

| Grade | CRIB Tier | Scorecard Points | Rationale |
|-------|-----------|------------------|-----------|
| A | Very Low Risk | +250 | Pristine credit history. Highest confidence in repayment. |
| B | Low Risk | +150 | Minor, inconsequential anomalies. Generally reliable. |
| C | Average Risk | 0 (neutral) | Moderate irregularities. Neither positive nor negative signal. |
| D | High Risk | -150 | Statistically high probability of default on new facilities. |
| E | Very High Risk | -300 | Existing severe defaults, repossessions, or extreme irregularities. |
| XX | Insufficient Info | -150 | No credit history. Scored as D-equivalent because the system cannot distinguish between a truly new borrower and one avoiding the formal credit system. |

---

## 4. Income Ranges

### Calibration Methodology

Sri Lanka's most recent official household income data is from the 2019
HIES (Household Income and Expenditure Survey, LKR 76,414/month). The
2024/2025 HIES is currently being conducted and results are not yet
available. We therefore use a combination of proxy indicators:

- **National median individual salary**: ~LKR 50,000/month
  *(Source: Remote People labor analytics)*
- **National minimum wage**: LKR 30,000/month
  *(Source: National Minimum Wage of Workers (Amendment) Act, No. 11 of 2025)*
- **Professional services top earners (Colombo)**: ~LKR 300,000/month
  *(Source: labor market analyses)*
- **Per capita income proxy**: ~LKR 96,600/month
  *(Source: Worlddata.info, at ~300 LKR/USD)*

Vehicle leasing customers represent a **biased subset** of the
population — they are significantly wealthier than the national median
because leasing a vehicle worth LKR 7+ million requires substantial
income. The ranges below reflect this selection bias.

| Persona | Monthly Income (LKR) | Rationale |
|---------|---------------------|-----------|
| Prime Salaried | 120,000 – 350,000 | Upper-middle professionals (IT, banking, government executives). Upper bound stays below the ~300K "top earner" threshold with a small buffer. |
| SME Truck Operator | 180,000 – 500,000 | SME operators have higher gross turnover but variable monthly margins. Floor reflects minimum viable income for commercial vehicle installments. |
| Subprime Entrepreneur | 250,000 – 800,000 | "Subprime" denotes **credit quality** (poor CRIB, volatile cash flow), not income level. However, the upper bound was reduced from an earlier 1,200,000 because an individual earning 1.2M/month is unlikely to be subprime — at that income, alternative financing options become available. |
| Strategic Defaulter | 150,000 – 400,000 | Middle-income borrowers with **capacity but lacking willingness** to pay. Income is sufficient; the default pattern is behavioural, not financial. |
| New-to-Credit | 80,000 – 250,000 | Young professionals or first-time borrowers. Floor of 80K reflects junior employees outside Colombo (well above minimum wage but below the leasing industry's typical customer median). |
| Tourism Borrower | 150,000 – 450,000 | Tourism operators with highly seasonal income — peak during Dec-Mar tourist season, low during monsoon. Monthly figures represent an annualised average. |
| Recovering Distressed | 150,000 – 400,000 | Previously distressed borrowers rebuilding. Income may have recovered, but credit history still carries legacy marks. |

### Key Limitation

Exact minimum income thresholds for PLC vehicle lease approval are
**not publicly available**. Sri Lankan NBFIs use dynamic DTI
(Debt-to-Income) and PTI (Payment-to-Income) ratios rather than rigid
income floors. Our income ranges are therefore reverse-engineered from
vehicle prices and typical lease installments.

---

## 5. Vehicle Values

### The Sri Lankan Vehicle Market Distortion

The Sri Lankan automotive market operates under extreme, policy-induced
price distortions. In March 2020, the government imposed a total ban on
vehicle imports to conserve foreign exchange reserves. This ban was
gradually lifted in three stages:

- **October 2024**: Public transport and special-purpose vehicles
- **December 2024**: Commercial and goods transport vehicles
- **February 2025**: Personal-use motor vehicles (cars, vans, SUVs)

*(Source: [The Sunday Times](https://www.sundaytimes.lk/241222/business-times/govt-gradually-lifting-vehicle-import-ban-581116.html))*

During the 5-year import embargo, used vehicle prices **appreciated**
in nominal LKR terms — the opposite of normal depreciation. A Suzuki
Alto (entry-level) that might cost USD 8,000 globally was trading at
LKR 7.3–8.1 million (~USD 24,000–27,000) on local platforms like
ikman.lk.

Our vehicle value ranges reflect this **inflated 2024/2025 reality**:

| Persona | Vehicle Value (LKR) | Vehicle Type | Rationale |
|---------|-------------------|--------------|-----------|
| Prime Salaried | 7.0M – 15.0M | Private | Entry-level (Suzuki Alto ~7.3M) to mid-range sedan (Toyota Vitz ~7.8M, Corolla ~12M+). |
| SME Truck | 10.0M – 25.0M | Commercial | Medium trucks (TATA, Isuzu 4-6 ton) and light commercial vans. |
| Subprime Entrepreneur | 12.0M – 25.0M | Commercial | Heavy commercial vehicles. Upper bound reduced from 30M — luxury territory is incongruent with a subprime credit profile. |
| Strategic Defaulter | 7.0M – 18.0M | Private or Commercial | Mixed fleet, mid-range vehicles. |
| New-to-Credit | 6.0M – 12.0M | Private or Commercial | Cheaper vehicles for first-time buyers. Floor raised from 5M (below any usable vehicle in 2025 SL). |
| Tourism | 7.0M – 16.0M | Private or Commercial | Tour vehicles, hotel shuttles, private cars for tourism operators. |
| Recovering | 7.0M – 18.0M | Private or Commercial | Mixed fleet, typical mid-range. |

### Depreciation Modelling

We apply a **10–25% random depreciation** from the purchase price to
generate the `current_value` in the `market_valuations` table. This is
a simplification. In reality:

- During the import ban (2020–2024), vehicles often **appreciated** in
  nominal terms.
- Post-ban (2025 onwards), the influx of new imports is expected to
  **rapidly deflate** the secondary market.
- Standard international depreciation curves (15–20% in year 1, 10–15%
  thereafter) do not apply to Sri Lanka's distorted market.

For the prototype, the 10–25% range produces vehicles that are worth
less than their purchase price, which is the conservative, safer
assumption for LTV calculations.

---

## 6. Loan-to-Value (LTV) Ratios and Regulatory Compliance

### CBSL LTV Caps

The Central Bank of Sri Lanka mandates strict LTV caps through
**CBSL Act Directions No. 03 of 2025** (effective 8 November 2025):

| Vehicle Category | Maximum LTV |
|-----------------|-------------|
| Motor Cars, SUVs, Vans (incl. hybrid) | 50% |
| Commercial Vehicles | 70% |
| Three-Wheelers | 50% |
| Registered Used Vehicles (>1 year in SL) | 70% |

*(Source: [CBSL Directions](https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/laws/CBSL_Act_Directions_No_3_of_2025_e.pdf))*

### Prototype Simplification

We model two categories: **Private (50%)** and **Commercial (70%)**.
Three-wheelers and used-vehicle sub-categories are excluded from v1.0.
This simplification is valid because:

- PLC's leasing portfolio is dominated by cars, vans, and trucks.
- Three-wheeler and used-vehicle financing require distinct persona
  types and pricing models that are out of scope.
- The two-category model correctly enforces the regulatory caps for the
  vehicle types we do model.

### LTV Per Persona

| Persona | LTV Strategy | Rationale |
|---------|-------------|-----------|
| Prime Salaried | 30–40% | Well below the 50% cap. Low risk, conservative borrowing. |
| SME Truck | 55–68% | Approaching the 70% commercial cap but within compliance. |
| Subprime Entrepreneur | Exactly 70% | At the regulatory limit. Tests the system's compliance gate. |
| Strategic Defaulter | Cap minus 2–6% | Just under the cap — leaves room for market depreciation to push into breach territory during stress testing. |
| New/Tourism/Recovering | Cap minus 5–15% | Moderate LTV with headroom. |

---

## 7. Sector NPL Ratios

### The Data Gap

Granular, sector-level NPL ratios for the NBFI sector are **not
published by CBSL**. The Central Bank publishes industry-wise NPL
breakdowns only for the Licensed Commercial Banking sector (in the
Financial System Stability Review). NBFI sector data is reported only
as an aggregate.

*(Source: [CBSL Financial Stability Review](https://www.cbsl.gov.lk/en/publications/economic-and-financial-reports/financial-system-stability-review))*

### Derivation Methodology

We derive sector-relative NPL ratios using three inputs:

1. **PLC's own sector concentration** (from the 2024/25 Annual Report,
   Risk Management Review):

   | Sector | PLC Concentration (2024/25) |
   |--------|---------------------------|
   | Transport | 31.1% |
   | Manufacturing | 14.1% |
   | Traders/Retail | 10.3% |
   | Construction | 8.8% |
   | Services | 7.4% |
   | Agriculture | 4.5% |
   | Tourism | 2.3% |
   | Others | 19.6% |

2. **CBSL Annual Economic Review 2024** qualitative sector assessments:
   - Manufacturing and Construction: initiating revival, slow recovery
   - Transport and Tourism: strong, sustained recovery
   - Agriculture: robust yields but highest volatility (monsoon-dependent)

3. **Aggregate benchmarks**:
   - NBFI sector NPL: 11.3% (2024), down from 17.8% (2023)
     *(Source: [Fitch Ratings, Oct 2024](https://www.fitchratings.com/research/non-bank-financial-institutions/economic-recovery-drives-sri-lankan-finance-leasing-companies-growth-21-10-2024))*
   - PLC-specific NPL: 5.86% (2024/25), down from 15.84% (2023/24)
     *(Source: PLC Annual Report 2024/25)*

### Assigned Ratios

| Sector Code | Assigned NPL | GDP Outlook | Derivation Basis |
|-------------|-------------|-------------|------------------|
| GOVERNMENT | 2.0% | Positive | Guaranteed income (government salaries), lowest default risk in any economy. |
| EDUCATION | 2.5% | Positive | Stable, often government-funded sector. Low historical volatility. |
| SERVICES | 3.5% | Positive | Professional services (IT, banking, accounting) in Colombo. Salaried, stable cash flows. |
| TRANSPORT | 4.0% | Positive | PLC's largest concentration (31.1%). Strong recovery driven by stabilised fuel prices and tourism-linked logistics demand. Assigned below the 5% "Green" EWI threshold. |
| OTHER | 5.5% | Neutral | Blended category. Assigned at the sector-wide midpoint. |
| MANUFACTURING | 6.0% | Neutral | Revival underway but slower than services/transport. Stabilised raw material costs support moderate recovery. |
| RETAIL | 6.5% | Neutral | Consumer demand recovering but uneven. Informal retail operators carry higher risk. |
| TOURISM | 8.0% | Positive | Recovery trajectory is strong, but the sector carries **seasonal volatility** (peak Dec-Mar, trough during monsoon). Assigned in the Amber EWI zone to demonstrate sectoral stress. |
| AGRICULTURE | 9.5% | Neutral | Highest-volatility sector in Sri Lanka. Intrinsically vulnerable to monsoon failures, fertiliser shortages, and sudden climatic shifts that instantly decimate rural household liquidity. |
| CONSTRUCTION | 11.0% | Negative | Slowest recovery among all sectors. Many infrastructure projects remain paused. Raw material costs and regulatory uncertainty continue to suppress activity. |

### Transparency Note

These ratios are our **best-available estimates**, not measured values.
They are defensible because:

- The **relative ordering** is consistent across all three source types
  (PLC concentration, CBSL economic review, Fitch sectoral assessment).
- The **absolute values** are anchored to PLC's own NPL of 5.86% and
  the NBFI sector average of 11.3%.
- They produce the intended distribution when combined with other
  scoring variables (sector NPL is only 10% of the total score weight).

If sector-specific NBFI NPL data becomes publicly available from CBSL,
these ratios should be updated accordingly.

---

## 8. App Login Frequency

### Data Source Validation

PLC operates a customer-facing mobile app called **"PLC Touch"**,
available on both [Google Play](https://play.google.com/store/apps/details?id=com.plc.mobilebanking)
and the [Apple App Store](https://apps.apple.com/lk/app/plc-touch/id1542564742).

The app provides:
- 360-degree view of savings, loans, leases, and fixed deposits
- Lease and loan rental payments
- Fund transfers (CEFT) and utility bill payments
- ATM card management (lock/unlock/freeze)

*(Source: [PLC Touch — PLC website](https://www.plc.lk/plc-touch/))*

### Scoring Justification

Whether PLC **currently uses** login frequency as a credit risk variable
is not publicly known. However:

1. The PLC Touch infrastructure **inherently possesses** the
   capability to track user telemetry (login timestamps, session
   duration, feature usage).
2. PLC's 2024/25 Annual Report explicitly names a **"customer risk
   rating system"** as a planned enhancement — behavioural metrics like
   app engagement would be a natural component.
3. Academic literature on digital lending consistently identifies
   **digital engagement decay** as an early warning indicator of
   financial distress (borrowers in trouble often disengage from
   financial apps before they miss payments).

We model `app_login_freq` as a **proposed behavioural Early Warning
Indicator** — one that PLC's existing technology can support but may
not yet have implemented in production.

| Persona | Logins/Month | Rationale |
|---------|-------------|-----------|
| Prime Salaried | 10–30 | Active, digitally engaged customer. Uses app for payments and account monitoring. |
| SME Truck | 3–12 | Moderate engagement. May prefer branch visits or manual payments. |
| Subprime | 1–6 | Low engagement. Possible avoidance behaviour or unfamiliarity with digital tools. |
| Strategic Defaulter | 0–3 | Very low. May deliberately avoid the app to reduce institutional contact. |
| New-to-Credit | 4–20 | Wide range — younger borrowers may be highly digital, but some new customers are still learning the platform. |
| Tourism | 5–15 | Moderate. Seasonal usage patterns may align with tourism income cycles. |
| Recovering | 4–12 | Re-engaging with the platform as financial health improves. |

---

## 9. Province Distribution

### Data Source

PLC's 2024/25 Risk Management Review provides an exact **geographic
concentration breakdown** of the lending portfolio:

| Province | PLC Concentration (2024/25) |
|----------|---------------------------|
| Western | 40.1% |
| Eastern | 12.8% |
| North Western | 10.7% |
| Sabaragamuwa | 7.9% |
| Southern | 5.3% |
| Central | 7.2% |
| Northern | 6.1% |
| North Central | 5.1% |
| Uva | 4.8% |

*(Source: PLC Annual Report 2024/25, Risk Management Review,
Geographic Concentration table)*

### Why It Matters

Province is **not used in the scoring formula** (the scorecard has no
province-based bin). However, it serves two purposes:

1. **Portfolio visualisation**: The dashboard can display a geographic
   concentration chart matching PLC's real-world distribution, which
   strengthens demo credibility.
2. **Contextual realism**: An evaluator reviewing individual records
   will see borrowers distributed across Sri Lanka rather than
   clustered in a single province.

Geographic risk (e.g., rural vs. urban default rates, monsoon-affected
agricultural districts) is an important risk dimension in PLC's actual
operations, but modelling it in the scoring engine is out of scope for
v1.0.

---

## 10. Lease Tenure

### Decision

Each lease agreement is assigned a `tenure_months` value drawn from
**{36, 48, 60}** months with approximate weights of 20%, 50%, and 30%
respectively.

### Rationale

The exact average lease tenure at PLC is not publicly available.
Industry data from securitisation prospectuses and NBFI regulatory
filings indicates that standard Sri Lankan vehicle leasing terms range
from **24 to 60 months**, with tenures beyond 60 months being
exceedingly rare due to accelerated physical depreciation in local
conditions.

*(Source: PLC Annual Report 2024/25; industry securitisation data)*

48 months is weighted highest as it represents the most common balance
between affordable monthly payments and acceptable total interest cost.

### Scoring Impact

Tenure is **not currently used in the scoring formula**. However, it is
stored in the database and returned by the API because:

- A borrower 6 months into a 60-month lease has a fundamentally
  different risk profile than one 54 months in.
- This field enables future enhancements such as "months remaining"
  risk adjustments.
- It adds contextual realism for evaluators reviewing individual records.

---

## 11. Net Worth

### Data Source Concern

Net worth is typically **self-declared** on loan application forms and
is difficult for PLC to independently verify. In practice, it includes:
- Property (land and buildings, based on assessed valuations)
- Savings and fixed deposits (verifiable through bank statements)
- Other investments
- Minus declared liabilities

### Modelling Approach

We express net worth as a **multiple of annual income**, varied by
persona:

| Persona | Net Worth Multiple | Rationale |
|---------|-------------------|-----------|
| Prime Salaried | 4–10× | Established professional with accumulated assets. |
| SME Truck | 2–5× | Business assets partially offset by business liabilities. |
| Subprime | 1–3× | Low asset accumulation, possibly over-leveraged. |
| Strategic Defaulter | 1.5–3× | Moderate. May have hidden assets (strategic behaviour). |
| New-to-Credit | 0.5–3× | Wide range. Some young borrowers have family-backed assets; others have minimal savings. |
| Tourism/Recovering | 1.5–5× | Moderate range. |

### Limitation

The precision of these multiples exceeds what PLC would have in
practice. In a real portfolio, net worth figures would cluster around
round numbers and show significant self-reporting bias. For a prototype,
this granularity is acceptable because it exercises the Capital scoring
category's binning logic across its full range.

---

## 12. Liquidity Score

### Definition

The `liquidity_score` field (1–10) on `market_valuations` represents
how easily a repossessed vehicle can be resold on the secondary market.

### Modelling

- **Private vehicles**: random integer 5–8. Private cars (Toyota, Honda,
  Suzuki) have strong secondary market demand in Sri Lanka.
- **Commercial vehicles**: random integer 3–6. Trucks and vans have
  a more specialised buyer pool and longer resale cycles.

### Why Not Hardcoded

An earlier design used fixed values (7 for Private, 5 for Commercial).
This was unrealistic because:

- A Toyota Corolla (high demand) and a luxury BMW (niche market) would
  both receive a 7, despite vastly different resale characteristics.
- The variance (5–8 and 3–6) better exercises the scoring system and
  produces more realistic portfolio diversity.

---

## 13. Persona Distribution

### Portfolio Mix

| Persona | Weight | Target Risk Grade | Purpose |
|---------|--------|------------------|---------|
| Prime Salaried | 30% | Low (Green) | The backbone of a healthy portfolio. Demonstrates that the system correctly identifies safe borrowers. |
| SME Truck | 22% | Low–Medium (Green–Amber) | PLC's largest sector (Transport = 31.1%). Shows the system handles moderate-risk borrowers. |
| Subprime Entrepreneur | 12% | Medium–High (Amber–Red) | Tests the upper risk boundary. LTV at the regulatory cap exercises the compliance gate. |
| Strategic Defaulter | 6% | High (Red) | Tests the system's ability to detect behavioural gaming (day-29 payments with widening trend). |
| New-to-Credit | 10% | Medium (Amber) | Tests how the system handles information absence (Grade XX). Forces reliance on collateral and income. |
| Tourism | 12% | Low–Medium (Green–Amber) | Tests sector-level risk (Tourism NPL = 8.0%). Demonstrates the Conditions scoring category. |
| Recovering | 8% | Medium (Amber) | Tests the DPD trend interpretation (improving pattern: 25→22→18→12→8→5). |

### Target Distribution

The mix is designed to produce approximately:
- **~70% Low Risk** (Green)
- **~20% Medium Risk** (Amber)
- **~10% High Risk** (Red)

This distribution:
- Matches a realistic portfolio (most borrowers are performing)
- Provides enough Red cases to populate the Alert Dashboard
- Creates enough Amber cases for meaningful "early warning" demonstration

---

## 14. Data Update Frequency in Production

Understanding how often each data point would be updated in PLC's real
systems is essential for interpreting the synthetic data correctly.

| Data Point | Source in Production | Update Frequency | Prototype Treatment |
|-----------|---------------------|-----------------|-------------------|
| Monthly income | Loan application form | **Static** (fixed at origination; rarely updated unless refinanced) | Generated once per record |
| Monthly debt obligations | CRIB database + internal records | **Monthly** (via CRIB batch updates at month-end) | Generated once per record |
| CRIB grade | CRIB API/Portal | **Monthly** | Generated once per record |
| DPD (Days Past Due) | Core banking system | **Daily / Real-time** | Generated once; DPD pattern gives 6-month history |
| Vehicle resale value | Valuation panel reports | **Static at origination; updated ad-hoc** upon repossession or restructuring | Depreciated once from purchase price |
| Sector NPL ratio | Risk MIS | **Monthly / Quarterly** | Stored in `sector_reference` table; can be updated independently |
| App login frequency | PLC Touch app analytics | **Real-time / Daily** | Generated once per record |
| Net worth | Loan application form | **Static** (fixed at origination) | Generated once per record |

*(Source: Analysis based on CBSL Finance Business Act Direction No. 02
of 2024 requirements and CRIB reporting procedures)*

---

## 15. What This Data Does Not Model

The following real-world risk factors are deliberately excluded from
the prototype, either because data is unavailable, the modelling
complexity exceeds scope, or they require real system integration:

| Excluded Factor | Reason for Exclusion |
|----------------|---------------------|
| **Guarantor information** | CRIB tracks guaranteed contracts, and guarantor default contagion is a real risk vector. However, modelling guarantor relationships requires a separate entity table and dual-scoring logic that is out of scope. |
| **Restructured/rescheduled status** | Facilities under restructuring carry inherently higher re-default probabilities. PLC's Special Care department handles ~45% of distressed cases through restructuring. Modelling this requires a binary flag and adjusted PD multiplier — deferred to v2.0. |
| **Three-wheeler financing** | PLC actively finances three-wheelers (including electric). However, three-wheeler operators earn primarily in the informal cash economy, making income verification difficult. A dedicated persona would need distinct DTI thresholds and data validation rules. |
| **Seasonal default patterns** | Sri Lankan leasing defaults are cyclical — stress peaks during April/May (Sinhala/Tamil New Year spending) and during failed monsoon seasons in agricultural districts. Modelling this requires time-series data across multiple years, which is out of scope. |
| **Geographic risk weighting** | While `province` is captured, it is not scored. Rural agricultural provinces (North Central, Uva) have structurally different risk profiles from urban Colombo. This would require province-specific NPL overlays. |
| **Electric vehicle premium** | PLC has a first-mover advantage in electric three-wheeler financing. EV LTV caps were historically more permissive (up to 90%) but were equalised in July 2025. EV-specific modelling is deferred. |

---

## Sources

| # | Source | Usage |
|---|--------|-------|
| 1 | PLC Annual Report 2024/25 — [CDN link](https://cdn.cse.lk/cmt/upload_report_file/1103_1749213770885.pdf) | Portfolio size, NPL ratio, sector concentration, geographic concentration, strategic priorities |
| 2 | PLC Risk Management Review 2024/25 — [PLC website](https://www.plc.lk/wp-content/uploads/2025/08/Risk-Management.pdf) | Risk governance, credit risk discussion, NP ratios, stress testing methodology |
| 3 | CRIB Score Report Reference Guide — [CRIB](https://www.crib.lk/images/pdfs/crib-score-reference-guide.pdf) | Score range (250–900), grade tiers (A1–E3 + XX), report structure |
| 4 | CBSL Act Directions No. 03 of 2025 — [CBSL](https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/laws/CBSL_Act_Directions_No_3_of_2025_e.pdf) | LTV caps by vehicle category |
| 5 | Fitch Ratings (Oct 2024) — [Fitch](https://www.fitchratings.com/research/non-bank-financial-institutions/economic-recovery-drives-sri-lankan-finance-leasing-companies-growth-21-10-2024) | NBFI sector NPL: 11.3% (2024) |
| 6 | CBSL Annual Economic Review 2024 — [CBSL](https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/about/presentation_20250516_%20AER_2024_e.pdf) | Sector-level GDP outlook, recovery assessments |
| 7 | National Minimum Wage Act No. 11 of 2025 | Minimum wage = LKR 30,000/month |
| 8 | PLC Touch — [Google Play](https://play.google.com/store/apps/details?id=com.plc.mobilebanking), [PLC website](https://www.plc.lk/plc-touch/) | App existence, feature set |
| 9 | Sri Lankan vehicle market — [ikman.lk](https://ikman.lk), [patpat.lk](https://patpat.lk) | Vehicle prices under import-ban conditions |
| 10 | Vehicle import ban timeline — [Sunday Times](https://www.sundaytimes.lk/241222/business-times/govt-gradually-lifting-vehicle-import-ban-581116.html) | Phased lifting schedule (Oct 2024 – Feb 2025) |
| 11 | CBSL Finance Business Act Direction No. 02 of 2024 — [CBSL](https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/laws/cdg/snbfi_finance_business_act_directions_no_2_of_2024_e.pdf) | Credit risk management framework requirements for NBFIs |
| 12 | Finance Leasing Act No. 56 of 2000 | Lessor ownership rights, repossession provisions |
