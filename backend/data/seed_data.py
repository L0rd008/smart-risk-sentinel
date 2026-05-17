"""Synthetic portfolio seed script.

Owned by Member 1 (Database & Data Layer). Generates ~1,000 borrowers
across the 7 persona types defined in docs/ROLES.md, with at least 10%
obvious High Risk and 10% obvious Low Risk.

Run from the repo root with the venv active:
    python backend/data/seed_data.py

Requires: schema.sql already loaded, .env populated, PostgreSQL running.
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import Any

from faker import Faker

# Allow running this file directly: add backend/ to sys.path so `app...` imports work.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db_connect import get_connection, dict_cursor  # noqa: E402


fake = Faker()
Faker.seed(42)
random.seed(42)


# ---------------------------------------------------------------------------
# Persona definitions — see docs/ROLES.md Member 1 section
# ---------------------------------------------------------------------------

PERSONA_PRIME_SALARIED      = "prime_salaried"
PERSONA_SME_TRUCK           = "sme_truck"
PERSONA_SUBPRIME_ENTRE      = "subprime_entrepreneur"
PERSONA_STRATEGIC_DEFAULTER = "strategic_defaulter"
PERSONA_NEW_TO_CREDIT       = "new_to_credit"
PERSONA_TOURISM             = "tourism_borrower"
PERSONA_RECOVERING          = "recovering_distressed"

# Persona mix (weights must sum to 1.0). Skews towards Green/Amber to look
# realistic, with enough Red examples to populate the AlertDashboard.
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

def generate_persona(persona_type: str) -> dict[str, Any]:
    """Return a fully-populated synthetic borrower + lease dict.

    Output keys are organised so the caller can split into borrower and
    lease rows for insertion.
    """
    name = fake.name()
    age = random.randint(25, 65)

    if persona_type == PERSONA_PRIME_SALARIED:
        sector = random.choice(["SERVICES", "GOVERNMENT", "EDUCATION"])
        monthly_income = random.randint(180_000, 450_000)
        monthly_oblig = int(monthly_income * random.uniform(0.10, 0.25))
        crib = random.choice(["A", "A", "A", "B"])
        vehicle_type = "Private"
        vehicle_value = random.randint(6_500_000, 14_000_000)
        loan_amount = int(vehicle_value * random.uniform(0.30, 0.40))
        dpd_current = random.choice([0, 0, 0, 1, 2])
        dpd_pattern = [random.choice([0, 0, 0, 1]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(4, 10))
        app_logins = random.randint(10, 30)

    elif persona_type == PERSONA_SME_TRUCK:
        sector = random.choice(["TRANSPORT", "RETAIL", "MANUFACTURING"])
        monthly_income = random.randint(250_000, 600_000)
        monthly_oblig = int(monthly_income * random.uniform(0.30, 0.45))
        crib = random.choice(["B", "C", "C"])
        vehicle_type = "Commercial"
        vehicle_value = random.randint(8_000_000, 22_000_000)
        loan_amount = int(vehicle_value * random.uniform(0.55, 0.68))
        dpd_current = random.choice([0, 2, 5, 7])
        dpd_pattern = [random.choice([0, 2, 5, 8]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(2, 5))
        app_logins = random.randint(3, 12)

    elif persona_type == PERSONA_SUBPRIME_ENTRE:
        sector = random.choice(["CONSTRUCTION", "TOURISM", "OTHER"])
        monthly_income = random.randint(400_000, 1_200_000)
        monthly_oblig = int(monthly_income * random.uniform(0.45, 0.65))
        crib = random.choice(["C", "D", "D", "E"])
        vehicle_type = "Commercial"
        vehicle_value = random.randint(12_000_000, 30_000_000)
        loan_amount = int(vehicle_value * 0.70)  # exactly at cap
        dpd_current = random.choice([5, 12, 18, 25])
        dpd_pattern = [random.choice([3, 10, 15, 22]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(1, 3))
        app_logins = random.randint(1, 6)

    elif persona_type == PERSONA_STRATEGIC_DEFAULTER:
        sector = random.choice(["RETAIL", "OTHER", "MANUFACTURING"])
        monthly_income = random.randint(220_000, 500_000)
        monthly_oblig = int(monthly_income * random.uniform(0.35, 0.50))
        crib = random.choice(["C", "D"])
        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(7_000_000, 18_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.02, 0.06)))
        dpd_current = random.choice([26, 28, 29, 30])
        dpd_pattern = [c for c in [12, 18, 22, 25, 27, 29]]  # widening
        net_worth = int(monthly_income * 12 * random.uniform(1.5, 3))
        app_logins = random.randint(0, 3)

    elif persona_type == PERSONA_NEW_TO_CREDIT:
        sector = random.choice(SECTORS)
        monthly_income = random.randint(150_000, 400_000)
        monthly_oblig = int(monthly_income * random.uniform(0.15, 0.35))
        crib = "XX"
        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(5_000_000, 12_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.05, 0.10)))
        dpd_current = random.choice([0, 0, 1])
        dpd_pattern = [random.choice([0, 0, 1, 2]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(0.5, 3))
        app_logins = random.randint(4, 20)

    elif persona_type == PERSONA_TOURISM:
        sector = "TOURISM"
        monthly_income = random.randint(200_000, 550_000)
        monthly_oblig = int(monthly_income * random.uniform(0.25, 0.40))
        crib = random.choice(["B", "C"])
        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(6_000_000, 16_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.05, 0.15)))
        dpd_current = random.choice([0, 2, 5])
        dpd_pattern = [random.choice([0, 2, 5, 8]) for _ in range(6)]
        net_worth = int(monthly_income * 12 * random.uniform(2, 5))
        app_logins = random.randint(5, 15)

    elif persona_type == PERSONA_RECOVERING:
        sector = random.choice(SECTORS)
        monthly_income = random.randint(220_000, 550_000)
        monthly_oblig = int(monthly_income * random.uniform(0.25, 0.40))
        crib = random.choice(["C", "D"])
        vehicle_type = random.choice(["Private", "Commercial"])
        vehicle_value = random.randint(7_000_000, 18_000_000)
        cap = 0.50 if vehicle_type == "Private" else 0.70
        loan_amount = int(vehicle_value * (cap - random.uniform(0.05, 0.12)))
        dpd_current = random.choice([3, 5, 7])
        # improving trend: high in the past, low recently
        dpd_pattern = [25, 22, 18, 12, 8, 5]
        net_worth = int(monthly_income * 12 * random.uniform(1.5, 3.5))
        app_logins = random.randint(4, 12)

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
        # lease row
        "vehicle_type": vehicle_type,
        "vehicle_value": vehicle_value,
        "loan_amount": loan_amount,
        "ltv_ratio": ltv_ratio,
        "dpd_current": dpd_current,
        "dpd_pattern": dpd_pattern,
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
        monthly_obligations, crib_grade, net_worth, app_login_freq
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING customer_id
"""

INSERT_LEASE_SQL = """
    INSERT INTO lease_agreements (
        customer_id, vehicle_type, vehicle_value, loan_amount,
        ltv_ratio, dpd_current, dpd_pattern
    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
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
    ))
    agreement_id = cur.fetchone()["agreement_id"]

    # Current resale value: depreciate by 10–25% for realism.
    depreciation = random.uniform(0.10, 0.25)
    current_value = int(record["vehicle_value"] * (1 - depreciation))
    liquidity = 7 if record["vehicle_type"] == "Private" else 5
    cur.execute(INSERT_VALUATION_SQL, (agreement_id, current_value, liquidity))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(n_records: int = 1000) -> None:
    print(f"Seeding {n_records} synthetic borrowers...")

    with get_connection() as conn, dict_cursor(conn) as cur:
        for i in range(n_records):
            persona = _weighted_persona_pick()
            record = generate_persona(persona)
            insert_record(cur, record)

            if (i + 1) % 100 == 0:
                print(f"  ... {i + 1} / {n_records}")

    print(f"Done. Inserted {n_records} borrowers + leases + valuations.")


if __name__ == "__main__":
    count = int(os.getenv("SEED_COUNT", "1000"))
    main(count)
