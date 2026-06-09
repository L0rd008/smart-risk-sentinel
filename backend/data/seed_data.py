"""Synthetic portfolio seed script — Smart-Risk Sentinel.

Owned by Member 1 (Database & Data Layer). Generates ~1,000 borrowers
across 7 persona types, with at least 10% obvious High Risk and 10%
obvious Low Risk.

Run from the repo root with the venv active:
    python backend/data/seed_data.py

Requires: schema.sql already loaded, .env populated, PostgreSQL running.

Data Methodology
-----------------
All synthetic ranges are calibrated against the following sources:

1. PLC Annual Report 2024/25 — sector concentration, NPL trajectory,
   portfolio size (LKR 157 Bn), NPL ratio (5.86%).
   Source: cdn.cse.lk/cmt/upload_report_file/1103_1749213770885.pdf

2. CRIB Score Report Reference Guide — grade tiers A1–E3 + XX,
   score range 250–900.
   Source: crib.lk/images/pdfs/crib-score-reference-guide.pdf

3. CBSL Act Directions No. 03 of 2025 — LTV caps for motor vehicles.
   Source: cbsl.gov.lk → CBSL_Act_Directions_No_3_of_2025_e.pdf

4. Sri Lankan vehicle market data (ikman.lk, patpat.lk) — vehicle
   prices under import-ban-inflated conditions (2024/2025).

5. DCS HIES 2019 + proxy estimates — national median salary ~LKR 50,000;
   minimum wage LKR 30,000 (Act No. 11 of 2025); professional
   services top earners ~LKR 300,000.

6. Fitch Ratings (Oct 2024) — NBFI sector NPL 11.3% (2024),
   down from 17.8% (2023).

See docs/SYNTHETIC_DATA_METHODOLOGY.md for the full decision rationale.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import Any

from faker import Faker

# Allow running this file directly: add backend/ to sys.path.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db_connect import get_connection, dict_cursor  # noqa: E402


# Deterministic seeding for reproducibility.
fake = Faker()
Faker.seed(42)
random.seed(42)


# ---------------------------------------------------------------------------
# Sri Lankan name generator
# ---------------------------------------------------------------------------
# PLC serves a multi-ethnic Sri Lankan customer base. Using Faker's default
# locale would produce Western names ("John Smith") which undermines demo
# realism. We use a curated list of common Sinhalese, Tamil, and Muslim
# names proportionally. Ethnic distribution is approximate and used solely
# for name realism — it has zero impact on scoring.

SINHALESE_FIRST = [
    "Amal", "Anura", "Asanka", "Bandara", "Chaminda", "Chandana",
    "Charith", "Dasun", "Dinesh", "Dulshan", "Gayan", "Harsha",
    "Heshan", "Indika", "Janaka", "Kamal", "Kasun", "Kumara",
    "Lakmal", "Lasith", "Mahela", "Malintha", "Namal", "Nimal",
    "Nuwan", "Pasan", "Pradeep", "Prasad", "Ravindra", "Ruwan",
    "Sampath", "Saman", "Sanjeewa", "Sarath", "Suresh", "Tharindu",
    "Thisara", "Upul", "Wasantha", "Yasith",
    "Ama", "Chamari", "Chathurika", "Dilhani", "Gayani", "Hashini",
    "Himali", "Iresha", "Kumari", "Malini", "Nadeesha", "Nilmini",
    "Pavithra", "Sachini", "Sanduni", "Sewwandi", "Shanika", "Tharushi",
]

SINHALESE_LAST = [
    "Perera", "Fernando", "Silva", "De Silva", "Jayawardena",
    "Wickramasinghe", "Bandara", "Rajapaksa", "Dissanayake",
    "Gunawardena", "Senanayake", "Kumarasinghe", "Senevirathne",
    "Karunaratne", "Rathnayake", "Herath", "Jayasuriya",
    "Wijesinghe", "Liyanage", "Abeysinghe", "Mendis",
    "Amarasinghe", "Weerasinghe", "Pathirana", "Gamage",
]

TAMIL_FIRST = [
    "Arun", "Bala", "Chandran", "Deepan", "Ganesh", "Hari",
    "Karthik", "Kumar", "Mohan", "Nishanthan", "Prasanna",
    "Rajan", "Ramesh", "Santhosh", "Selvan", "Subramaniam",
    "Thilak", "Vimal", "Yogeswaran",
    "Anitha", "Devika", "Kavitha", "Lakshmi", "Meena", "Nithya",
    "Priya", "Saranya", "Thulasi", "Vasuki",
]

TAMIL_LAST = [
    "Rajaratnam", "Nadarajah", "Sivakumar", "Chandrasekaran",
    "Balasingam", "Thambiah", "Kanagasabai", "Gnanasekaran",
    "Velupillai", "Yoganathan", "Krishnapillai", "Murugesu",
    "Packiyanathan", "Sathananthan",
]

MUSLIM_FIRST = [
    "Abdul", "Ahmed", "Anwar", "Faisal", "Farhan", "Haris",
    "Imran", "Ismail", "Junaid", "Kasim", "Mohamed", "Mushtaq",
    "Naseer", "Rizwan", "Sajith", "Shahul", "Shafiq", "Yusuf",
    "Amina", "Fathima", "Hafsa", "Mariam", "Nusrath", "Safiya",
    "Zainab",
]

MUSLIM_LAST = [
    "Hameed", "Hussain", "Cassim", "Mohideen", "Marikar",
    "Laffir", "Naufer", "Saleem", "Razik", "Haniffa",
    "Jabbar", "Nizar",
]


def _sri_lankan_name(used_names: set[str] | None = None) -> str:
    """Generate a unique, realistic Sri Lankan name.

    Approximate ethnic proportions for PLC's customer base:
    ~60% Sinhalese, ~25% Tamil, ~15% Muslim.

    If `used_names` is provided, the function retries until it finds a
    name not already in the set, then adds the new name to the set before
    returning. With ~2,142 possible combinations and 1,000 records, the
    average retry rate is negligible (<0.5 retries by the 900th record).
    """
    for _ in range(500):  # safety cap; pool is 2× record count
        r = random.random()
        if r < 0.60:
            name = f"{random.choice(SINHALESE_FIRST)} {random.choice(SINHALESE_LAST)}"
        elif r < 0.85:
            name = f"{random.choice(TAMIL_FIRST)} {random.choice(TAMIL_LAST)}"
        else:
            name = f"{random.choice(MUSLIM_FIRST)} {random.choice(MUSLIM_LAST)}"

        if used_names is None or name not in used_names:
            if used_names is not None:
                used_names.add(name)
            return name

    raise RuntimeError(
        f"Could not generate a unique name after 500 retries. "
        f"Pool size ~2,142 vs {len(used_names or set())} used names."
    )


# ---------------------------------------------------------------------------
# Province distribution — matches PLC's 2024/25 Annual Report
# ---------------------------------------------------------------------------
# Source: PLC Risk Management Review 2024/25, Geographic Concentration table.
# We use PLC's actual provincial lending concentration as weights.

PROVINCE_WEIGHTS: list[tuple[str, float]] = [
    ("Western",       0.401),
    ("Eastern",       0.128),
    ("North Western", 0.107),
    ("Sabaragamuwa",  0.079),
    ("Central",       0.072),
    ("Services",      0.074),   # mapped to "Southern" below
    ("Northern",      0.061),
    ("North Central", 0.051),
    ("Uva",           0.048),
]

# Corrected: The "Services" row in PLC's data is actually Southern Province.
PROVINCE_WEIGHTS = [
    ("Western",       0.401),
    ("Eastern",       0.128),
    ("North Western", 0.107),
    ("Sabaragamuwa",  0.079),
    ("Southern",      0.074),
    ("Central",       0.072),
    ("Northern",      0.061),
    ("North Central", 0.051),
    ("Uva",           0.048),
]


def _pick_province() -> str:
    """Weighted random province selection matching PLC's concentration."""
    r = random.random()
    cumulative = 0.0
    for province, weight in PROVINCE_WEIGHTS:
        cumulative += weight
        if r <= cumulative:
            return province
    return "Western"


# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------
# Each persona type models a distinct borrower archetype observed in Sri
# Lankan vehicle leasing. Income ranges, vehicle values, and CRIB grades
# are calibrated against the data sources listed in the module docstring.
# See docs/SYNTHETIC_DATA_METHODOLOGY.md for the full rationale.

PERSONA_PRIME_SALARIED      = "prime_salaried"
PERSONA_SME_TRUCK           = "sme_truck"
PERSONA_SUBPRIME_ENTRE      = "subprime_entrepreneur"
PERSONA_STRATEGIC_DEFAULTER = "strategic_defaulter"
PERSONA_NEW_TO_CREDIT       = "new_to_credit"
PERSONA_TOURISM             = "tourism_borrower"
PERSONA_RECOVERING          = "recovering_distressed"

# Persona mix (weights sum to 1.0). Expected distribution with corrected
# thresholds (Low >=620, High <420): approx. 20–25% Low (Green),
# 55–65% Medium (Amber), 15–20% High (Red) — calibrated to represent a
# healthy but imperfect NBFI portfolio consistent with PLC's reported
# NPL structure (sector NPL ~5.86%, NBFI sector ~11.3% as of 2024/25).
PERSONA_MIX: list[tuple[str, float]] = [
    (PERSONA_PRIME_SALARIED,      0.30),
    (PERSONA_SME_TRUCK,           0.22),
    (PERSONA_SUBPRIME_ENTRE,      0.12),
    (PERSONA_STRATEGIC_DEFAULTER, 0.06),
    (PERSONA_NEW_TO_CREDIT,       0.10),
    (PERSONA_TOURISM,             0.12),
    (PERSONA_RECOVERING,          0.08),
]

