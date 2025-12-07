-- Raw Products Table
-- Stores raw product data from e-commerce platforms
-- Data is appended with ingestion metadata, no deduplication at this layer

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_raw}.raw_products` (
    -- Ingestion metadata
    _ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _source_table STRING,
    _batch_id STRING,

    -- Source identification
    platform STRING NOT NULL,
    platform_product_id STRING NOT NULL,
    sku STRING,

    -- Raw JSON data (preserves original structure)
    raw_data JSON NOT NULL,

    -- Extracted at timestamp from source
    extracted_at TIMESTAMP
)
PARTITION BY DATE(_ingested_at)
CLUSTER BY platform, platform_product_id
OPTIONS (
    description = 'Raw product data from e-commerce platforms',
    labels = [('layer', 'raw'), ('domain', 'products')]
);
