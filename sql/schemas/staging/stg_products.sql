-- Staging Products Table
-- Unified product data from all e-commerce platforms

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_products` (
    -- Primary identifiers
    product_id STRING NOT NULL,  -- Format: {platform}_{platform_product_id}
    platform STRING NOT NULL,
    platform_product_id STRING NOT NULL,

    -- SKU information
    sku STRING,
    seller_sku STRING,
    master_sku STRING,  -- Mapped unified SKU

    -- Product details
    name STRING NOT NULL,
    variation STRING,
    category STRING,
    brand STRING,

    -- Pricing (normalized to THB)
    unit_price FLOAT64 NOT NULL DEFAULT 0.0,
    original_price FLOAT64,
    discount_price FLOAT64,
    currency STRING NOT NULL DEFAULT 'THB',

    -- Physical attributes
    weight FLOAT64,
    weight_unit STRING NOT NULL DEFAULT 'kg',

    -- Status
    is_active BOOL NOT NULL DEFAULT TRUE,
    is_mapped BOOL NOT NULL DEFAULT FALSE,

    -- Timestamps
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(last_seen_at)
CLUSTER BY platform, is_mapped
OPTIONS (
    description = 'Unified product data from all e-commerce platforms',
    labels = [('layer', 'staging'), ('domain', 'products')]
);


-- Staging SKU Mappings Table
-- Cross-platform SKU mapping reference

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_sku_mappings` (
    -- Primary identifiers
    master_sku STRING NOT NULL,
    platform STRING NOT NULL,
    platform_sku STRING NOT NULL,

    -- Product reference
    product_name STRING,
    variation STRING,

    -- Metadata
    notes STRING,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
CLUSTER BY master_sku, platform
OPTIONS (
    description = 'Cross-platform SKU mapping reference',
    labels = [('layer', 'staging'), ('domain', 'products')]
);