SECTORS = [
    "TRANSPORT", "TOURISM", "AGRICULTURE", "CONSTRUCTION", "RETAIL",
    "SERVICES", "MANUFACTURING", "EDUCATION", "GOVERNMENT", "OTHER",
]


# ---------------------------------------------------------------------------
# Persona generation
# ---------------------------------------------------------------------------

def generate_persona(persona_type: str, used_names: set[str] | None = None) -> dict[str, Any]:
    """Return a fully-populated synthetic borrower + lease dict.

    Output keys are organised so the caller can split into borrower and
    lease rows for insertion. Every numeric range is sourced — see the
    inline comments and docs/SYNTHETIC_DATA_METHODOLOGY.md.

    If `used_names` is provided, the generated name is guaranteed to be
    unique across the entire seeding run.
    """
    name = _sri_lankan_name(used_names)
    age = random.randint(25, 65)
    province = _pick_province()

    if persona_type == PERSONA_PRIME_SALARIED:
        # ── Sector: Stable, low-NPL sectors (Services, Government, Education)
        sector = random.choice(["SERVICES", "GOVERNMENT", "EDUCATION"])

        # ── Income: Upper-middle to high-income professionals.
        # National median salary ~LKR 50K; professional services top
        # earners reach ~LKR 300K. Vehicle lessees are above median.
        # Range: 120K–350K LKR/month.
        monthly_income = random.randint(120_000, 350_000)
        monthly_oblig = int(monthly_income * random.uniform(0.10, 0.25))

        # ── CRIB: Excellent credit history. A = Very Low Risk (CRIB tiers).
        crib = random.choice(["A", "A", "A", "B"])

        # ── Vehicle: Private car. Entry-level Suzuki Alto starts at ~7.3M;
        # mid-range used sedans (Toyota Vitz/Corolla) reach ~12-15M.
        vehicle_type = "Private"
        vehicle_value = random.randint(7_000_000, 15_000_000)
        loan_amount = int(vehicle_value * random.uniform(0.30, 0.40))

        # ── DPD: Near-perfect payment behaviour.
        dpd_current = random.choice([0, 0, 0, 1, 2])
        dpd_pattern = [random.choice([0, 0, 0, 1]) for _ in range(6)]

        # ── Net worth: Established professional, 4-10x annual income.
        net_worth = int(monthly_income * 12 * random.uniform(4, 10))

        # ── App: Active PLC Touch user, regular engagement.
        app_logins = random.randint(10, 30)

        # ── Tenure: Standard lease terms.
        tenure_months = random.choice([36, 48, 48, 60])

    elif persona_type == PERSONA_SME_TRUCK:
        # ── Sector: Transport, retail, manufacturing — PLC's largest
        # concentration (Transport alone = 31.1% of portfolio).
        sector = random.choice(["TRANSPORT", "RETAIL", "MANUFACTURING"])

        # ── Income: SME operators with higher gross turnover but variable
        # margins. Three-wheeler operators earn ~LKR 50-80K (informal);
        # truck/van operators earn more but with volatility.
        monthly_income = random.randint(180_000, 500_000)
        monthly_oblig = int(monthly_income * random.uniform(0.30, 0.45))

        # ── CRIB: Low to Average risk — B or C grade.
        crib = random.choice(["B", "C", "C"])

        # ── Vehicle: Commercial truck/van. TATA/Isuzu medium trucks
        # range 10M–25M in the import-ban-inflated market.
        vehicle_type = "Commercial"
        vehicle_value = random.randint(10_000_000, 25_000_000)
        loan_amount = int(vehicle_value * random.uniform(0.55, 0.68))

        # ── DPD: Occasional minor delays, typical for SMEs with
        # irregular cash flow cycles.
        dpd_current = random.choice([0, 2, 5, 7])
        dpd_pattern = [random.choice([0, 2, 5, 8]) for _ in range(6)]

        # ── Net worth: Moderate, 2-5x annual income.
        net_worth = int(monthly_income * 12 * random.uniform(2, 5))
        app_logins = random.randint(3, 12)
        tenure_months = random.choice([36, 48, 48, 60, 60])

    elif persona_type == PERSONA_SUBPRIME_ENTRE:
        # ── Sector: High-risk, cyclical sectors.
        sector = random.choice(["CONSTRUCTION", "TOURISM", "OTHER"])

        # ── Income: Entrepreneurs with volatile, lumpy revenue.
        # "Subprime" refers to credit quality, NOT income level — however
        # upper bound capped at 800K (not 1.2M) because extremely high
        # earners are unlikely to be subprime.
        monthly_income = random.randint(250_000, 800_000)
        monthly_oblig = int(monthly_income * random.uniform(0.45, 0.65))

        # ── CRIB: Average to High risk — C, D, or E grade.
        crib = random.choice(["C", "D", "D", "E"])

        # ── Vehicle: Commercial, large — often construction equipment
        # or heavy trucks. Upper bound reduced from 30M to 25M (30M
        # approaches luxury territory, incongruent with subprime profile).
        vehicle_type = "Commercial"
        vehicle_value = random.randint(12_000_000, 25_000_000)
        loan_amount = int(vehicle_value * 0.70)  # exactly at CBSL cap

        # ── DPD: Significant delays, hallmark of stressed borrowers.
        dpd_current = random.choice([5, 12, 18, 25])
        dpd_pattern = [random.choice([3, 10, 15, 22]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(1, 3))
        app_logins = random.randint(1, 6)
        tenure_months = random.choice([48, 48, 60, 60])

    elif persona_type == PERSONA_STRATEGIC_DEFAULTER:
        # ── A borrower who systematically games the 30-day DPD trigger.
        # Pays on day 28-29 to avoid NPL classification, but shows a
        # widening trend. Common in SL's leasing sector.
        sector = random.choice(["RETAIL", "OTHER", "MANUFACTURING"])

        # ── Income: Middle-income, has capacity but lacks willingness.
        monthly_income = random.randint(150_000, 400_000)
        monthly_oblig = int(monthly_income * random.uniform(0.35, 0.50))

        # ── CRIB: Average risk — the strategic behaviour hasn't yet
        # triggered a severe CRIB downgrade.
        crib = random.choice(["C", "D"])

        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(7_000_000, 18_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.02, 0.06)))

        # ── DPD: The signature pattern — consistently near but below 30.
        dpd_current = random.choice([26, 28, 29, 30])
        dpd_pattern = [12, 18, 22, 25, 27, 29]  # widening trend

        net_worth = int(monthly_income * 12 * random.uniform(1.5, 3))
        app_logins = random.randint(0, 3)
        tenure_months = random.choice([36, 48, 48, 60])

    elif persona_type == PERSONA_NEW_TO_CREDIT:
        # ── No CRIB history (Grade XX = "Insufficient Information").
        # Often young professionals or first-time borrowers.
        # System must rely on collateral + income rather than history.
        sector = random.choice(SECTORS)

        # ── Income: Lowered floor to 80K — reflects young professionals
        # or junior employees outside Colombo. National min wage = 30K.
        monthly_income = random.randint(80_000, 250_000)
        monthly_oblig = int(monthly_income * random.uniform(0.15, 0.35))
        crib = "XX"

        # ── Vehicle: Cheaper vehicles for first-time buyers.
        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(6_000_000, 12_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.05, 0.10)))

        dpd_current = random.choice([0, 0, 1])
        dpd_pattern = [random.choice([0, 0, 1, 2]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(0.5, 3))
        app_logins = random.randint(4, 20)
        tenure_months = random.choice([36, 48, 48, 60])

    elif persona_type == PERSONA_TOURISM:
        # ── Tourism sector: CRIB Sri Lanka data shows recovery in tourism
        # post-2022 crisis, but the sector carries elevated systemic risk
        # due to seasonal volatility. PLC's tourism concentration is only
        # 2.3%, but the sector NPL is above average.
        sector = "TOURISM"

        # ── Income: Tourist operators, hotel shuttle services, etc.
        # Seasonal — high in Dec-Mar (peak season), low in monsoon.
        monthly_income = random.randint(150_000, 450_000)
        monthly_oblig = int(monthly_income * random.uniform(0.25, 0.40))

        # ── CRIB: Low to Average risk — B or C.
        crib = random.choice(["B", "C"])

        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(7_000_000, 16_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.05, 0.15)))

        dpd_current = random.choice([0, 2, 5])
        dpd_pattern = [random.choice([0, 2, 5, 8]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(2, 5))
        app_logins = random.randint(5, 15)
        tenure_months = random.choice([36, 48, 48, 60])

    elif persona_type == PERSONA_RECOVERING:
        # ── Previously High Risk, now improving. DPD pattern shows
        # a clear downward trajectory — the borrower is rebuilding.
        # Common after PLC's aggressive out-of-court restructuring
        # efforts (referenced in the 2024/25 Annual Report).
        sector = random.choice(SECTORS)

        monthly_income = random.randint(150_000, 400_000)
        monthly_oblig = int(monthly_income * random.uniform(0.25, 0.40))

        # ── CRIB: Average to High risk — legacy of past distress.
        crib = random.choice(["C", "D"])

        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(7_000_000, 18_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.05, 0.12)))

        dpd_current = random.choice([3, 5, 7])
        # Improving trend: high in the past, low recently.
        dpd_pattern = [25, 22, 18, 12, 8, 5]

        net_worth = int(monthly_income * 12 * random.uniform(1.5, 3.5))
        app_logins = random.randint(4, 12)
        tenure_months = random.choice([48, 48, 60, 60])

    else:
        raise ValueError(f"unknown persona_type: {persona_type}")

    ltv_ratio = round(loan_amount / vehicle_value, 4)

    return {
        # borrower row
        "name": name,
        "age": age,
        "sector_code": sector,
        "annual_income": monthly_income * 12,
        "monthly_income": monthly_income,
        "monthly_obligations": monthly_oblig,
        "crib_grade": crib,
        "net_worth": net_worth,
        "app_login_freq": app_logins,
        "province": province,
        # lease row
        "vehicle_type": vehicle_type,
        "vehicle_value": vehicle_value,
        "loan_amount": loan_amount,
        "ltv_ratio": ltv_ratio,
        "dpd_current": dpd_current,
        "dpd_pattern": dpd_pattern,
        "tenure_months": tenure_months,
    }


