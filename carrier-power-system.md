# Project Prompt for OpenCode — BTS Carrier Power-Saving System (Thesis Project)

## 1. Project Overview

Build a full-stack web application that predicts hourly cellular network traffic for a BTS
(Base Transceiver Station) site and automatically decides which radio carriers should be
ON or OFF to save power, while keeping service quality intact. This is for a PhD
thesis-level research project called an **ML-Based Traffic-Aware Adaptive Carrier
Management System**.

Each physical site has **2 logical towers**, and each tower has **3 carriers (sectors)**:

- Tower A: carriers `1_A`, `1_B`, `1_C`
- Tower B: carriers `2_A`, `2_B`, `2_C`

**Sector A on each tower always stays ON** (it's the primary/anchor carrier that always
carries some baseline traffic). **Sectors B and C are the "switchable" carriers** — the
system predicts upcoming traffic and turns B/C on or off accordingly.

## 2. Real Data Schema (already collected, sample provided)

Source file has one sheet per tower (`Tower_A`, `Tower_B`), each with these exact columns:

| Column | Type | Description |
|---|---|---|
| `Date` | date | Calendar date |
| `Time` | string (HH:MM) | Hour of day, hourly granularity |
| `Tower_Sector` | string | Carrier ID, e.g. `1_A`, `1_B`, `1_C` |
| `eNodeB Name` | string | Site name (same for all rows of a site) |
| `Cell Name` | string | Unique cell identifier per carrier |
| `L.Traffic.User.Avg` | float | Average active users on that carrier that hour |
| `DL_PRB_Utilization(%)` | float | Downlink Physical Resource Block utilization % — **this is the primary metric used for ON/OFF decisions** |

Sample data available: ~32 days of hourly records per tower (3 carriers × 24 hours ×
~32 days ≈ 2,260 rows per sheet). This is the seed/training dataset — the system must be
built to keep growing this dataset over time (see §5).

## 3. Tech Stack (recommended — adjust if OpenCode prefers an equivalent)

- **Backend**: Python (FastAPI) — good ecosystem for both APIs and ML (pandas, scikit-learn / XGBoost)
- **Database**: SQLite to start (file-based, zero-ops), structured so it can be swapped for PostgreSQL later without schema changes
- **Scheduler**: APScheduler (or a simple cron-style background task) for periodic retraining and data ingestion
- **ML**: scikit-learn / XGBoost regression models, plus a simple seasonal-average baseline model for comparison
- **Frontend**: React + a charting library (Recharts or Chart.js) + Tailwind CSS, styled to look like a Power BI report (KPI cards, slicers/filters panel, clean grid layout)
- **Export**: `openpyxl` / `pandas.to_excel` for Excel export, endpoint returns a downloadable `.xlsx`

## 4. Database Schema (proposed)

```
sites (id, enodeb_name, location)
towers (id, site_id, tower_label)         -- Tower A / Tower B
carriers (id, tower_id, sector_label, cell_name, is_primary)  -- is_primary=true for Sector A
kpi_hourly (id, carrier_id, date, hour, traffic_users, prb_utilization, source)  -- source: 'upload' | 'live' | 'seed'
predictions (id, carrier_id, target_date, target_hour, predicted_traffic, predicted_prb, model_version, created_at)
decisions (id, tower_id, date, hour, mode, carrier_b_state, carrier_c_state, predicted_prb_used)
model_runs (id, trained_at, model_type, training_row_count, mae, rmse, notes)
```

`kpi_hourly.source` lets the dashboard distinguish seed/history data from newly ingested
live data, and lets the retraining job know how much fresh data has accumulated.

## 5. Data Ingestion Layer

Two ingestion paths, both writing into the same `kpi_hourly` table:

