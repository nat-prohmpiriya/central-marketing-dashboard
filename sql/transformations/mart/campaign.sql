-- Mart: Campaign Performance
-- Campaign-level metrics with performance status classification
-- Dependencies: stg_ads

-- Campaign Performance Summary
CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_campaign_performance`
PARTITION BY date
CLUSTER BY platform, campaign_id
AS
WITH campaign_metrics AS (
    SELECT
        date,
        platform,
        account_id,
        campaign_id,
        campaign_name,
        campaign_type,
        objective,
        status,
        SUM(spend) as spend,
        SUM(impressions) as impressions,
        SUM(clicks) as clicks,
        SUM(reach) as reach,
        SUM(conversions) as conversions,
        SUM(conversion_value) as conversion_value,
        SUM(video_views) as video_views,
        SUM(likes) as likes,
        SUM(comments) as comments,
        SUM(shares) as shares,
        COUNT(DISTINCT adgroup_id) as active_adgroups,
        COUNT(DISTINCT ad_id) as active_ads
    FROM `${project_id}.${dataset_staging}.stg_ads`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
      AND level IN ('campaign', 'ad', 'adgroup')
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
),
campaign_benchmarks AS (
    -- Calculate platform-level benchmarks for comparison
    SELECT
        platform,
        AVG(SAFE_DIVIDE(clicks, NULLIF(impressions, 0))) as benchmark_ctr,
        AVG(SAFE_DIVIDE(spend, NULLIF(clicks, 0))) as benchmark_cpc,
        AVG(SAFE_DIVIDE(spend * 1000, NULLIF(impressions, 0))) as benchmark_cpm,
        AVG(SAFE_DIVIDE(conversion_value, NULLIF(spend, 0))) as benchmark_roas,
        AVG(SAFE_DIVIDE(spend, NULLIF(conversions, 0))) as benchmark_cpa
    FROM campaign_metrics
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY platform
),
campaign_history AS (
    -- Get previous period metrics for comparison
    SELECT
        platform,
        campaign_id,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN spend ELSE 0 END) as spend_7d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
                  AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN spend ELSE 0 END) as spend_prev_7d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN conversion_value ELSE 0 END) as conv_value_7d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
                  AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN conversion_value ELSE 0 END) as conv_value_prev_7d,
        MIN(date) as first_active_date,
        MAX(date) as last_active_date,
        COUNT(DISTINCT date) as days_active
    FROM campaign_metrics
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY platform, campaign_id
)
SELECT
    cm.date,
    cm.platform,
    cm.account_id,
    cm.campaign_id,
    cm.campaign_name,
    cm.campaign_type,
    cm.objective,
    cm.status,

    -- Spend metrics
    cm.spend,

    -- Reach & Impressions
    cm.impressions,
    cm.reach,
    cm.clicks,

    -- Efficiency metrics
    SAFE_DIVIDE(cm.clicks, NULLIF(cm.impressions, 0)) as ctr,
    SAFE_DIVIDE(cm.spend, NULLIF(cm.clicks, 0)) as cpc,
    SAFE_DIVIDE(cm.spend * 1000, NULLIF(cm.impressions, 0)) as cpm,

    -- Conversion metrics
    cm.conversions,
    cm.conversion_value,
    SAFE_DIVIDE(cm.spend, NULLIF(cm.conversions, 0)) as cost_per_conversion,
    SAFE_DIVIDE(cm.conversions, NULLIF(cm.clicks, 0)) as conversion_rate,
    SAFE_DIVIDE(cm.conversion_value, NULLIF(cm.spend, 0)) as roas,

    -- Video metrics
    cm.video_views,
    SAFE_DIVIDE(cm.video_views, NULLIF(cm.impressions, 0)) as video_view_rate,

    -- Engagement metrics
    cm.likes,
    cm.comments,
    cm.shares,
    cm.likes + cm.comments + cm.shares as total_engagement,
    SAFE_DIVIDE(cm.likes + cm.comments + cm.shares, NULLIF(cm.impressions, 0)) as engagement_rate,

    -- Campaign structure
    cm.active_adgroups,
    cm.active_ads,

    -- Comparison to benchmarks
    SAFE_DIVIDE(cm.clicks, NULLIF(cm.impressions, 0)) - cb.benchmark_ctr as ctr_vs_benchmark,
    SAFE_DIVIDE(cm.spend, NULLIF(cm.clicks, 0)) - cb.benchmark_cpc as cpc_vs_benchmark,
    SAFE_DIVIDE(cm.conversion_value, NULLIF(cm.spend, 0)) - cb.benchmark_roas as roas_vs_benchmark,

    -- Historical context
    ch.first_active_date,
    ch.last_active_date,
    ch.days_active,
    ch.spend_7d,
    ch.spend_prev_7d,
    SAFE_DIVIDE(ch.spend_7d - ch.spend_prev_7d, NULLIF(ch.spend_prev_7d, 0)) as spend_change_wow,
    ch.conv_value_7d,
    ch.conv_value_prev_7d,
    SAFE_DIVIDE(ch.conv_value_7d - ch.conv_value_prev_7d, NULLIF(ch.conv_value_prev_7d, 0)) as conv_value_change_wow,

    -- Performance classification
    CASE
        -- High performers
        WHEN SAFE_DIVIDE(cm.conversion_value, NULLIF(cm.spend, 0)) > cb.benchmark_roas * 1.5
             AND cm.spend > 0 THEN 'top_performer'

        -- Good performers
        WHEN SAFE_DIVIDE(cm.conversion_value, NULLIF(cm.spend, 0)) > cb.benchmark_roas
             AND cm.spend > 0 THEN 'good'

        -- Underperformers
        WHEN SAFE_DIVIDE(cm.conversion_value, NULLIF(cm.spend, 0)) < cb.benchmark_roas * 0.5
             AND cm.spend > 0 THEN 'underperforming'

        -- Learning phase (new campaigns with limited data)
        WHEN ch.days_active < 7 THEN 'learning'

        -- Paused campaigns
        WHEN cm.status = 'paused' THEN 'paused'

        -- Average performers
        ELSE 'average'
    END as performance_status,

    -- Optimization recommendations flag
    CASE
        WHEN SAFE_DIVIDE(cm.clicks, NULLIF(cm.impressions, 0)) < cb.benchmark_ctr * 0.7 THEN 'low_ctr'
        WHEN SAFE_DIVIDE(cm.spend, NULLIF(cm.clicks, 0)) > cb.benchmark_cpc * 1.3 THEN 'high_cpc'
        WHEN SAFE_DIVIDE(cm.conversions, NULLIF(cm.clicks, 0)) < 0.01 THEN 'low_cvr'
        ELSE NULL
    END as optimization_flag,

    CURRENT_TIMESTAMP() as _updated_at
FROM campaign_metrics cm
LEFT JOIN campaign_benchmarks cb ON cm.platform = cb.platform
LEFT JOIN campaign_history ch ON cm.platform = ch.platform AND cm.campaign_id = ch.campaign_id;


-- Campaign Summary View (latest snapshot per campaign)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_campaign_summary` AS
WITH latest_data AS (
    SELECT
        platform,
        campaign_id,
        MAX(date) as latest_date
    FROM `${project_id}.${dataset_mart}.mart_campaign_performance`
    GROUP BY platform, campaign_id
)
SELECT
    cp.*
