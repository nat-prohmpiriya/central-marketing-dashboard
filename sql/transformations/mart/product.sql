-- Mart: Product Performance
-- Product-level sales metrics with cross-platform aggregation
-- Dependencies: stg_orders, stg_order_items, stg_products, stg_sku_mappings

-- Product Performance Summary
CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_product_performance`
PARTITION BY date
CLUSTER BY master_sku, platform
AS
WITH order_items_enriched AS (
    SELECT
        oi.order_id,
        oi.platform,
        oi.product_id,
        oi.sku,
        oi.name as product_name,
        oi.variation,
        oi.quantity,
        oi.unit_price,
        oi.total_price,
        oi.discount,
        oi.order_date,
        -- Get master SKU from mapping
        COALESCE(sm.master_sku, oi.sku) as master_sku,
        -- Get order status
        o.status as order_status
    FROM `${project_id}.${dataset_staging}.stg_order_items` oi
    LEFT JOIN `${project_id}.${dataset_staging}.stg_sku_mappings` sm
        ON oi.platform = sm.platform AND oi.sku = sm.platform_sku
    LEFT JOIN `${project_id}.${dataset_staging}.stg_orders` o
        ON oi.order_id = o.order_id
    WHERE oi.order_date >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
),
daily_product_sales AS (
    SELECT
        DATE(order_date) as date,
        master_sku,
        platform,
        product_name,
        variation,
        -- Total sales (all orders)
        SUM(quantity) as units_sold,
        SUM(total_price) as gross_revenue,
        SUM(total_price - discount) as net_revenue,
        SUM(discount) as total_discount,
        COUNT(DISTINCT order_id) as order_count,
        -- Completed sales only
        SUM(CASE WHEN order_status = 'completed' THEN quantity ELSE 0 END) as units_completed,
        SUM(CASE WHEN order_status = 'completed' THEN total_price ELSE 0 END) as revenue_completed,
        -- Cancelled
        SUM(CASE WHEN order_status = 'cancelled' THEN quantity ELSE 0 END) as units_cancelled,
        -- Average metrics
        AVG(unit_price) as avg_unit_price,
        AVG(quantity) as avg_quantity_per_order
    FROM order_items_enriched
    GROUP BY 1, 2, 3, 4, 5
),
product_info AS (
    SELECT
        COALESCE(sm.master_sku, p.sku) as master_sku,
        p.platform,
        FIRST_VALUE(p.name) OVER (PARTITION BY COALESCE(sm.master_sku, p.sku) ORDER BY p.last_seen_at DESC) as canonical_name,
        FIRST_VALUE(p.category) OVER (PARTITION BY COALESCE(sm.master_sku, p.sku) ORDER BY p.last_seen_at DESC) as category,
        FIRST_VALUE(p.brand) OVER (PARTITION BY COALESCE(sm.master_sku, p.sku) ORDER BY p.last_seen_at DESC) as brand,
        p.unit_price as current_price,
        p.is_active
    FROM `${project_id}.${dataset_staging}.stg_products` p
    LEFT JOIN `${project_id}.${dataset_staging}.stg_sku_mappings` sm
        ON p.platform = sm.platform AND p.sku = sm.platform_sku
),
product_history AS (
    -- Get previous period for comparison
    SELECT
        master_sku,
        platform,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN units_sold ELSE 0 END) as units_7d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
                  AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY) THEN units_sold ELSE 0 END) as units_prev_7d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN units_sold ELSE 0 END) as units_30d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
                  AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN units_sold ELSE 0 END) as units_prev_30d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN net_revenue ELSE 0 END) as revenue_30d,
        SUM(CASE WHEN date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
                  AND date < DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN net_revenue ELSE 0 END) as revenue_prev_30d
    FROM daily_product_sales
    GROUP BY master_sku, platform
)
SELECT
    dps.date,
    dps.master_sku,
    dps.platform,
    dps.product_name,
    dps.variation,

    -- Product info
    pi.canonical_name,
    pi.category,
    pi.brand,
    pi.current_price,
    pi.is_active,

    -- Daily sales metrics
    dps.units_sold,
    dps.gross_revenue,
    dps.net_revenue,
    dps.total_discount,
    dps.order_count,
    dps.units_completed,
    dps.revenue_completed,
    dps.units_cancelled,

    -- Average metrics
    dps.avg_unit_price,
    dps.avg_quantity_per_order,
    SAFE_DIVIDE(dps.net_revenue, NULLIF(dps.order_count, 0)) as avg_order_value,
    SAFE_DIVIDE(dps.total_discount, NULLIF(dps.gross_revenue, 0)) as discount_rate,

    -- Historical comparison
    ph.units_7d,
    ph.units_prev_7d,
    SAFE_DIVIDE(ph.units_7d - ph.units_prev_7d, NULLIF(ph.units_prev_7d, 0)) as units_growth_wow,
    ph.units_30d,
    ph.units_prev_30d,
    SAFE_DIVIDE(ph.units_30d - ph.units_prev_30d, NULLIF(ph.units_prev_30d, 0)) as units_growth_mom,
    ph.revenue_30d,
    ph.revenue_prev_30d,
    SAFE_DIVIDE(ph.revenue_30d - ph.revenue_prev_30d, NULLIF(ph.revenue_prev_30d, 0)) as revenue_growth_mom,

    -- Cancellation rate
    SAFE_DIVIDE(dps.units_cancelled, NULLIF(dps.units_sold, 0)) as cancellation_rate,

    -- Completion rate
    SAFE_DIVIDE(dps.units_completed, NULLIF(dps.units_sold, 0)) as completion_rate,

    CURRENT_TIMESTAMP() as _updated_at
FROM daily_product_sales dps
LEFT JOIN product_info pi
    ON dps.master_sku = pi.master_sku AND dps.platform = pi.platform
LEFT JOIN product_history ph
    ON dps.master_sku = ph.master_sku AND dps.platform = ph.platform;


-- Cross-Platform Product Performance (aggregated by master_sku)
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_product_cross_platform` AS
SELECT
    master_sku,
    ANY_VALUE(canonical_name) as product_name,
    ANY_VALUE(category) as category,
    ANY_VALUE(brand) as brand,
    ARRAY_AGG(DISTINCT platform) as platforms,
    COUNT(DISTINCT platform) as platform_count,
    SUM(units_30d) as total_units_30d,
    SUM(revenue_30d) as total_revenue_30d,
    -- Per platform breakdown
    SUM(CASE WHEN platform = 'shopee' THEN units_30d ELSE 0 END) as shopee_units_30d,
    SUM(CASE WHEN platform = 'lazada' THEN units_30d ELSE 0 END) as lazada_units_30d,
    SUM(CASE WHEN platform = 'tiktok_shop' THEN units_30d ELSE 0 END) as tiktok_units_30d,
    SUM(CASE WHEN platform = 'shopee' THEN revenue_30d ELSE 0 END) as shopee_revenue_30d,
    SUM(CASE WHEN platform = 'lazada' THEN revenue_30d ELSE 0 END) as lazada_revenue_30d,
    SUM(CASE WHEN platform = 'tiktok_shop' THEN revenue_30d ELSE 0 END) as tiktok_revenue_30d,
    -- Growth
    AVG(units_growth_mom) as avg_units_growth_mom,
    AVG(revenue_growth_mom) as avg_revenue_growth_mom
