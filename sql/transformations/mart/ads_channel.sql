-- Mart: Ads Channel Performance
-- Aggregates performance by advertising platform/channel
-- Dependencies: stg_ads, stg_ga4_sessions, stg_ga4_traffic

-- Ads Channel Performance Summary
CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_ads_channel_performance`
PARTITION BY date
CLUSTER BY platform
AS
WITH ads_by_channel AS (
    SELECT
        date,
        platform,
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
        COUNT(DISTINCT campaign_id) as active_campaigns,
        COUNT(DISTINCT ad_id) as active_ads
    FROM `${project_id}.${dataset_staging}.stg_ads`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY date, platform
),
ga4_by_channel AS (
    SELECT
        date,
        -- Map GA4 source/medium to channel
        CASE
            WHEN LOWER(source) LIKE '%facebook%' OR LOWER(medium) = 'paid_social' THEN 'facebook_ads'
            WHEN LOWER(source) LIKE '%google%' AND LOWER(medium) IN ('cpc', 'ppc') THEN 'google_ads'
            WHEN LOWER(source) LIKE '%tiktok%' THEN 'tiktok_ads'
            WHEN LOWER(source) LIKE '%line%' THEN 'line_ads'
            WHEN LOWER(source) LIKE '%shopee%' THEN 'shopee_ads'
            WHEN LOWER(source) LIKE '%lazada%' THEN 'lazada_ads'
            ELSE 'organic_and_other'
        END as platform,
        SUM(sessions) as sessions,
        SUM(total_users) as users,
        SUM(new_users) as new_users,
        AVG(bounce_rate) as avg_bounce_rate,
        AVG(avg_session_duration) as avg_session_duration
    FROM `${project_id}.${dataset_staging}.stg_ga4_sessions`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY date, 2
),
ga4_conversions AS (
    SELECT
        date,
        CASE
            WHEN LOWER(source) LIKE '%facebook%' OR LOWER(medium) = 'paid_social' THEN 'facebook_ads'
            WHEN LOWER(source) LIKE '%google%' AND LOWER(medium) IN ('cpc', 'ppc') THEN 'google_ads'
            WHEN LOWER(source) LIKE '%tiktok%' THEN 'tiktok_ads'
            WHEN LOWER(source) LIKE '%line%' THEN 'line_ads'
            WHEN LOWER(source) LIKE '%shopee%' THEN 'shopee_ads'
            WHEN LOWER(source) LIKE '%lazada%' THEN 'lazada_ads'
            ELSE 'organic_and_other'
        END as platform,
        SUM(transactions) as transactions,
        SUM(revenue) as revenue
    FROM `${project_id}.${dataset_staging}.stg_ga4_traffic`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY date, 2
)
SELECT
    COALESCE(a.date, g.date) as date,
    COALESCE(a.platform, g.platform) as platform,

    -- Spend metrics
    COALESCE(a.spend, 0) as spend,

    -- Reach & Impressions
    COALESCE(a.impressions, 0) as impressions,
    COALESCE(a.reach, 0) as reach,
    COALESCE(a.clicks, 0) as clicks,

    -- Efficiency metrics
    SAFE_DIVIDE(a.clicks, NULLIF(a.impressions, 0)) as ctr,
    SAFE_DIVIDE(a.spend, NULLIF(a.clicks, 0)) as cpc,
    SAFE_DIVIDE(a.spend * 1000, NULLIF(a.impressions, 0)) as cpm,

    -- Conversions from ads platform
    COALESCE(a.conversions, 0) as platform_conversions,
    COALESCE(a.conversion_value, 0) as platform_conversion_value,
    SAFE_DIVIDE(a.spend, NULLIF(a.conversions, 0)) as cost_per_conversion,
    SAFE_DIVIDE(a.conversion_value, NULLIF(a.spend, 0)) as platform_roas,

    -- Video metrics
    COALESCE(a.video_views, 0) as video_views,

    -- Engagement metrics
    COALESCE(a.likes, 0) as likes,
    COALESCE(a.comments, 0) as comments,
    COALESCE(a.shares, 0) as shares,
    a.likes + a.comments + a.shares as total_engagement,
    SAFE_DIVIDE(a.likes + a.comments + a.shares, NULLIF(a.impressions, 0)) as engagement_rate,

    -- Campaign counts
    COALESCE(a.active_campaigns, 0) as active_campaigns,
    COALESCE(a.active_ads, 0) as active_ads,

    -- GA4 session metrics
    COALESCE(g.sessions, 0) as ga4_sessions,
    COALESCE(g.users, 0) as ga4_users,
    COALESCE(g.new_users, 0) as ga4_new_users,
    g.avg_bounce_rate as ga4_bounce_rate,
    g.avg_session_duration as ga4_avg_session_duration,

    -- GA4 conversion metrics
    COALESCE(gc.transactions, 0) as ga4_transactions,
    COALESCE(gc.revenue, 0) as ga4_revenue,
    SAFE_DIVIDE(gc.transactions, NULLIF(g.sessions, 0)) as ga4_conversion_rate,
    SAFE_DIVIDE(gc.revenue, NULLIF(a.spend, 0)) as ga4_roas,

    -- Efficiency metrics
    SAFE_DIVIDE(a.spend, NULLIF(g.sessions, 0)) as cost_per_session,
    SAFE_DIVIDE(a.spend, NULLIF(gc.transactions, 0)) as cost_per_acquisition,

    -- Channel comparison metrics
    SAFE_DIVIDE(a.spend, NULLIF(g.users, 0)) as cost_per_user,
    SAFE_DIVIDE(gc.revenue, NULLIF(g.users, 0)) as revenue_per_user,

    CURRENT_TIMESTAMP() as _updated_at
FROM ads_by_channel a
FULL OUTER JOIN ga4_by_channel g ON a.date = g.date AND a.platform = g.platform
LEFT JOIN ga4_conversions gc ON a.date = gc.date AND a.platform = gc.platform
WHERE COALESCE(a.date, g.date) IS NOT NULL;


-- Channel Performance Summary View (aggregated totals)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_ads_channel_summary` AS
SELECT
    platform,
    SUM(spend) as total_spend,
    SUM(impressions) as total_impressions,
    SUM(clicks) as total_clicks,
    SUM(platform_conversions) as total_conversions,
    SUM(platform_conversion_value) as total_conversion_value,
    SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) as avg_ctr,
    SAFE_DIVIDE(SUM(spend), NULLIF(SUM(clicks), 0)) as avg_cpc,
    SAFE_DIVIDE(SUM(spend) * 1000, NULLIF(SUM(impressions), 0)) as avg_cpm,
    SAFE_DIVIDE(SUM(platform_conversion_value), NULLIF(SUM(spend), 0)) as avg_roas,
    SAFE_DIVIDE(SUM(spend), NULLIF(SUM(platform_conversions), 0)) as avg_cost_per_conversion,
    SUM(ga4_sessions) as total_ga4_sessions,
    SUM(ga4_transactions) as total_ga4_transactions,
    SUM(ga4_revenue) as total_ga4_revenue,
    SAFE_DIVIDE(SUM(ga4_revenue), NULLIF(SUM(spend), 0)) as avg_ga4_roas
FROM `${project_id}.${dataset_mart}.mart_ads_channel_performance`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY platform
ORDER BY total_spend DESC;


-- Channel Performance Trend View (daily comparison)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_ads_channel_trend` AS
SELECT
    date,
    platform,
    spend,
    impressions,
    clicks,
    platform_conversions,
    platform_conversion_value,
    ctr,
    cpc,
    cpm,
    platform_roas,
    ga4_sessions,
    ga4_transactions,
    ga4_revenue,
    ga4_roas,
    -- Running totals for the month
    SUM(spend) OVER (PARTITION BY platform, DATE_TRUNC(date, MONTH) ORDER BY date) as mtd_spend,
    SUM(platform_conversion_value) OVER (PARTITION BY platform, DATE_TRUNC(date, MONTH) ORDER BY date) as mtd_conversion_value
FROM `${project_id}.${dataset_mart}.mart_ads_channel_performance`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
ORDER BY date DESC, platform;
