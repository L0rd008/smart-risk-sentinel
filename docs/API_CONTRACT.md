# API Contract — Smart-Risk Sentinel

**Base URL:** `http://localhost:<FLASK_PORT>/api` (`FLASK_PORT` defaults to `5000`)
**Version:** 1.0 (FROZEN at project start)

> This document is the immutable bridge between the React frontend and the
> Flask backend. No team member may change response shapes without a full
> team consensus, because doing so silently breaks the other side. If a
> change is genuinely needed, raise it in the standup, update this file,
> bump the version, and notify everyone before merging.

All endpoints return JSON with `Content-Type: application/json`.
All datetime fields are ISO 8601 strings (e.g. `"2026-05-18T09:30:00Z"`).
All monetary amounts are in Sri Lankan Rupees (LKR) unless otherwise noted.

---

## GET /api/health

**Purpose:** Health check — used by the frontend to confirm the API is reachable
and by the integration tests as a readiness probe.

**Request:** none

**Response:**
```json
{
  "status": "ok",
  "version": "1.0"
}
```

---

## GET /api/borrowers

**Purpose:** List all borrowers (summary only) for the dashboard list view.

**Request:** none

**Response:**
```json
{
  "borrowers": [
    {
      "customer_id": "string (UUID)",
      "name": "string",
      "risk_grade": "Low | Medium | High",
      "risk_score": 0,
      "sector": "string",
      "province": "string",
      "last_updated": "ISO 8601 datetime"
    }
  ],
  "total": 0
}
```

---

## GET /api/borrowers/:customer_id

**Purpose:** Single borrower profile (raw data, no scoring). Used by the stress
test panel to pre-fill the form with the borrower's current attributes.

**Path params:**
- `customer_id` — UUID string

**Response:**
```json
{
  "customer_id": "string",
  "name": "string",
  "age": 0,
  "sector_code": "string",
  "annual_income": 0,
  "crib_grade": "A | B | C | D | E | XX",
  "vehicle_type": "Private | Commercial",
  "loan_amount": 0,
  "vehicle_value": 0,
  "ltv_ratio": 0.0,
  "dpd_current": 0,
  "dpd_pattern": [0, 0, 0, 0, 0, 0],
  "app_login_freq": 0,
  "monthly_income": 0,
  "monthly_obligations": 0
}
```

`dpd_pattern` is the days-past-due figure for each of the last 6 months,
oldest first.

---

## GET /api/risk/:customer_id

**Purpose:** Full risk assessment for one borrower. This is the canonical
output of the scoring engine and the primary payload for the BorrowerCard.

**Path params:**
- `customer_id` — UUID string

**Response:**
```json
{
  "customer_id": "string",
  "risk_score": 0,
  "risk_grade": "Low | Medium | High",
  "risk_colour": "Green | Amber | Red",
  "compliance_breach": false,
  "compliance_reason": "string or null",
  "top_risk_drivers": [
    {
      "factor": "string",
      "impact": "Positive | Negative",
      "detail": "string"
    }
  ],
  "category_scores": {
    "capacity": 0,
    "character": 0,
    "collateral": 0,
    "conditions": 0,
    "capital": 0
  },
  "ewi_flags": [
    {
      "indicator": "string",
      "status": "Green | Amber | Red",
      "value": "string"
    }
  ],
  "recommended_action": "string",
  "calculated_at": "ISO 8601 datetime"
}
```

**Grading rules:**
- `risk_score >= 620` → `Low / Green`
- `420 <= risk_score < 620` → `Medium / Amber`
- `risk_score < 420` → `High / Red`
- If `compliance_breach == true`, the grade is forced to `High / Red`
  regardless of `risk_score`. The numeric `risk_score` is still returned
  so the frontend can show "score was 720 but flagged Red due to LTV breach".

---

## GET /api/portfolio/snapshot

**Purpose:** Aggregate view for the portfolio dashboard. Powers the doughnut
chart, sector table, and geographic concentration chart.

**Request:** none

**Response:**
```json
{
  "total_borrowers": 0,
  "by_grade": {
    "Low": 0,
    "Medium": 0,
    "High": 0
  },
  "by_sector": [
    {
      "sector": "string",
      "count": 0,
      "avg_score": 0
    }
  ],
  "by_province": [
    {
      "province": "string",
      "count": 0,
      "pct": 0.0,
      "avg_score": 0,
      "plc_target_pct": 0.0
    }
  ],
  "compliance_breaches": 0,
  "avg_portfolio_score": 0
}
```

---

## POST /api/stress-test

**Purpose:** Inject a risk event and get a recalculated score for a borrower
without persisting any change. The endpoint reads the borrower from the
database, applies the overrides on top, runs the scoring engine, and returns
the result. Nothing is written back.

**Request body:**
```json
{
  "customer_id": "string",
  "overrides": {
    "ltv_ratio": 0.0,
    "dpd_current": 0,
    "crib_grade": "string",
    "app_login_freq": 0
  }
}
```

All keys inside `overrides` are optional. Any key not provided keeps the
borrower's existing value.

**Response:** identical shape to `GET /api/risk/:customer_id`.

---

## Error responses

All endpoints return errors in this shape:

```json
{
  "error": "string (machine-readable code)",
  "message": "string (human-readable explanation)"
}
```

Standard status codes:
- `400` — malformed request body or missing required field
- `404` — borrower not found
- `500` — unhandled server error
