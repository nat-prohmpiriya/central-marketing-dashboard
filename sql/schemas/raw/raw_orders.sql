-- Raw Orders Table
-- Stores raw order data from e-commerce platforms (Shopee, Lazada, TikTok Shop)
-- Data is appended with ingestion metadata, no deduplication at this layer

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_raw}.raw_orders` (
    -- Ingestion metadata
    _ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _source_table STRING,
    _batch_id STRING,

    -- Source identification
    platform STRING NOT NULL,
    platform_order_id STRING NOT NULL,

    -- Raw JSON data (preserves original structure)
    raw_data JSON NOT NULL,

    -- Extracted at timestamp from source
    extracted_at TIMESTAMP
)
PARTITION BY DATE(_ingested_at)
CLUSTER BY platform, platform_order_id
OPTIONS (
    description = 'Raw order data from e-commerce platforms',
    labels = [('layer', 'raw'), ('domain', 'orders')]
);


-- Raw Order Items Table
-- Stores raw order item data extracted from orders

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_raw}.raw_order_items` (
    -- Ingestion metadata
    _ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _source_table STRING,
    _batch_id STRING,

    -- Source identification
    platform STRING NOT NULL,
    platform_order_id STRING NOT NULL,
    item_id STRING NOT NULL,

    -- Raw JSON data
    raw_data JSON NOT NULL,

    -- Extracted at timestamp from source
    extracted_at TIMESTAMP
)
PARTITION BY DATE(_ingested_at)
CLUSTER BY platform, platform_order_id
OPTIONS (
    description = 'Raw order item data from e-commerce platforms',
    labels = [('layer', 'raw'), ('domain', 'orders')]
);
