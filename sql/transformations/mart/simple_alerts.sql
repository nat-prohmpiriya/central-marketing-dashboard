-- Mart: Simple Alerts
-- Rule-based alerts generated from mart tables
-- Dependencies: mart_daily_performance, mart_shop_performance, mart_campaign_performance

-- Alert Thresholds Configuration
-- These can be adjusted based on business requirements
-- ROAS thresholds: Critical < 1.5, Warning < 2.0
-- CPA thresholds: Critical > 500, Warning > 300
-- Revenue drop: Critical > 30%, Warning > 20%

-- Simple Alerts Table
CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_simple_alerts`
PARTITION BY DATE(created_at)
CLUSTER BY alert_type, severity, platform
AS
WITH
-- Daily Performance Alerts (ROAS, CPA)
daily_alerts AS (
    SELECT
        GENERATE_UUID() as alert_id,
        date,
        platform,
        'daily' as entity_type,
        CONCAT(platform, '_', CAST(date AS STRING)) as entity_id,
        CONCAT(platform, ' - ', CAST(date AS STRING)) as entity_name,

        -- Low ROAS Critical
        CASE
            WHEN roas IS NOT NULL AND roas < 1.5 AND total_ad_spend > 0 THEN 'low_roas'
            WHEN roas IS NOT NULL AND roas < 2.0 AND total_ad_spend > 0 THEN 'low_roas'
            ELSE NULL
        END as alert_type,

        CASE
            WHEN roas IS NOT NULL AND roas < 1.5 AND total_ad_spend > 0 THEN 'critical'
            WHEN roas IS NOT NULL AND roas < 2.0 AND total_ad_spend > 0 THEN 'warning'
            ELSE NULL
        END as severity,

        CASE
            WHEN roas IS NOT NULL AND roas < 1.5 AND total_ad_spend > 0 THEN CONCAT('Low ROAS: ', platform)
            WHEN roas IS NOT NULL AND roas < 2.0 AND total_ad_spend > 0 THEN CONCAT('Low ROAS Warning: ', platform)
            ELSE NULL
        END as title,

        CASE
            WHEN roas IS NOT NULL AND roas < 1.5 AND total_ad_spend > 0
                THEN CONCAT('ROAS is ', ROUND(roas, 2), ', below critical threshold of 1.5')
            WHEN roas IS NOT NULL AND roas < 2.0 AND total_ad_spend > 0
                THEN CONCAT('ROAS is ', ROUND(roas, 2), ', below warning threshold of 2.0')
            ELSE NULL
        END as message,

        'roas' as metric_name,
        roas as metric_value,
        CASE
            WHEN roas < 1.5 THEN 1.5
            WHEN roas < 2.0 THEN 2.0
            ELSE NULL
        END as threshold,

        net_revenue,
        total_ad_spend,
        cpa
    FROM `${project_id}.${dataset_mart}.mart_daily_performance`
    WHERE date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
      AND (roas < 2.0 AND total_ad_spend > 0)
),

-- CPA Alerts
cpa_alerts AS (
    SELECT
        GENERATE_UUID() as alert_id,
        date,
        platform,
        'daily' as entity_type,
        CONCAT(platform, '_', CAST(date AS STRING)) as entity_id,
        CONCAT(platform, ' - ', CAST(date AS STRING)) as entity_name,

        CASE
            WHEN cpa IS NOT NULL AND cpa > 500 THEN 'high_cpa'
            WHEN cpa IS NOT NULL AND cpa > 300 THEN 'high_cpa'
            ELSE NULL
        END as alert_type,

        CASE
            WHEN cpa IS NOT NULL AND cpa > 500 THEN 'critical'
            WHEN cpa IS NOT NULL AND cpa > 300 THEN 'warning'
            ELSE NULL
        END as severity,

        CASE
            WHEN cpa IS NOT NULL AND cpa > 500 THEN CONCAT('High CPA: ', platform)
            WHEN cpa IS NOT NULL AND cpa > 300 THEN CONCAT('High CPA Warning: ', platform)
            ELSE NULL
        END as title,

        CASE
            WHEN cpa IS NOT NULL AND cpa > 500
                THEN CONCAT('CPA is ', ROUND(cpa, 2), ' THB, above critical threshold of 500 THB')
            WHEN cpa IS NOT NULL AND cpa > 300
                THEN CONCAT('CPA is ', ROUND(cpa, 2), ' THB, above warning threshold of 300 THB')
            ELSE NULL
        END as message,

        'cpa' as metric_name,
        cpa as metric_value,
        CASE
            WHEN cpa > 500 THEN 500.0
            WHEN cpa > 300 THEN 300.0
            ELSE NULL
        END as threshold,

        net_revenue,
        total_ad_spend,
        cpa as cpa_value
    FROM `${project_id}.${dataset_mart}.mart_daily_performance`
    WHERE date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
      AND (cpa > 300)
),

-- Revenue Drop Alerts (WoW comparison)
revenue_history AS (
    SELECT
        platform,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
                  AND date < CURRENT_DATE() THEN net_revenue ELSE 0 END) as revenue_7d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
                  AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN net_revenue ELSE 0 END) as revenue_prev_7d
    FROM `${project_id}.${dataset_mart}.mart_daily_performance`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
    GROUP BY platform
),
revenue_alerts AS (
    SELECT
        GENERATE_UUID() as alert_id,
        DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY) as date,
        platform,
        'weekly' as entity_type,
        CONCAT(platform, '_week_', CAST(DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) AS STRING)) as entity_id,
        CONCAT(platform, ' Weekly Revenue') as entity_name,

        CASE
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.30 THEN 'revenue_drop'
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.20 THEN 'revenue_drop'
            ELSE NULL
        END as alert_type,

        CASE
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.30 THEN 'critical'
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.20 THEN 'warning'
            ELSE NULL
        END as severity,

        CASE
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.30
                THEN CONCAT('Revenue Drop Critical: ', platform)
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.20
                THEN CONCAT('Revenue Drop Warning: ', platform)
            ELSE NULL
        END as title,

        CASE
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.30
                THEN CONCAT('Revenue dropped by ',
                    ROUND(ABS((revenue_7d - revenue_prev_7d) / revenue_prev_7d) * 100, 1),
                    '% WoW (from ', ROUND(revenue_prev_7d, 2), ' to ', ROUND(revenue_7d, 2), ')')
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.20
                THEN CONCAT('Revenue dropped by ',
                    ROUND(ABS((revenue_7d - revenue_prev_7d) / revenue_prev_7d) * 100, 1),
                    '% WoW (from ', ROUND(revenue_prev_7d, 2), ' to ', ROUND(revenue_7d, 2), ')')
            ELSE NULL
        END as message,

        'revenue_change_pct' as metric_name,
        CASE WHEN revenue_prev_7d > 0 THEN (revenue_7d - revenue_prev_7d) / revenue_prev_7d ELSE NULL END as metric_value,
        CASE
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.30 THEN -0.30
            WHEN revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.20 THEN -0.20
            ELSE NULL
        END as threshold,

        revenue_7d as net_revenue,
        NULL as total_ad_spend,
        NULL as cpa
    FROM revenue_history
    WHERE revenue_prev_7d > 0 AND (revenue_7d - revenue_prev_7d) / revenue_prev_7d < -0.20
),

-- Campaign Performance Alerts
campaign_alerts AS (
    SELECT
        GENERATE_UUID() as alert_id,
        date,
        platform,
        'campaign' as entity_type,
        campaign_id as entity_id,
        campaign_name as entity_name,

        'campaign_underperforming' as alert_type,

        CASE
            WHEN performance_status = 'underperforming' THEN 'warning'
            ELSE NULL
        END as severity,

        CONCAT('Underperforming Campaign: ', campaign_name) as title,

        CONCAT('Campaign ROAS (', ROUND(roas, 2), ') is significantly below platform benchmark') as message,

        'roas' as metric_name,
        roas as metric_value,
        NULL as threshold,

        conversion_value as net_revenue,
        spend as total_ad_spend,
        cost_per_conversion as cpa
    FROM `${project_id}.${dataset_mart}.mart_campaign_performance`
    WHERE date = DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
      AND performance_status = 'underperforming'
      AND spend > 100  -- Only alert for campaigns with meaningful spend
),

-- Combine all alerts
all_alerts AS (
    SELECT * FROM daily_alerts WHERE alert_type IS NOT NULL
    UNION ALL
    SELECT * FROM cpa_alerts WHERE alert_type IS NOT NULL
    UNION ALL
    SELECT * FROM revenue_alerts WHERE alert_type IS NOT NULL
    UNION ALL
    SELECT * FROM campaign_alerts WHERE severity IS NOT NULL
)

SELECT
    alert_id,
    alert_type,
    severity,
    title,
    message,
    metric_name,
    metric_value,
    threshold,
    platform,
    entity_type,
    entity_id,
    entity_name,
    date as alert_date,
    'active' as status,
    STRUCT(
        net_revenue,
        total_ad_spend,
        cpa
    ) as context,
    CURRENT_TIMESTAMP() as created_at,
    CURRENT_TIMESTAMP() as _updated_at
FROM all_alerts
ORDER BY
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        ELSE 3
    END,
    date DESC;


-- View for Active Alerts
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_active_alerts` AS
SELECT
    alert_id,
    alert_type,
    severity,
    title,
    message,
    metric_name,
    ROUND(metric_value, 2) as metric_value,
    threshold,
    platform,
    entity_type,
    entity_id,
    entity_name,
    alert_date,
    status,
    created_at
