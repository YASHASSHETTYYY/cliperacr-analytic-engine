# Cliperact Analytics Engine

A lightweight Python engine that ingests raw analytics events from Cliperact's interactive player, cleans them, and computes core product and engagement metrics.

## Project Structure

```
analytics-engine/
├── analytics_engine.py       # Main engine: loads, cleans, and computes metrics
├── events.json                # Raw event dataset (1,000 records)
├── queries.sql                 # SQL equivalents of the core metrics
├── schema.md                   # Field-by-field schema documentation
├── engineering_decisions.md    # Assumptions, anomalies, and cleaning rationale
├── README.md                   # This file
└── requirements.txt             # Python dependencies
```

## Installation

Requires Python 3.9+.

```bash
git clone <https://github.com/YASHASSHETTYYY/cliperacr-analytic-engine.git>
cd analytics-engine

python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## How to Run

```bash
python analytics_engine.py
```

This loads `events.json`, cleans it, and prints a metrics report to stdout, including a short audit log of how many records were dropped and why.

To run the SQL queries instead, load `events.json` into a table named `events` in your database of choice, then execute `queries.sql` against it (written for standard/ANSI SQL, tested against SQLite).

## Libraries Used

- **pandas** — the only dependency. The dataset (1,000 records) and metric set are small enough that pandas' groupby/aggregation API covers everything needed without introducing extra tooling.

## Sample Output

```
INFO: Ingestion audit: 1000 total raw records.
INFO: Dropped 1 record with an unparseable timestamp.
INFO: Dropped 2 records with out-of-bounds (future placeholder) timestamps.
INFO: Retained 997 valid records for processing.
INFO: Self-verification passed — all metric invariants satisfied.
==================================================
          CLIPERACT ANALYTICS ENGINE
==================================================
Daily Active Users (DAU)  : {'2026-08-10': 30, '2026-08-11': 31, '2026-08-12': 28, '2026-08-13': 30, '2026-08-14': 4}
Total Sessions            : 164
Unique Users              : 54
Avg Sessions / User       : 3.04
Avg Session Duration      : 106.38 seconds
Top Interactions          : {'BTN_BUY': 57, 'BTN_PLAY': 53, 'BTN_FEATURES': 51, 'BTN_DEMO': 51, 'BTN_CONTACT': 44}
Bounce Rate               : 0.0%
Conversion Rate           : 23.78%
Device Usage Share (%)    : {'Desktop': 36.08, 'Mobile': 33.07, 'Tablet': 30.85}
==================================================
```

## Metric Definitions

| Metric | Definition |
| :--- | :--- |
| **Daily Active Users** | Distinct `user_id` count per calendar day, among events with a valid timestamp and non-null `user_id`. |
| **Total Sessions / Avg Sessions per User** | Distinct `session_id` count, and that count divided by distinct `user_id` count. |
| **Average Session Duration** | `max(timestamp) − min(timestamp)` per session, averaged across all sessions with a valid `session_id`. |
| **Top 5 Interactions** | Frequency of `interaction_id` where `event_name = 'interaction_click'`, top 5 by count. |
| **Bounce Rate** | Percentage of sessions with exactly one event. On this dataset this is 0% — every session has at least 3 events, so no bounces exist in the data (see `engineering_decisions.md`). |
| **Conversion Rate** | Percentage of sessions containing at least one `purchase` event. |
| **Device Usage Share** (additional metric) | Percentage distribution of events by `device`, computed at the event level rather than the session level — see assumptions below for why. |

## Key Assumptions

Full rationale is in `engineering_decisions.md`; the short version:

- Records with unparseable timestamps (e.g. the malformed `EVT_00175` entry) are dropped rather than repaired, since the original value can't be recovered reliably.
- Two records dated `2035-01-01` are treated as placeholder/test data (likely a corrupted client clock) and excluded — an event dated years past the rest of the dataset would otherwise distort session duration by orders of magnitude.
- Events missing `session_id` are excluded from session-scoped metrics (bounce rate, session duration) but not from event-level counts.
- Events missing `user_id` are excluded from user-scoped metrics (DAU) but retained for session- and event-level metrics, since an unauthenticated event still belongs to a real session.
- `device` is treated as a per-event attribute, not a per-session one — 160 of 164 sessions contain more than one distinct device value, so assuming one device per session would be inaccurate for this dataset.

## Future Improvements

- Export metrics to JSON/CSV in addition to stdout, for downstream dashboarding.
- Add a `pytest` suite with fixed input/output fixtures to regression-test each metric.
- Add CLI arguments for date-range filtering and configurable top-N interaction counts.
- Persist the cleaned dataset (post-filtering) to a local SQLite or Parquet file so the SQL queries and Python engine can run against an identical, already-validated source of truth.
- Compute a session-level "primary device" (e.g. mode of device per session) alongside the current event-level device share, since both views answer slightly different product questions.
