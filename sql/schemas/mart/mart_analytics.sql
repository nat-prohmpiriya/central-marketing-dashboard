-- Mart Website Analytics Daily
-- Aggregated daily website analytics from GA4

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_analytics_daily` (
    -- Date dimension
    date DATE NOT NULL,

    -- Property identification
    property_id STRING NOT NULL,

    -- Traffic summary
    total_sessions INT64 NOT NULL DEFAULT 0,
    engaged_sessions INT64 NOT NULL DEFAULT 0,
    total_users INT64 NOT NULL DEFAULT 0,
    new_users INT64 NOT NULL DEFAULT 0,
    returning_users INT64 NOT NULL DEFAULT 0,

    -- Engagement metrics
    avg_bounce_rate FLOAT64,
    avg_engagement_rate FLOAT64,
    avg_session_duration FLOAT64,
    total_page_views INT64 NOT NULL DEFAULT 0,

    -- E-commerce metrics
    transactions INT64 NOT NULL DEFAULT 0,
    revenue FLOAT64 NOT NULL DEFAULT 0.0,
    conversion_rate FLOAT64,

    -- Channel distribution (JSON for flexibility)
    sessions_by_channel JSON,
    users_by_channel JSON,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY property_id
OPTIONS (
    description = 'Daily website analytics summary from GA4',
    labels = [('layer', 'mart'), ('domain', 'analytics')]
);


-- Mart Top Pages Daily
-- Top performing pages by date

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_top_pages_daily` (
    -- Date dimension
    date DATE NOT NULL,

    -- Property identification
    property_id STRING NOT NULL,

    -- Page identification
    page_path STRING NOT NULL,
    page_title STRING,
    page_rank INT64 NOT NULL,  -- Rank by page views

    -- Page metrics
    page_views INT64 NOT NULL DEFAULT 0,
    unique_page_views INT64 NOT NULL DEFAULT 0,
    sessions INT64 NOT NULL DEFAULT 0,

    -- Engagement
    avg_time_on_page FLOAT64,
    bounce_rate FLOAT64,
    exit_rate FLOAT64,
    entrances INT64 NOT NULL DEFAULT 0,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY property_id, page_rank
OPTIONS (
    description = 'Daily top pages ranking by page views',
    labels = [('layer', 'mart'), ('domain', 'analytics')]
);


-- Mart Traffic Sources Daily
-- Traffic source breakdown

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_traffic_sources_daily` (
    -- Date dimension
    date DATE NOT NULL,

    -- Property identification
    property_id STRING NOT NULL,

    -- Source identification
    channel_grouping STRING NOT NULL,
    source STRING,
    medium STRING,
    campaign STRING,

    -- Traffic metrics
    sessions INT64 NOT NULL DEFAULT 0,
    users INT64 NOT NULL DEFAULT 0,
    new_users INT64 NOT NULL DEFAULT 0,

    -- Engagement
    bounce_rate FLOAT64,
    engagement_rate FLOAT64,
    avg_session_duration FLOAT64,

    -- E-commerce
    transactions INT64 NOT NULL DEFAULT 0,
    revenue FLOAT64 NOT NULL DEFAULT 0.0,
    conversion_rate FLOAT64,

    -- Percentage of total
    pct_of_sessions FLOAT64,
    pct_of_revenue FLOAT64,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY property_id, channel_grouping
OPTIONS (
    description = 'Daily traffic source breakdown',
    labels = [('layer', 'mart'), ('domain', 'analytics')]
);
