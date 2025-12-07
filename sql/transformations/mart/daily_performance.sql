-- Mart: Daily Performance
-- Aggregates orders and ads data to calculate daily ROAS, CPA, and overall performance
-- Dependencies: stg_orders, stg_ads

-- Daily Performance Summary combining Orders + Ads
CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_daily_performance`
PARTITION BY date
CLUSTER BY platform
AS
WITH daily_orders AS (
    SELECT
        DATE(order_date) as date,
        platform,
        COUNT(*) as total_orders,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_orders,
        COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_orders,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
        SUM(total) as gross_revenue,
        SUM(total - discount) as net_revenue,
        SUM(discount) as total_discount,
        SUM(shipping_fee) as total_shipping_fee,
        SUM(item_count) as total_items_sold,
        COUNT(DISTINCT customer_id) as unique_customers
    FROM `${project_id}.${dataset_staging}.stg_orders`
    WHERE order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    GROUP BY 1, 2
),
daily_ads AS (
    SELECT
        date,
        platform,
        SUM(spend) as total_ad_spend,
        SUM(impressions) as total_impressions,
        SUM(clicks) as total_clicks,
        SUM(conversions) as total_conversions,
        SUM(conversion_value) as total_conversion_value,
        AVG(ctr) as avg_ctr,
        AVG(cpc) as avg_cpc,
        AVG(cpm) as avg_cpm
    FROM `${project_id}.${dataset_staging}.stg_ads`
    WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY 1, 2
),
-- Map ads platform to e-commerce platform for ROAS calculation
platform_mapping AS (
    SELECT 'shopee_ads' as ads_platform, 'shopee' as ecom_platform UNION ALL
    SELECT 'lazada_ads', 'lazada' UNION ALL
    SELECT 'facebook_ads', 'all' UNION ALL
    SELECT 'google_ads', 'all' UNION ALL
    SELECT 'tiktok_ads', 'tiktok_shop' UNION ALL
    SELECT 'line_ads', 'all'
)
SELECT
    COALESCE(o.date, a.date) as date,
    COALESCE(o.platform,
        CASE WHEN a.platform IN ('facebook_ads', 'google_ads', 'line_ads') THEN 'all'
             ELSE pm.ecom_platform
        END) as platform,

    -- Order metrics
    COALESCE(o.total_orders, 0) as total_orders,
    COALESCE(o.completed_orders, 0) as completed_orders,
    COALESCE(o.cancelled_orders, 0) as cancelled_orders,
    COALESCE(o.pending_orders, 0) as pending_orders,
    COALESCE(o.gross_revenue, 0) as gross_revenue,
    COALESCE(o.net_revenue, 0) as net_revenue,
    COALESCE(o.total_discount, 0) as total_discount,
    COALESCE(o.total_shipping_fee, 0) as total_shipping_fee,
    COALESCE(o.total_items_sold, 0) as total_items_sold,
    COALESCE(o.unique_customers, 0) as unique_customers,

    -- Ads metrics
    COALESCE(a.total_ad_spend, 0) as total_ad_spend,
    COALESCE(a.total_impressions, 0) as total_impressions,
    COALESCE(a.total_clicks, 0) as total_clicks,
    COALESCE(a.total_conversions, 0) as total_conversions,
    COALESCE(a.total_conversion_value, 0) as total_conversion_value,
    a.avg_ctr,
    a.avg_cpc,
    a.avg_cpm,

    -- Calculated metrics
    SAFE_DIVIDE(o.net_revenue, a.total_ad_spend) as roas,
    SAFE_DIVIDE(a.total_ad_spend, o.completed_orders) as cpa,
    SAFE_DIVIDE(o.net_revenue, o.completed_orders) as avg_order_value,
    SAFE_DIVIDE(o.completed_orders, o.total_orders) as order_completion_rate,
    SAFE_DIVIDE(a.total_conversions, a.total_clicks) as conversion_rate,

    CURRENT_TIMESTAMP() as _updated_at
FROM daily_orders o
FULL OUTER JOIN daily_ads a
    ON o.date = a.date
    AND (
        o.platform = (SELECT ecom_platform FROM platform_mapping pm WHERE pm.ads_platform = a.platform)
        OR (SELECT ecom_platform FROM platform_mapping pm WHERE pm.ads_platform = a.platform) = 'all'
    )
LEFT JOIN platform_mapping pm ON a.platform = pm.ads_platform
WHERE COALESCE(o.date, a.date) IS NOT NULL;


-- Create view for total daily performance (all platforms combined)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_daily_performance_total` AS
SELECT
    date,
    'all' as platform,
    SUM(total_orders) as total_orders,
    SUM(completed_orders) as completed_orders,
    SUM(cancelled_orders) as cancelled_orders,
    SUM(pending_orders) as pending_orders,
    SUM(gross_revenue) as gross_revenue,
    SUM(net_revenue) as net_revenue,
    SUM(total_discount) as total_discount,
    SUM(total_shipping_fee) as total_shipping_fee,
    SUM(total_items_sold) as total_items_sold,
    SUM(unique_customers) as unique_customers,
    SUM(total_ad_spend) as total_ad_spend,
    SUM(total_impressions) as total_impressions,
    SUM(total_clicks) as total_clicks,
    SUM(total_conversions) as total_conversions,
    SUM(total_conversion_value) as total_conversion_value,
    SAFE_DIVIDE(SUM(total_clicks), NULLIF(SUM(total_impressions), 0)) as avg_ctr,
    SAFE_DIVIDE(SUM(total_ad_spend), NULLIF(SUM(total_clicks), 0)) as avg_cpc,
    SAFE_DIVIDE(SUM(total_ad_spend) * 1000, NULLIF(SUM(total_impressions), 0)) as avg_cpm,
    SAFE_DIVIDE(SUM(net_revenue), NULLIF(SUM(total_ad_spend), 0)) as roas,
    SAFE_DIVIDE(SUM(total_ad_spend), NULLIF(SUM(completed_orders), 0)) as cpa,
    SAFE_DIVIDE(SUM(net_revenue), NULLIF(SUM(completed_orders), 0)) as avg_order_value,
    SAFE_DIVIDE(SUM(completed_orders), NULLIF(SUM(total_orders), 0)) as order_completion_rate,
    SAFE_DIVIDE(SUM(total_conversions), NULLIF(SUM(total_clicks), 0)) as conversion_rate,
    MAX(_updated_at) as _updated_at
FROM `${project_id}.${dataset_mart}.mart_daily_performance`
GROUP BY date;
