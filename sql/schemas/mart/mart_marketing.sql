-- Mart Marketing Daily Summary
-- Aggregated daily marketing spend and performance

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_marketing_daily` (
    -- Date dimension
    date DATE NOT NULL,

    -- Platform breakdown
    platform STRING NOT NULL,  -- facebook_ads, google_ads, tiktok_ads, all

    -- Spend metrics (THB)
    total_spend FLOAT64 NOT NULL DEFAULT 0.0,

    -- Reach and awareness
    total_impressions INT64 NOT NULL DEFAULT 0,
    total_reach INT64,

    -- Engagement
    total_clicks INT64 NOT NULL DEFAULT 0,
    avg_ctr FLOAT64,
    avg_cpc FLOAT64,
    avg_cpm FLOAT64,

    -- Conversions
    total_conversions INT64 NOT NULL DEFAULT 0,
    total_conversion_value FLOAT64 NOT NULL DEFAULT 0.0,
    avg_cost_per_conversion FLOAT64,
    avg_conversion_rate FLOAT64,

    -- Video performance
    total_video_views INT64,

    -- Engagement (social)
    total_likes INT64,
    total_comments INT64,
    total_shares INT64,

    -- Campaign counts
    active_campaigns INT64 NOT NULL DEFAULT 0,
    active_ads INT64 NOT NULL DEFAULT 0,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY platform
OPTIONS (
    description = 'Daily marketing spend and performance aggregation',
    labels = [('layer', 'mart'), ('domain', 'marketing')]
);


-- Mart Marketing by Campaign
-- Campaign-level performance aggregation

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_marketing_by_campaign` (
    -- Date dimension
    date DATE NOT NULL,

    -- Campaign identification
    platform STRING NOT NULL,
    account_id STRING NOT NULL,
    campaign_id STRING NOT NULL,
    campaign_name STRING,
    campaign_type STRING,

    -- Spend metrics (THB)
    spend FLOAT64 NOT NULL DEFAULT 0.0,

    -- Performance metrics
    impressions INT64 NOT NULL DEFAULT 0,
    clicks INT64 NOT NULL DEFAULT 0,
    reach INT64,
    ctr FLOAT64,
    cpc FLOAT64,
    cpm FLOAT64,

    -- Conversions
    conversions INT64 NOT NULL DEFAULT 0,
    conversion_value FLOAT64 NOT NULL DEFAULT 0.0,
    cost_per_conversion FLOAT64,
    roas FLOAT64,  -- Return on ad spend

    -- Status
    status STRING,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY platform, account_id, campaign_id
OPTIONS (
    description = 'Daily campaign-level marketing performance',
    labels = [('layer', 'mart'), ('domain', 'marketing')]
);


-- Mart Channel Attribution
-- Marketing channel performance with attribution

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_mart}.mart_channel_attribution` (
    -- Date dimension
    date DATE NOT NULL,

    -- Channel identification
    channel_grouping STRING NOT NULL,
    source STRING,
    medium STRING,

    -- Traffic metrics (from GA4)
    sessions INT64 NOT NULL DEFAULT 0,
    users INT64 NOT NULL DEFAULT 0,
    new_users INT64 NOT NULL DEFAULT 0,
    bounce_rate FLOAT64,
    avg_session_duration FLOAT64,

    -- Conversion metrics
    transactions INT64 NOT NULL DEFAULT 0,
    revenue FLOAT64 NOT NULL DEFAULT 0.0,
    conversion_rate FLOAT64,

    -- Marketing spend (matched from ads)
    attributed_spend FLOAT64 NOT NULL DEFAULT 0.0,

    -- Efficiency metrics
    cost_per_session FLOAT64,
    cost_per_acquisition FLOAT64,
    roas FLOAT64,

    -- Metadata
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY channel_grouping
OPTIONS (
    description = 'Marketing channel performance with attribution',
    labels = [('layer', 'mart'), ('domain', 'marketing')]
);