**A. Manual upload (build this first — it's the reliable path today)**
- Endpoint + UI widget to upload `.csv` or `.xlsx` matching the schema in §2
- Validate columns, parse Date+Time into a proper timestamp, reject/report malformed rows
- Deduplicate on (carrier_id, date, hour) — re-uploading the same period should upsert, not duplicate

**B. Live/automated ingestion (build as a pluggable connector interface)**
- Design an abstract `DataConnector` interface (e.g. `fetch_latest(since_timestamp) -> DataFrame`) so a real OSS/NMS API (e.g. Huawei U2020, Nokia NetAct, or whatever the network vendor exposes) can be plugged in later without changing the rest of the system
- Ship a working **simulated/mock connector** now (e.g. a scheduled job that reads from a designated "incoming" folder or a mock endpoint) so the live pipeline is fully functional and demoable even before a real vendor API is wired in
- Note for the user: true real-time integration depends on what access the actual telecom OSS/NMS system provides (API, SFTP export, SNMP, etc.) — flag this as a "connect real source here" extension point rather than blocking the whole system on it

Every ingested batch (manual or live) should trigger a check: if enough new rows have
accumulated since the last training run (e.g. 7+ new days), queue a retraining job.

## 6. Prediction Engine

Two models, both stored with results in `predictions`, so their accuracy can be compared on the dashboard:

**Baseline — Seasonal/Historical Pattern Model** (matches the "what happened on previous Mondays" idea directly):
- For a given target (date, hour, carrier), predicts using the average of the same weekday + same hour from history (e.g. average of the last N same weekdays, e.g. all previous Mondays at 14:00)
- Also compute the historical **range** (min–max, or mean ± std dev) for that weekday+hour bucket, so the dashboard can show "expected range" not just a point estimate
- This model is simple, transparent, and works even with limited data — good default/fallback

**ML Model — Random Forest / XGBoost Regression**:
- Features: hour, day-of-week, is_weekend, rolling 24h average, same-weekday-lag average (last 4 occurrences of this weekday+hour), trend/week-index
- Target: next-hour `prb_utilization` (and optionally `traffic_users`) per carrier
- Retrain on a schedule (nightly, or triggered after N new days of data as in §5)
- Track MAE/RMSE per training run in `model_runs` so accuracy-over-time is visible on the dashboard (this demonstrates the "more data → better prediction" narrative for the thesis)

## 7. Decision Engine — 3 Operating Modes (auto-selected)

Based on the **predicted** PRB utilization for Sectors B/C on each tower, the system
automatically selects one of three modes per tower, per hour:

| Mode | Trigger (example thresholds — make configurable) | Carrier B | Carrier C |
|---|---|---|---|
| **Power Saving** | predicted PRB < 60% | OFF | OFF |
| **Balanced** | 60% ≤ predicted PRB < 80% | ON | OFF |
| **High** | predicted PRB ≥ 80% | ON | ON |

Important: use **hysteresis** so the mode doesn't flap — e.g. only *downgrade* a mode if
predicted PRB has been below the lower threshold for the decision window, and don't
immediately re-upgrade on a single high reading unless it crosses the upper threshold.
Log every mode decision (with the predicted value that triggered it) into `decisions` —
this log is what the thesis will use to report energy savings and switching frequency.
Make all three thresholds **admin-configurable** (not hardcoded), since the actual
cut-offs should ideally be derived from analyzing this site's historical data, not
picked arbitrarily (this is a specific point the thesis needs to justify).

## 8. Dashboard (Power BI–style)

**Layout & feel**: professional, clean, KPI-card-driven, dark or light theme with clear
data hierarchy — should look like a network operations dashboard, not a generic admin panel.

**Required views/components:**
1. **Top KPI cards**: current mode (per tower), current predicted PRB, active carriers count, estimated energy saved (today / this week), model accuracy (latest MAE)
2. **"This [Weekday] vs history" chart**: pick a date, show its hourly prediction curve against the average + range band from previous same-weekdays — this directly implements the "last Mondays" comparison request
3. **Time-series chart**: actual vs predicted PRB / traffic, selectable by tower/carrier/date range
4. **Carrier state timeline**: ON/OFF (step chart) per carrier over the selected period, with mode color-coding (Power Saving / Balanced / High)
5. **Model accuracy trend**: MAE/RMSE per retraining run over time
6. **Filters/slicers panel**: date range, tower (A/B), carrier, mode — should update all charts on the page (Power BI-style cross-filtering)
7. **Data upload widget**: drag-and-drop CSV/XLSX upload with validation feedback
8. **Export button**: export the currently filtered data (raw KPIs, predictions, or decision log — user's choice) to `.xlsx`

## 9. Suggested Build Phases (so OpenCode can work incrementally)

1. **Phase 1 — Foundation**: DB schema, seed it with the provided sample data, manual CSV/XLSX upload endpoint + basic table view
2. **Phase 2 — Baseline prediction**: seasonal/historical model + "this weekday vs history" chart
3. **Phase 3 — Decision engine**: 3-mode logic with hysteresis, configurable thresholds, decision log
4. **Phase 4 — Dashboard**: full Power BI–style UI with filters, KPI cards, all charts from §8
5. **Phase 5 — ML upgrade**: Random Forest/XGBoost model alongside baseline, accuracy tracking, scheduled retraining
6. **Phase 6 — Live ingestion**: pluggable connector interface + mock live feed + retraining triggers
7. **Phase 7 — Export & polish**: Excel export, UI refinement, thesis-ready screenshots/reports

## 10. Notes for OpenCode

- Use the exact column names from §2 for any seed-data import script — the real sample file uses `L.Traffic.User.Avg` and `DL_PRB_Utilization(%)` with that exact punctuation/casing.
- Keep the seasonal baseline model even after the ML model is added — the dashboard should be able to show both, since comparing them is itself a thesis result.
- Everything about thresholds, retraining frequency, and connector source should be config, not hardcoded — this is a research tool that will be tuned against real data.
