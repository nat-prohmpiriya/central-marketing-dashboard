-- Staging GA4 Sessions Table
-- Unified session data from GA4

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_ga4_sessions` (
    -- Primary identifiers
    record_id STRING NOT NULL,
    property_id STRING NOT NULL,
    date DATE NOT NULL,

    -- Traffic source
    source STRING,
    medium STRING,
    campaign STRING,
    channel_grouping STRING NOT NULL,

    -- Session metrics
    sessions INT64 NOT NULL DEFAULT 0,
    engaged_sessions INT64 NOT NULL DEFAULT 0,
    total_users INT64 NOT NULL DEFAULT 0,
    new_users INT64 NOT NULL DEFAULT 0,
    active_users INT64 NOT NULL DEFAULT 0,
    returning_users INT64 NOT NULL DEFAULT 0,

    -- Engagement metrics
    bounce_rate FLOAT64,
    engagement_rate FLOAT64,
    avg_session_duration FLOAT64,
    events_per_session FLOAT64,
    screen_page_views INT64 NOT NULL DEFAULT 0,
    session_duration_total FLOAT64 NOT NULL DEFAULT 0.0,

    -- Metadata
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY property_id, channel_grouping
OPTIONS (
    description = 'Unified GA4 session data',
    labels = [('layer', 'staging'), ('domain', 'analytics')]
);


-- Staging GA4 Traffic Table
-- Traffic summary with channel grouping

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_ga4_traffic` (
    -- Primary identifiers
    record_id STRING NOT NULL,
    property_id STRING NOT NULL,
    date DATE NOT NULL,

    -- Traffic source
    source STRING,
    medium STRING,
    campaign STRING,
    channel_grouping STRING NOT NULL,

    -- Traffic metrics
    sessions INT64 NOT NULL DEFAULT 0,
    total_users INT64 NOT NULL DEFAULT 0,
    new_users INT64 NOT NULL DEFAULT 0,

    -- Engagement metrics
    bounce_rate FLOAT64,
    engagement_rate FLOAT64,
    avg_session_duration FLOAT64,

    -- Ecommerce metrics
    transactions INT64 NOT NULL DEFAULT 0,
    revenue FLOAT64 NOT NULL DEFAULT 0.0,
    avg_order_value FLOAT64,
    conversion_rate FLOAT64,

    -- Metadata
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY property_id, channel_grouping
OPTIONS (
    description = 'Unified GA4 traffic data with channel grouping',
    labels = [('layer', 'staging'), ('domain', 'analytics')]
);


-- Staging GA4 Pages Table
-- Page performance metrics

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_ga4_pages` (
    -- Primary identifiers
    record_id STRING NOT NULL,
    property_id STRING NOT NULL,
    date DATE NOT NULL,

    -- Page information
    page_path STRING NOT NULL,
    page_title STRING,

    -- Page metrics
    page_views INT64 NOT NULL DEFAULT 0,
    unique_page_views INT64 NOT NULL DEFAULT 0,
    sessions INT64 NOT NULL DEFAULT 0,

    -- Engagement metrics
    bounce_rate FLOAT64,
    engagement_rate FLOAT64,
    avg_time_on_page FLOAT64,
    exit_rate FLOAT64,
    entrances INT64 NOT NULL DEFAULT 0,
    exits INT64 NOT NULL DEFAULT 0,

    -- Metadata
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY property_id, page_path
OPTIONS (
    description = 'Unified GA4 page performance data',
    labels = [('layer', 'staging'), ('domain', 'analytics')]
);