FROM `${project_id}.${dataset_mart}.mart_simple_alerts`
WHERE status = 'active'
ORDER BY
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        ELSE 3
    END,
    created_at DESC;


-- View for Alert Summary by Type
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_alert_summary` AS
SELECT
    alert_type,
    severity,
    COUNT(*) as alert_count,
    COUNT(DISTINCT platform) as platforms_affected,
    COUNT(DISTINCT entity_id) as entities_affected,
    MIN(alert_date) as earliest_alert,
    MAX(alert_date) as latest_alert
FROM `${project_id}.${dataset_mart}.mart_simple_alerts`
WHERE status = 'active'
  AND alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY alert_type, severity
ORDER BY
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'warning' THEN 2
        ELSE 3
    END,
    alert_count DESC;


-- View for Platform Alert Health Score
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_platform_alert_health` AS
SELECT
    platform,
    COUNTIF(severity = 'critical') as critical_alerts,
    COUNTIF(severity = 'warning') as warning_alerts,
    COUNTIF(severity = 'info') as info_alerts,
    COUNT(*) as total_alerts,
    -- Health score: 100 - (critical * 20 + warning * 5 + info * 1)
    -- Capped at 0-100
    GREATEST(0, 100 - (COUNTIF(severity = 'critical') * 20 + COUNTIF(severity = 'warning') * 5 + COUNTIF(severity = 'info'))) as health_score
FROM `${project_id}.${dataset_mart}.mart_simple_alerts`
WHERE status = 'active'
  AND alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY platform
ORDER BY health_score ASC;


-- Daily Alert Trend
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_alert_trend` AS
SELECT
    alert_date,
    alert_type,
    severity,
    COUNT(*) as alert_count
FROM `${project_id}.${dataset_mart}.mart_simple_alerts`
WHERE alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY alert_date, alert_type, severity
ORDER BY alert_date DESC, alert_type;
