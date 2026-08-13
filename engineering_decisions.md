# Data Engineering Decisions & Observations

## Key Observations & Anomalies Identified in `events.json`
1. **Invalid Timestamps**: Entry `EVT_00175` contains an unparseable timestamp string (`2026-99-40T99:99:99Z`).
2. **Missing `session_id`**: Entry `EVT_00009` contains a valid `user_id` but a `null` `session_id`.
3. **Missing `user_id`**: Entry `EVT_00019` contains a valid `session_id` but a `null` `user_id`.
4. **Future Timestamp Outliers**: Multiple entries (e.g., `EVT_00850`, `EVT_00912`) contain far-future placeholder timestamps (`2035-01-01T00:00:00Z`).
5. **Intra-Session Device Switching**: 160 of 164 valid sessions contain multiple distinct `device` values across their event logs. This high frequency indicates that `device` metadata is generated randomly per event rather than bound strictly to user session context. As a result, event-level device share metrics represent event volume rather than primary user device preference.
6. **Dataset Event Volume Floor**: The minimum event count for any session in this dataset is 3 events. There are zero single-event sessions in `events.json`. Consequently, the calculated Bounce Rate is mathematically guaranteed to evaluate to 0.0% due to dataset construction rather than an error in engine logic.

## Preprocessing & Data Cleaning Strategy
* **Corrupted Record Handling**: Records with unparseable or out-of-bounds timestamps are removed during ingestion. Exact row drop counts are logged for auditability.
* **Date Bounds Enforcement**: Events with timestamps outside the logical range (`2020-01-01` to `2026-12-31`) are filtered out to prevent skew in daily metrics and session duration metrics.
* **Orphan Event Handling**:
  * Events missing `session_id` are excluded from session-based metrics (Bounce Rate, Session Duration).
  * Unauthenticated events (`user_id = null`) remain included in session/event totals but are excluded from DAU calculations.

## Metric Definitions & Business Logic

| Metric | Business Definition / Logic |
| :--- | :--- |
| **Daily Active Users (DAU)** | Distinct count of non-null `user_id`s with at least 1 valid event per day within valid date bounds. |
| **Total Sessions** | Distinct count of non-null `session_id`s. |
| **Average Session Duration** | `(max(timestamp) - min(timestamp))` in seconds across events in a valid session, averaged across all sessions. |
| **Top 5 Interactions** | Frequency count of `interaction_id` where `event_name = 'interaction_click'`. |
| **Bounce Rate** | Percentage of sessions containing only 1 event OR where `max(timestamp) == min(timestamp)`. Both conditions are evaluated to capture single-event visits as well as zero-duration batch/programmatic events. |
| **Conversion Rate** | Distinct sessions containing a `purchase` event divided by total distinct sessions. |
| **Custom Metric: Device Usage Share** | Percentage distribution of total valid events grouped by `device` type (Desktop, Mobile, Tablet). |