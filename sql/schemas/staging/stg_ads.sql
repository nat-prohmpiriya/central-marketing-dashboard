-- Staging Ads Performance Table
-- Unified ads data from all advertising platforms

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_staging}.stg_ads` (
    -- Primary identifiers
    record_id STRING NOT NULL,
    platform STRING NOT NULL,  -- facebook_ads, google_ads, tiktok_ads
    account_id STRING NOT NULL,
    campaign_id STRING NOT NULL,

    -- Campaign hierarchy
    campaign_name STRING,
    adgroup_id STRING,
    adgroup_name STRING,
    ad_id STRING,
    ad_name STRING,

    -- Performance metrics
    impressions INT64 NOT NULL DEFAULT 0,
    clicks INT64 NOT NULL DEFAULT 0,
    reach INT64,
    ctr FLOAT64,  -- Click-through rate (%)
    cpc FLOAT64,  -- Cost per click (THB)
    cpm FLOAT64,  -- Cost per mille (THB)

    -- Cost metrics (normalized to THB)
    spend FLOAT64 NOT NULL DEFAULT 0.0,
    spend_raw FLOAT64 NOT NULL DEFAULT 0.0,
    currency STRING NOT NULL DEFAULT 'THB',
    currency_raw STRING,

    -- Conversion metrics
    conversions INT64 NOT NULL DEFAULT 0,
    conversion_value FLOAT64 NOT NULL DEFAULT 0.0,
    cost_per_conversion FLOAT64,
    conversion_rate FLOAT64,

    -- Video metrics
    video_views INT64,
    video_views_p25 INT64,
    video_views_p50 INT64,
    video_views_p75 INT64,
    video_views_p100 INT64,

    -- Engagement metrics (for social platforms)
    likes INT64,
    comments INT64,
    shares INT64,
    follows INT64,

    -- Status and type
    status STRING,  -- active, paused, deleted
    campaign_type STRING,
    objective STRING,

    -- Date information
    date DATE NOT NULL,
    date_start DATE,
    date_end DATE,
    level STRING NOT NULL DEFAULT 'ad',  -- campaign, adgroup, ad

    -- Metadata
    extracted_at TIMESTAMP,
    transformed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY date
CLUSTER BY platform, account_id, campaign_id
OPTIONS (
    description = 'Unified ads performance data from all advertising platforms',
    labels = [('layer', 'staging'), ('domain', 'ads')]
);