FROM `${project_id}.${dataset_mart}.mart_product_performance`
WHERE date = (SELECT MAX(date) FROM `${project_id}.${dataset_mart}.mart_product_performance`)
GROUP BY master_sku
ORDER BY total_revenue_30d DESC;


-- Top Products View
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_top_products` AS
SELECT
    master_sku,
    platform,
    product_name,
    category,
    brand,
    SUM(units_sold) as total_units,
    SUM(net_revenue) as total_revenue,
    AVG(avg_unit_price) as avg_price,
    AVG(discount_rate) as avg_discount_rate,
    AVG(completion_rate) as avg_completion_rate,
    MAX(units_growth_wow) as latest_growth_wow,
    MAX(units_growth_mom) as latest_growth_mom
FROM `${project_id}.${dataset_mart}.mart_product_performance`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY master_sku, platform, product_name, category, brand
ORDER BY total_revenue DESC
LIMIT 100;


-- Product Performance Trend
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_product_trend` AS
SELECT
    date,
    master_sku,
    platform,
    product_name,
    units_sold,
    net_revenue,
    -- 7-day rolling
    SUM(units_sold) OVER (
        PARTITION BY master_sku, platform
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as units_7d_rolling,
    SUM(net_revenue) OVER (
        PARTITION BY master_sku, platform
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as revenue_7d_rolling
FROM `${project_id}.${dataset_mart}.mart_product_performance`
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
ORDER BY date DESC, master_sku, platform;


-- Category Performance Summary
CREATE OR REPLACE VIEW `${project_id}.${dataset_mart}.v_category_performance` AS
SELECT
    category,
    platform,
    COUNT(DISTINCT master_sku) as product_count,
    SUM(units_30d) as total_units_30d,
    SUM(revenue_30d) as total_revenue_30d,
    AVG(avg_unit_price) as avg_price,
    AVG(discount_rate) as avg_discount_rate,
    AVG(completion_rate) as avg_completion_rate,
    AVG(units_growth_mom) as avg_growth_mom
FROM `${project_id}.${dataset_mart}.mart_product_performance`
WHERE date = (SELECT MAX(date) FROM `${project_id}.${dataset_mart}.mart_product_performance`)
  AND category IS NOT NULL
GROUP BY category, platform
ORDER BY total_revenue_30d DESC;