FROM `${project_id}.${dataset_mart}.mart_campaign_performance` cp
INNER JOIN latest_data ld
    ON cp.platform = ld.platform
    AND cp.campaign_id = ld.campaign_id
    AND cp.date = ld.latest_date
ORDER BY cp.spend DESC;


-- Campaign Performance Trends (7-day rolling)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_campaign_trend` AS
SELECT
    date,
    platform,
    campaign_id,
    campaign_name,
    spend,
    conversions,
    conversion_value,
    roas,
    performance_status,
    -- 7-day rolling metrics
    SUM(spend) OVER (
        PARTITION BY platform, campaign_id
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as spend_7d_rolling,
    SUM(conversion_value) OVER (
        PARTITION BY platform, campaign_id
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as conv_value_7d_rolling,
    AVG(roas) OVER (
        PARTITION BY platform, campaign_id
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as roas_7d_rolling
FROM `${project_id}.${dataset_mart}.mart_campaign_performance`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY date DESC, platform, campaign_id;


-- Top Campaigns View (by ROAS and spend)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_top_campaigns` AS
SELECT
    platform,
    campaign_id,
    campaign_name,
    SUM(spend) as total_spend,
    SUM(conversion_value) as total_conversion_value,
    SAFE_DIVIDE(SUM(conversion_value), NULLIF(SUM(spend), 0)) as avg_roas,
    SUM(conversions) as total_conversions,
    SAFE_DIVIDE(SUM(spend), NULLIF(SUM(conversions), 0)) as avg_cpa,
    MAX(performance_status) as latest_status
FROM `${project_id}.${dataset_mart}.mart_campaign_performance`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY platform, campaign_id, campaign_name
HAVING SUM(spend) > 0
ORDER BY total_conversion_value DESC
LIMIT 50;
