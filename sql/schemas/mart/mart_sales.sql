-- Mart Sales Daily Summary
-- Aggregated daily sales metrics across all platforms

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_sales_daily` (
    -- Date dimension
    date DATE NOT NULL,

    -- Platform breakdown
    platform STRING NOT NULL,  -- shopee, lazada, tiktok_shop, all

    -- Order metrics
    total_orders INT64 NOT NULL DEFAULT 0,
    completed_orders INT64 NOT NULL DEFAULT 0,
    cancelled_orders INT64 NOT NULL DEFAULT 0,
    pending_orders INT64 NOT NULL DEFAULT 0,

    -- Revenue metrics (THB)
    gross_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    net_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    total_discount FLOAT64 NOT NULL DEFAULT 0.0,
    total_shipping_fee FLOAT64 NOT NULL DEFAULT 0.0,

    -- Item metrics
    total_items_sold INT64 NOT NULL DEFAULT 0,
    avg_items_per_order FLOAT64,

    -- Customer metrics
    unique_customers INT64 NOT NULL DEFAULT 0,
    new_customers INT64 NOT NULL DEFAULT 0,
    returning_customers INT64 NOT NULL DEFAULT 0,

    -- Average metrics
    avg_order_value FLOAT64,
    avg_item_value FLOAT64,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY platform
OPTIONS (
    description = 'Daily sales aggregation across all e-commerce platforms',
    labels = [('layer', 'mart'), ('domain', 'sales')]
);


-- Mart Sales by Product
-- Product-level sales aggregation

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_sales_by_product` (
    -- Date dimension
    date DATE NOT NULL,

    -- Product identification
    master_sku STRING,
    product_name STRING NOT NULL,
    platform STRING NOT NULL,

    -- Sales metrics
    quantity_sold INT64 NOT NULL DEFAULT 0,
    gross_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    net_revenue FLOAT64 NOT NULL DEFAULT 0.0,
    total_discount FLOAT64 NOT NULL DEFAULT 0.0,

    -- Order metrics
    order_count INT64 NOT NULL DEFAULT 0,

    -- Average metrics
    avg_selling_price FLOAT64,
    avg_discount_percent FLOAT64,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY platform, master_sku
OPTIONS (
    description = 'Daily product-level sales aggregation',
    labels = [('layer', 'mart'), ('domain', 'sales')]
);


-- Mart Sales by Customer Segment
-- Customer segmentation based on purchase behavior

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_customer_segments` (
    -- Date of segmentation
    snapshot_date DATE NOT NULL,

    -- Customer identification
    customer_id STRING NOT NULL,
    platform STRING NOT NULL,

    -- RFM metrics
    recency_days INT64 NOT NULL DEFAULT 0,
    frequency INT64 NOT NULL DEFAULT 0,
    monetary_value FLOAT64 NOT NULL DEFAULT 0.0,

    -- RFM scores (1-5)
    recency_score INT64,
    frequency_score INT64,
    monetary_score INT64,
    rfm_segment STRING,  -- Champions, Loyal, At Risk, etc.

    -- Historical metrics
    first_order_date DATE,
    last_order_date DATE,
    total_orders INT64 NOT NULL DEFAULT 0,
    total_spent FLOAT64 NOT NULL DEFAULT 0.0,
    avg_order_value FLOAT64,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY snapshot_date
CLUSTER BY platform, rfm_segment
OPTIONS (
    description = 'Customer segmentation based on RFM analysis',
    labels = [('layer', 'mart'), ('domain', 'sales')]
);
