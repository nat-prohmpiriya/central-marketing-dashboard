-- Raw GA4 Sessions Table
-- Stores raw GA4 session/traffic data
-- Data is appended with ingestion metadata, no deduplication at this layer

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_raw}.raw_ga4_sessions` (
    -- Ingestion metadata
    _ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _source_table STRING,
    _batch_id STRING,

    -- Source identification
    property_id STRING NOT NULL,
    report_type STRING,  -- sessions, traffic, pages

    -- Report date
    report_date DATE NOT NULL,

    -- Dimensions for clustering
    source STRING,
    medium STRING,

    -- Raw JSON data (preserves original structure)
    raw_data JSON NOT NULL,

    -- Extracted at timestamp from source
    extracted_at TIMESTAMP
)
PARTITION BY report_date
CLUSTER BY property_id, source, medium
OPTIONS (
    description = 'Raw GA4 session and traffic data',
    labels = [('layer', 'raw'), ('domain', 'analytics')]
);


-- Raw GA4 Pages Table
-- Stores raw GA4 page performance data

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_raw}.raw_ga4_pages` (
    -- Ingestion metadata
    _ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _source_table STRING,
    _batch_id STRING,

    -- Source identification
    property_id STRING NOT NULL,

    -- Report date
    report_date DATE NOT NULL,

    -- Page dimension for clustering
    page_path STRING,

    -- Raw JSON data (preserves original structure)
    raw_data JSON NOT NULL,

    -- Extracted at timestamp from source
    extracted_at TIMESTAMP
)
PARTITION BY report_date
CLUSTER BY property_id, page_path
OPTIONS (
    description = 'Raw GA4 page performance data',
    labels = [('layer', 'raw'), ('domain', 'analytics')]
);
