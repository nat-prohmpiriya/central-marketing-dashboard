-- Raw Ads Performance Table
-- Stores raw ads data from advertising platforms (Facebook, Google, TikTok Ads)
-- Data is appended with ingestion metadata, no deduplication at this layer

CREATE TABLE IF NOT EXISTS `${project_id}.${dataset_raw}.raw_ads` (
    -- Ingestion metadata
    _ingested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    _source_table STRING,
    _batch_id STRING,

    -- Source identification
    platform STRING NOT NULL,
    account_id STRING NOT NULL,
    campaign_id STRING,
    adgroup_id STRING,
    ad_id STRING,

    -- Report date
    report_date DATE NOT NULL,

    -- Report level
    level STRING,  -- campaign, adgroup, ad

    -- Raw JSON data (preserves original structure)
    raw_data JSON NOT NULL,

    -- Extracted at timestamp from source
    extracted_at TIMESTAMP
)
PARTITION BY report_date
CLUSTER BY platform, account_id, campaign_id
OPTIONS (
    description = 'Raw ads performance data from advertising platforms',
    labels = [('layer', 'raw'), ('domain', 'ads')]
);
