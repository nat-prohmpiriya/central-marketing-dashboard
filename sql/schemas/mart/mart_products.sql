-- Mart Product Catalog
-- Master product catalog with cross-platform mapping

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_product_catalog` (
    -- Master identification
    master_sku STRING NOT NULL,
    product_name STRING NOT NULL,
    brand STRING,
    category STRING,

    -- Platform availability
    platforms ARRAY<STRING>,
    platform_skus JSON,  -- {platform: sku}

    -- Pricing summary (THB)
    min_price FLOAT64,
    max_price FLOAT64,
    avg_price FLOAT64,

    -- Inventory status
    is_active BOOL NOT NULL DEFAULT TRUE,
    platforms_active INT64 NOT NULL DEFAULT 0,

    -- Performance summary (last 30 days)
    total_units_sold INT64 NOT NULL DEFAULT 0,
    total_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    avg_daily_sales FLOAT64,

    -- Timestamps
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY master_sku, is_active
OPTIONS (
    description = 'Master product catalog with cross-platform SKU mapping',
    labels = [('layer', 'mart'), ('domain', 'products')]
);


-- Mart Product Performance
-- Daily product performance metrics

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_product_performance` (
    -- Date dimension
    date DATE NOT NULL,

    -- Product identification
    master_sku STRING NOT NULL,
    product_name STRING NOT NULL,

    -- Sales metrics (aggregated across platforms)
    units_sold INT64 NOT NULL DEFAULT 0,
    gross_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    net_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    order_count INT64 NOT NULL DEFAULT 0,

    -- Platform breakdown
    units_by_platform JSON,  -- {platform: units}
    revenue_by_platform JSON,  -- {platform: revenue}

    -- Pricing metrics
    avg_selling_price FLOAT64,
    min_selling_price FLOAT64,
    max_selling_price FLOAT64,

    -- Performance indicators
    rank_by_units INT64,
    rank_by_revenue INT64,
    pct_of_total_revenue FLOAT64,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY master_sku
OPTIONS (
    description = 'Daily product performance metrics across all platforms',
    labels = [('layer', 'mart'), ('domain', 'products')]
);


-- Mart Unmapped Products
-- Products without master SKU mapping for review

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_unmapped_products` (
    -- Product identification
    platform STRING NOT NULL,
    platform_product_id STRING NOT NULL,
    platform_sku STRING,
    product_name STRING NOT NULL,
    variation STRING,

    -- Sales impact
    total_units_sold INT64 NOT NULL DEFAULT 0,
    total_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    order_count INT64 NOT NULL DEFAULT 0,

    -- Timeline
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,

    -- Review status
    review_status STRING NOT NULL DEFAULT 'pending',  -- pending, reviewed, ignored
    suggested_master_sku STRING,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY platform, review_status
OPTIONS (
    description = 'Unmapped products requiring SKU mapping review',
    labels = [('layer', 'mart'), ('domain', 'products')]
);
