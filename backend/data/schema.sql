-- Smart-Risk Sentinel — PostgreSQL schema
-- Owned by Member 1 (Database & Data Layer).
-- Reference: docs/DATA_SCHEMA.md

-- Enable UUID generator (provides gen_random_uuid()).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ---------------------------------------------------------------------------
-- DROP in dependency order (safe to re-run during development)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS risk_scores_log   CASCADE;
DROP TABLE IF EXISTS market_valuations CASCADE;
DROP TABLE IF EXISTS lease_agreements  CASCADE;
DROP TABLE IF EXISTS borrowers         CASCADE;
DROP TABLE IF EXISTS sector_reference  CASCADE;

-- ---------------------------------------------------------------------------
-- sector_reference
-- ---------------------------------------------------------------------------
CREATE TABLE sector_reference (
    sector_code  VARCHAR(20)  PRIMARY KEY,
    sector_name  VARCHAR(100) NOT NULL,
    npl_ratio    NUMERIC(5,4) NOT NULL DEFAULT 0.0,
    gdp_outlook  VARCHAR(20)  NOT NULL DEFAULT 'Neutral'
                              CHECK (gdp_outlook IN ('Positive','Neutral','Negative')),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- borrowers
-- ---------------------------------------------------------------------------
CREATE TABLE borrowers (
    customer_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 VARCHAR(120) NOT NULL,
    age                  INT          NOT NULL CHECK (age BETWEEN 18 AND 100),
    sector_code          VARCHAR(20)  NOT NULL REFERENCES sector_reference(sector_code),
    annual_income        NUMERIC(12,2) NOT NULL DEFAULT 0,
    monthly_income       NUMERIC(12,2) NOT NULL DEFAULT 0,
    monthly_obligations  NUMERIC(12,2) NOT NULL DEFAULT 0,
    crib_grade           VARCHAR(2)   NOT NULL DEFAULT 'XX'
                                       CHECK (crib_grade IN ('A','B','C','D','E','F','G','H','XX')),
    net_worth            NUMERIC(14,2) NOT NULL DEFAULT 0,
    app_login_freq       INT          NOT NULL DEFAULT 0,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_borrowers_sector ON borrowers(sector_code);
CREATE INDEX idx_borrowers_crib   ON borrowers(crib_grade);

-- ---------------------------------------------------------------------------
-- lease_agreements
-- ---------------------------------------------------------------------------
CREATE TABLE lease_agreements (
    agreement_id   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id    UUID         NOT NULL REFERENCES borrowers(customer_id) ON DELETE CASCADE,
    vehicle_type   VARCHAR(20)  NOT NULL CHECK (vehicle_type IN ('Private','Commercial')),
    vehicle_value  NUMERIC(12,2) NOT NULL CHECK (vehicle_value > 0),
    loan_amount    NUMERIC(12,2) NOT NULL CHECK (loan_amount > 0),
    ltv_ratio      NUMERIC(5,4)  NOT NULL CHECK (ltv_ratio > 0 AND ltv_ratio <= 2.0),
    dpd_current    INT          NOT NULL DEFAULT 0 CHECK (dpd_current >= 0),
    dpd_pattern    INT[]        NOT NULL DEFAULT ARRAY[]::INT[],
    start_date     DATE         NOT NULL DEFAULT CURRENT_DATE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_lease_customer ON lease_agreements(customer_id);
CREATE INDEX idx_lease_ltv      ON lease_agreements(ltv_ratio);

-- ---------------------------------------------------------------------------
-- market_valuations
-- ---------------------------------------------------------------------------
CREATE TABLE market_valuations (
    valuation_id    UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    agreement_id    UUID         NOT NULL REFERENCES lease_agreements(agreement_id) ON DELETE CASCADE,
    current_value   NUMERIC(12,2) NOT NULL CHECK (current_value >= 0),
    valuation_date  DATE         NOT NULL DEFAULT CURRENT_DATE,
    liquidity_score INT          NOT NULL DEFAULT 5
                                  CHECK (liquidity_score BETWEEN 1 AND 10)
);

CREATE INDEX idx_valuation_agreement ON market_valuations(agreement_id);

-- ---------------------------------------------------------------------------
-- risk_scores_log
-- ---------------------------------------------------------------------------
CREATE TABLE risk_scores_log (
    log_id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id       UUID         NOT NULL REFERENCES borrowers(customer_id) ON DELETE CASCADE,
    score             INT          NOT NULL CHECK (score BETWEEN 0 AND 1000),
    grade             VARCHAR(10)  NOT NULL CHECK (grade IN ('Low','Medium','High')),
    compliance_breach BOOLEAN      NOT NULL DEFAULT FALSE,
    calculated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_scores_customer ON risk_scores_log(customer_id, calculated_at DESC);

-- ---------------------------------------------------------------------------
-- Initial sector reference data
-- (NPL ratios and outlook are illustrative; tune via seed_data.py if needed)
-- ---------------------------------------------------------------------------
INSERT INTO sector_reference (sector_code, sector_name, npl_ratio, gdp_outlook) VALUES
    ('TRANSPORT',   'Transport & Logistics',      0.045, 'Neutral'),
    ('TOURISM',     'Tourism & Hospitality',      0.115, 'Positive'),
    ('AGRICULTURE', 'Agriculture',                0.082, 'Neutral'),
    ('CONSTRUCTION','Construction',               0.135, 'Negative'),
    ('RETAIL',      'Retail Trade',               0.068, 'Neutral'),
    ('SERVICES',    'Professional Services',      0.038, 'Positive'),
    ('MANUFACTURING','Manufacturing',             0.072, 'Neutral'),
    ('EDUCATION',   'Education',                  0.029, 'Positive'),
    ('GOVERNMENT',  'Government / Public Sector', 0.022, 'Positive'),
    ('OTHER',       'Other',                      0.055, 'Neutral')
ON CONFLICT (sector_code) DO NOTHING;
