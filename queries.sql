-- ANSI SQL / PostgreSQL Compatible
-- Data Filtering Guard Note:
-- Filters out unparseable/null timestamps and enforces date bounds (2020-01-01 to 2026-12-31)
-- to exclude corrupted entries (e.g., EVT_00175) and far-future placeholders (e.g., 2035-01-01).

-- 1. Daily Active Users (DAU)
SELECT 
    CAST(timestamp AS DATE) AS event_date,
    COUNT(DISTINCT user_id) AS daily_active_users
FROM events
WHERE user_id IS NOT NULL 
  AND timestamp IS NOT NULL
  AND timestamp >= '2020-01-01T00:00:00Z'
  AND timestamp <= '2026-12-31T23:59:59Z'
GROUP BY CAST(timestamp AS DATE)
ORDER BY event_date;

-- 2. Total Sessions & Sessions per User
SELECT 
    COUNT(DISTINCT session_id) AS total_sessions,
    COUNT(DISTINCT user_id) AS total_users,
    ROUND(COUNT(DISTINCT session_id)::DECIMAL / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS avg_sessions_per_user
FROM events
WHERE session_id IS NOT NULL
  AND timestamp IS NOT NULL
  AND timestamp >= '2020-01-01T00:00:00Z'
  AND timestamp <= '2026-12-31T23:59:59Z';

-- 3. Top 5 Interactions
SELECT 
    interaction_id,
    COUNT(*) AS click_count
FROM events
WHERE event_name = 'interaction_click'
  AND interaction_id IS NOT NULL
  AND timestamp IS NOT NULL
  AND timestamp >= '2020-01-01T00:00:00Z'
  AND timestamp <= '2026-12-31T23:59:59Z'
GROUP BY interaction_id
ORDER BY click_count DESC
LIMIT 5;

-- 4. Conversion Rate
SELECT 
    COUNT(DISTINCT session_id) AS total_sessions,
    COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN session_id END) AS converted_sessions,
    ROUND(
        (COUNT(DISTINCT CASE WHEN event_name = 'purchase' THEN session_id END)::DECIMAL / 
        NULLIF(COUNT(DISTINCT session_id), 0)) * 100, 2
    ) AS conversion_rate_percentage
FROM events
WHERE session_id IS NOT NULL
  AND timestamp IS NOT NULL
  AND timestamp >= '2020-01-01T00:00:00Z'
  AND timestamp <= '2026-12-31T23:59:59Z';