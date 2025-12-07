-- Staging Orders Table
-- Unified order data from all e-commerce platforms
-- Deduplication is handled at this layer

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_orders` (
    -- Primary identifiers
    order_id STRING NOT NULL,  -- Format: {platform}_{platform_order_id}
    platform STRING NOT NULL,
    platform_order_id STRING NOT NULL,

    -- Customer information
    customer_id STRING,
    customer_name STRING,
    customer_phone STRING,

    -- Order status
    status STRING NOT NULL,  -- Normalized: pending, confirmed, shipped, completed, cancelled, etc.
    status_raw STRING,  -- Original platform status

    -- Timestamps
    order_date TIMESTAMP NOT NULL,
    paid_date TIMESTAMP,
    shipped_date TIMESTAMP,
    completed_date TIMESTAMP,

    -- Financial (normalized to THB)
    subtotal FLOAT64 NOT NULL DEFAULT 0.0,
    shipping_fee FLOAT64 NOT NULL DEFAULT 0.0,
    discount FLOAT64 NOT NULL DEFAULT 0.0,
    total FLOAT64 NOT NULL DEFAULT 0.0,
    currency STRING NOT NULL DEFAULT 'THB',

    -- Shipping
    shipping_address STRING,
    shipping_method STRING,
    tracking_number STRING,

    -- Item summary
    item_count INT64 NOT NULL DEFAULT 0,

    -- Metadata
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(order_date)
CLUSTER BY platform, status
OPTIONS (
    description = 'Unified order data from all e-commerce platforms',
    labels = [('layer', 'staging'), ('domain', 'orders')]
);


-- Staging Order Items Table
-- Unified order item data

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_order_items` (
    -- Primary identifiers
    item_id STRING NOT NULL,
    order_id STRING NOT NULL,
    platform STRING NOT NULL,

    -- Product information
    product_id STRING NOT NULL,
    sku STRING,
    name STRING NOT NULL,
    variation STRING,

    -- Quantities and pricing
    quantity INT64 NOT NULL DEFAULT 1,
    unit_price FLOAT64 NOT NULL DEFAULT 0.0,
    total_price FLOAT64 NOT NULL DEFAULT 0.0,
    discount FLOAT64 NOT NULL DEFAULT 0.0,

    -- Physical attributes
    weight FLOAT64,

    -- Order reference
    order_date TIMESTAMP,

    -- Metadata
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(order_date)
CLUSTER BY platform, order_id
OPTIONS (
    description = 'Unified order item data from all e-commerce platforms',
    labels = [('layer', 'staging'), ('domain', 'orders')]
);