def _weighted_persona_pick() -> str:
    r = random.random()
    cumulative = 0.0
    for persona, weight in PERSONA_MIX:
        cumulative += weight
        if r <= cumulative:
            return persona
    return PERSONA_MIX[-1][0]


# ---------------------------------------------------------------------------
# Insert helpers
# ---------------------------------------------------------------------------

INSERT_BORROWER_SQL = """
    INSERT INTO borrowers (
        name, age, sector_code, annual_income, monthly_income,
        monthly_obligations, crib_grade, net_worth, app_login_freq,
        province
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING customer_id
"""

INSERT_LEASE_SQL = """
    INSERT INTO lease_agreements (
        customer_id, vehicle_type, vehicle_value, loan_amount,
        ltv_ratio, dpd_current, dpd_pattern, tenure_months
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING agreement_id
"""

INSERT_VALUATION_SQL = """
    INSERT INTO market_valuations (
        agreement_id, current_value, liquidity_score
    ) VALUES (%s, %s, %s)
"""


def insert_record(cur, record: dict[str, Any]) -> None:
    """Insert one borrower + lease + valuation into the database."""
    cur.execute(INSERT_BORROWER_SQL, (
        record["name"],
        record["age"],
        record["sector_code"],
        record["annual_income"],
        record["monthly_income"],
        record["monthly_obligations"],
        record["crib_grade"],
        record["net_worth"],
        record["app_login_freq"],
        record["province"],
    ))
    customer_id = cur.fetchone()["customer_id"]

    cur.execute(INSERT_LEASE_SQL, (
        customer_id,
        record["vehicle_type"],
        record["vehicle_value"],
        record["loan_amount"],
        record["ltv_ratio"],
        record["dpd_current"],
        record["dpd_pattern"],
        record["tenure_months"],
    ))
    agreement_id = cur.fetchone()["agreement_id"]

    # ── Market valuation: depreciate by 10-25% from purchase price.
    # Standard depreciation models don't apply perfectly to SL's
    # import-ban-inflated market (vehicles sometimes appreciated in
    # nominal LKR), but for the prototype this approximation is
    # acceptable for vehicles originated in 2024/2025.
    depreciation = random.uniform(0.10, 0.25)
    current_value = int(record["vehicle_value"] * (1 - depreciation))

    # ── Liquidity score: Private vehicles resell more easily than
    # commercial vehicles in Sri Lanka. Added variance within each
    # category (was previously hardcoded to 7 and 5).
    if record["vehicle_type"] == "Private":
        liquidity = random.randint(5, 8)
    else:
        liquidity = random.randint(3, 6)

    cur.execute(INSERT_VALUATION_SQL, (agreement_id, current_value, liquidity))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(n_records: int = 1000) -> None:
    print(f"Seeding {n_records} synthetic borrowers...")

    used_names: set[str] = set()

    with get_connection() as conn, dict_cursor(conn) as cur:
        for i in range(n_records):
            persona = _weighted_persona_pick()
            record = generate_persona(persona, used_names)
            insert_record(cur, record)

            if (i + 1) % 100 == 0:
                print(f"  ... {i + 1} / {n_records}")

    print(f"Done. Inserted {n_records} borrowers + leases + valuations.")
    print(f"  Unique names generated: {len(used_names)}")


if __name__ == "__main__":
    count = int(os.getenv("SEED_COUNT", "1000"))
    main(count)
