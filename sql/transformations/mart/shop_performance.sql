-- Mart: Shop Performance
-- Aggregates performance by shop/seller with growth rate calculations
-- Dependencies: stg_orders, stg_ads

-- Shop Performance Summary with Growth Rates
CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_shop_performance`
PARTITION BY snapshot_date
CLUSTER BY platform
AS
WITH shop_metrics AS (
    SELECT
        CURRENT_DATE() as snapshot_date,
        platform,
        -- Current period (last 30 days)
        COUNT(CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN 1 END) as orders_30d,
        SUM(CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN total ELSE 0 END) as revenue_30d,
        SUM(CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN total - discount ELSE 0 END) as net_revenue_30d,
        COUNT(DISTINCT CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN customer_id END) as customers_30d,
        SUM(CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN item_count ELSE 0 END) as items_sold_30d,

        -- Previous period (31-60 days ago)
        COUNT(CASE
            WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)
            AND order_date < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            THEN 1
        END) as orders_prev_30d,
        SUM(CASE
            WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)
            AND order_date < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            THEN total ELSE 0
        END) as revenue_prev_30d,
        SUM(CASE
            WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)
            AND order_date < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            THEN total - discount ELSE 0
        END) as net_revenue_prev_30d,
        COUNT(DISTINCT CASE
            WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)
            AND order_date < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
            THEN customer_id
        END) as customers_prev_30d,

        -- Current week
        COUNT(CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) THEN 1 END) as orders_7d,
        SUM(CASE WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY) THEN total ELSE 0 END) as revenue_7d,

        -- Previous week
        COUNT(CASE
            WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
            AND order_date < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            THEN 1
        END) as orders_prev_7d,
        SUM(CASE
            WHEN order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
            AND order_date < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            THEN total ELSE 0
        END) as revenue_prev_7d,

        -- Order status breakdown
        COUNT(CASE WHEN status = 'completed' AND order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN 1 END) as completed_orders_30d,
        COUNT(CASE WHEN status = 'cancelled' AND order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN 1 END) as cancelled_orders_30d,
        COUNT(CASE WHEN status = 'pending' AND order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY) THEN 1 END) as pending_orders_30d,

        -- Total historical
        COUNT(*) as total_orders_all_time,
        SUM(total) as total_revenue_all_time,
        COUNT(DISTINCT customer_id) as total_customers_all_time,
        MIN(order_date) as first_order_date,
        MAX(order_date) as last_order_date
    FROM `${project_id}.${dataset_staging}.stg_orders`
    WHERE order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 365 DAY)
    GROUP BY platform
),
shop_ads AS (
    SELECT
        -- Map ads platform to e-commerce platform
        CASE
            WHEN platform = 'shopee_ads' THEN 'shopee'
            WHEN platform = 'lazada_ads' THEN 'lazada'
            WHEN platform = 'tiktok_ads' THEN 'tiktok_shop'
            ELSE platform
        END as platform,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN spend ELSE 0 END) as ad_spend_30d,
        SUM(CASE
            WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
            AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            THEN spend ELSE 0
        END) as ad_spend_prev_30d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN impressions ELSE 0 END) as impressions_30d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN clicks ELSE 0 END) as clicks_30d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN conversions ELSE 0 END) as conversions_30d
    FROM `${project_id}.${dataset_staging}.stg_ads`
    WHERE platform IN ('shopee_ads', 'lazada_ads', 'tiktok_ads')
      AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
    GROUP BY 1
)
SELECT
    sm.snapshot_date,
    sm.platform,

    -- Current period metrics
    sm.orders_30d,
    sm.revenue_30d,
    sm.net_revenue_30d,
    sm.customers_30d,
    sm.items_sold_30d,

    -- Week metrics
    sm.orders_7d,
    sm.revenue_7d,
    sm.orders_prev_7d,
    sm.revenue_prev_7d,

    -- Order status
    sm.completed_orders_30d,
    sm.cancelled_orders_30d,
    sm.pending_orders_30d,

    -- All time metrics
    sm.total_orders_all_time,
    sm.total_revenue_all_time,
    sm.total_customers_all_time,
    sm.first_order_date,
    sm.last_order_date,

    -- Ads metrics
    COALESCE(sa.ad_spend_30d, 0) as ad_spend_30d,
    COALESCE(sa.ad_spend_prev_30d, 0) as ad_spend_prev_30d,
    COALESCE(sa.impressions_30d, 0) as impressions_30d,
    COALESCE(sa.clicks_30d, 0) as clicks_30d,
    COALESCE(sa.conversions_30d, 0) as conversions_30d,

    -- Growth rates (MoM)
    SAFE_DIVIDE(sm.orders_30d - sm.orders_prev_30d, NULLIF(sm.orders_prev_30d, 0)) as order_growth_rate_mom,
    SAFE_DIVIDE(sm.revenue_30d - sm.revenue_prev_30d, NULLIF(sm.revenue_prev_30d, 0)) as revenue_growth_rate_mom,
    SAFE_DIVIDE(sm.net_revenue_30d - sm.net_revenue_prev_30d, NULLIF(sm.net_revenue_prev_30d, 0)) as net_revenue_growth_rate_mom,
    SAFE_DIVIDE(sm.customers_30d - sm.customers_prev_30d, NULLIF(sm.customers_prev_30d, 0)) as customer_growth_rate_mom,

    -- Growth rates (WoW)
    SAFE_DIVIDE(sm.orders_7d - sm.orders_prev_7d, NULLIF(sm.orders_prev_7d, 0)) as order_growth_rate_wow,
    SAFE_DIVIDE(sm.revenue_7d - sm.revenue_prev_7d, NULLIF(sm.revenue_prev_7d, 0)) as revenue_growth_rate_wow,

    -- Ad spend growth
    SAFE_DIVIDE(sa.ad_spend_30d - sa.ad_spend_prev_30d, NULLIF(sa.ad_spend_prev_30d, 0)) as ad_spend_growth_rate_mom,

    -- Efficiency metrics
    SAFE_DIVIDE(sm.net_revenue_30d, NULLIF(sa.ad_spend_30d, 0)) as roas_30d,
    SAFE_DIVIDE(sa.ad_spend_30d, NULLIF(sm.completed_orders_30d, 0)) as cpa_30d,
    SAFE_DIVIDE(sm.net_revenue_30d, NULLIF(sm.orders_30d, 0)) as aov_30d,
    SAFE_DIVIDE(sm.completed_orders_30d, NULLIF(sm.orders_30d, 0)) as completion_rate_30d,
    SAFE_DIVIDE(sm.cancelled_orders_30d, NULLIF(sm.orders_30d, 0)) as cancellation_rate_30d,

    -- Performance status
    CASE
        WHEN SAFE_DIVIDE(sm.revenue_30d - sm.revenue_prev_30d, NULLIF(sm.revenue_prev_30d, 0)) > 0.1 THEN 'growing'
        WHEN SAFE_DIVIDE(sm.revenue_30d - sm.revenue_prev_30d, NULLIF(sm.revenue_prev_30d, 0)) < -0.1 THEN 'declining'
        ELSE 'stable'
    END as performance_status,

    CURRENT_TIMESTAMP() as _updated_at
FROM shop_metrics sm
LEFT JOIN shop_ads sa ON sm.platform = sa.platform;


-- Create view for all shops combined
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_shop_performance_total` AS
SELECT
    snapshot_date,
    'all' as platform,
    SUM(orders_30d) as orders_30d,
    SUM(revenue_30d) as revenue_30d,
    SUM(net_revenue_30d) as net_revenue_30d,
    SUM(customers_30d) as customers_30d,
    SUM(items_sold_30d) as items_sold_30d,
    SUM(orders_7d) as orders_7d,
    SUM(revenue_7d) as revenue_7d,
    SUM(total_orders_all_time) as total_orders_all_time,
    SUM(total_revenue_all_time) as total_revenue_all_time,
    SUM(ad_spend_30d) as ad_spend_30d,
    SAFE_DIVIDE(SUM(net_revenue_30d), NULLIF(SUM(ad_spend_30d), 0)) as roas_30d,
    SAFE_DIVIDE(SUM(ad_spend_30d), NULLIF(SUM(completed_orders_30d), 0)) as cpa_30d,
    SAFE_DIVIDE(SUM(net_revenue_30d), NULLIF(SUM(orders_30d), 0)) as aov_30d,
    MAX(_updated_at) as _updated_at
FROM `${project_id}.${dataset_mart}.mart_shop_performance`
GROUP BY snapshot_date;
