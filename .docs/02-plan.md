# Technical Plan: Centralized Marketing Dashboard

## Overview

**Document Type:** Technical Architecture & Implementation Plan
**Phase:** Phase 1 - Single Tenant MVP
**Last Updated:** December 2025

### Reference Documents
- Product Specification: `.docs/01-spec.md`

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 DATA SOURCES                                     │
├──────────────────────────┬──────────────────────────┬───────────────────────────┤
│   E-commerce Platforms   │   Advertising Platforms  │   Analytics Platforms     │
│  ┌────────┐ ┌────────┐   │  ┌────────┐ ┌────────┐   │  ┌─────────────────────┐  │
│  │ Shopee │ │ Lazada │   │  │Facebook│ │ Google │   │  │ Google Analytics 4 │  │
│  └───┬────┘ └───┬────┘   │  │  Ads   │ │  Ads   │   │  │       (GA4)         │  │
│      │          │        │  └───┬────┘ └───┬────┘   │  └──────────┬──────────┘  │
│  ┌───┴────┐ ┌───┴────┐   │  ┌───┴────┐ ┌───┴────┐   │             │             │
│  │ TikTok │ │  LINE  │   │  │ TikTok │ │  LINE  │   │             │             │
│  │  Shop  │ │  Shop  │   │  │  Ads   │ │  Ads   │   │             │             │
│  └───┬────┘ └───┬────┘   │  └───┬────┘ └───┬────┘   │             │             │
└──────┼──────────┼────────┴──────┼──────────┼────────┴─────────────┼─────────────┘
       │          │               │          │                      │
       ▼          ▼               ▼          ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ETL LAYER (Hybrid: Airbyte + Python)                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌───────────────────────────────┐    ┌───────────────────────────────┐         │
│  │         AIRBYTE               │    │         PYTHON SCRIPTS        │         │
│  │  (Pre-built Connectors)       │    │    (Custom Extractors)        │         │
│  ├───────────────────────────────┤    ├───────────────────────────────┤         │
│  │  • Facebook Ads               │    │  • Shopee Orders/Products     │         │
│  │  • Google Ads                 │    │  • Lazada Orders/Products     │         │
│  │  • Google Analytics 4         │    │  • TikTok Shop                │         │
│  │  • TikTok Ads (50+ streams)   │    │  • LINE Ads                   │         │
│  │                               │    │  • Shopee/Lazada Ads          │         │
│  └───────────────┬───────────────┘    └───────────────┬───────────────┘         │
│                  │                                    │                          │
│                  └────────────────┬───────────────────┘                          │
│                                   ▼                                              │
│                    ┌─────────────────────────────┐                               │
│                    │     Transformers (Python)   │                               │
│                    │   • Data Cleaning           │                               │
│                    │   • Normalization           │                               │
│                    │   • SKU Mapping             │                               │
│                    └─────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          DATA WAREHOUSE (BigQuery)                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           RAW LAYER (raw_*)                               │  │
│  │  raw_shopee_orders │ raw_facebook_ads │ raw_google_ads │ raw_ga4_events   │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                         │
│                                        ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                        STAGING LAYER (stg_*)                              │  │
│  │  stg_orders │ stg_ads_performance │ stg_ga4_sessions │ stg_ga4_traffic    │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
│                                        │                                         │
│                                        ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                          MART LAYER (mart_*)                              │  │
│  │  mart_daily_performance │ mart_shop_metrics │ mart_website_analytics      │  │
│  │  mart_ads_summary │ mart_cross_channel_attribution │ mart_ai_recommendations│ │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         VISUALIZATION (Looker Studio)                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │Executive │ │  Shop    │ │   Ads    │ │ Product  │ │  GA4     │  (5 pages)  │
│  │ Overview │ │Performnce│ │ Overview │ │Analytics │ │Analytics │    MVP      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐               │
│  │  Phase 2: Facebook Deep Dive, Google Deep Dive,            │               │
│  │           TikTok Deep Dive, AI Insights                     │               │
│  └─────────────────────────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| **ETL - Pre-built** | Airbyte (Self-hosted/Cloud) | Pre-built connectors for Facebook, Google Ads, GA4 |
| **ETL - Custom** | Python 3.11+ | Custom extractors for Shopee, Lazada, TikTok |
| **Data Warehouse** | Google BigQuery | Serverless, scalable, cost-effective |
| **Orchestration** | Cloud Scheduler + Cloud Functions | Serverless, low maintenance |
| **Dashboard** | Google Looker Studio | Free, native BigQuery integration |
| **Version Control** | Git + GitHub | Standard practice |
| **Secrets Management** | Google Secret Manager | Secure API credentials |
| **Monitoring** | Cloud Logging (basic) | Manual monitoring for MVP (Phase 2: Cloud Monitoring) |

### 1.3 Airbyte vs Python Decision Matrix

| Platform | Airbyte Connector | Python Custom | Decision | Reason |
|----------|-------------------|---------------|----------|--------|
| Facebook Ads | ✅ Official (11 streams) | ❌ | **Airbyte** | Mature connector, handles pagination & rate limits |
| Google Ads | ✅ Official (19 tables) | ❌ | **Airbyte** | Complex API, connector handles GAQL |
| Google Analytics 4 | ✅ Official | ❌ | **Airbyte** | Native BigQuery export also available |
| TikTok Ads | ✅ Official (50+ streams) | ❌ | **Airbyte** | Full support: campaigns, ad groups, ads, reports by demographics |
| Shopee | ❌ None | ✅ | **Python** | No connector available |
| Lazada | ❌ None | ✅ | **Python** | No connector available |
| TikTok Shop | ❌ None | ✅ | **Python** | TikTok Marketing ≠ TikTok Shop (different API) |
| LINE Ads | ❌ None | ✅ | **Python** | No connector available |
| Shopee Ads | ❌ None | ✅ | **Python** | No connector available |
| Lazada Ads | ❌ None | ✅ | **Python** | No connector available |

> **Note:** TikTok Marketing connector ใน Airbyte รองรับ TikTok Ads (โฆษณา) แต่ไม่รองรับ TikTok Shop (ร้านค้า) ซึ่งเป็นคนละ API

---

## 2. Data Model / Schema

### 2.1 Raw Layer Tables

```sql
-- raw_shopee_orders
CREATE TABLE raw.shopee_orders (
    _ingested_at TIMESTAMP,
    _source_file STRING,
    order_id STRING,
    order_sn STRING,
    shop_id STRING,
    buyer_username STRING,
    order_status STRING,
    payment_method STRING,
    total_amount FLOAT64,
    currency STRING,
    create_time TIMESTAMP,
    update_time TIMESTAMP,
    items ARRAY<STRUCT<
        item_id STRING,
        item_name STRING,
        item_sku STRING,
        model_quantity_purchased INT64,
        model_original_price FLOAT64,
        model_discounted_price FLOAT64
    >>,
    raw_json STRING
);

-- raw_lazada_orders
CREATE TABLE raw.lazada_orders (
    _ingested_at TIMESTAMP,
    _source_file STRING,
    order_id STRING,
    order_number STRING,
    seller_id STRING,
    customer_name STRING,
    status STRING,
    payment_method STRING,
    price FLOAT64,
    currency STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    items ARRAY<STRUCT<
        id STRING,
        name STRING,
        sku STRING,
        quantity INT64,
        item_price FLOAT64,
        paid_price FLOAT64
    >>,
    raw_json STRING
);

-- raw_tiktok_orders
CREATE TABLE raw.tiktok_orders (
    _ingested_at TIMESTAMP,
    _source_file STRING,
    order_id STRING,
    shop_id STRING,
    buyer_email STRING,
    order_status STRING,
    payment_method STRING,
    total_amount FLOAT64,
    currency STRING,
    create_time TIMESTAMP,
    update_time TIMESTAMP,
    items ARRAY<STRUCT<
        product_id STRING,
        product_name STRING,
        sku_id STRING,
        quantity INT64,
        sale_price FLOAT64
    >>,
    raw_json STRING
);

-- raw_facebook_ads
CREATE TABLE raw.facebook_ads (
    _ingested_at TIMESTAMP,
    _date DATE,
    account_id STRING,
    account_name STRING,
    campaign_id STRING,
    campaign_name STRING,
    adset_id STRING,
    adset_name STRING,
    ad_id STRING,
    ad_name STRING,
    impressions INT64,
    clicks INT64,
    spend FLOAT64,
    reach INT64,
    frequency FLOAT64,
    cpc FLOAT64,
    cpm FLOAT64,
    ctr FLOAT64,
    conversions INT64,
    conversion_value FLOAT64,
    actions ARRAY<STRUCT<
        action_type STRING,
        value INT64
    >>,
    raw_json STRING
);

-- raw_google_ads
CREATE TABLE raw.google_ads (
    _ingested_at TIMESTAMP,
    _date DATE,
    customer_id STRING,
    customer_name STRING,
    campaign_id STRING,
    campaign_name STRING,
    campaign_type STRING,
    ad_group_id STRING,
    ad_group_name STRING,
    ad_id STRING,
    impressions INT64,
    clicks INT64,
    cost_micros INT64,
    conversions FLOAT64,
    conversion_value FLOAT64,
    search_impression_share FLOAT64,
    quality_score INT64,
    raw_json STRING
);

-- raw_tiktok_ads
CREATE TABLE raw.tiktok_ads (
    _ingested_at TIMESTAMP,
    _date DATE,
    advertiser_id STRING,
    advertiser_name STRING,
    campaign_id STRING,
    campaign_name STRING,
    adgroup_id STRING,
    adgroup_name STRING,
    ad_id STRING,
    ad_name STRING,
    impressions INT64,
    clicks INT64,
    spend FLOAT64,
    reach INT64,
    video_views INT64,
    likes INT64,
    shares INT64,
    comments INT64,
    conversions INT64,
    conversion_value FLOAT64,
    raw_json STRING
);

-- raw_ga4_events (from Airbyte or BigQuery Export)
CREATE TABLE raw.ga4_events (
    _ingested_at TIMESTAMP,
    event_date DATE,
    event_timestamp TIMESTAMP,
    event_name STRING,
    event_params ARRAY<STRUCT<
        key STRING,
        value STRUCT<
            string_value STRING,
            int_value INT64,
            float_value FLOAT64,
            double_value FLOAT64
        >
    >>,
    user_pseudo_id STRING,
    user_id STRING,
    device STRUCT<
        category STRING,
        mobile_brand_name STRING,
        mobile_model_name STRING,
        operating_system STRING,
        operating_system_version STRING,
        browser STRING,
        browser_version STRING
    >,
    geo STRUCT<
        country STRING,
        region STRING,
        city STRING
    >,
    traffic_source STRUCT<
        source STRING,
        medium STRING,
        campaign STRING
    >,
    ecommerce STRUCT<
        transaction_id STRING,
        total_item_quantity INT64,
        purchase_revenue FLOAT64,
        items ARRAY<STRUCT<
            item_id STRING,
            item_name STRING,
            item_category STRING,
            price FLOAT64,
            quantity INT64
        >>
    >,
    platform STRING,
    stream_id STRING,
    raw_json STRING
);
```

### 2.2 Staging Layer Tables

```sql
-- stg_orders (unified orders from all platforms)
CREATE TABLE staging.orders (
    order_id STRING,
    platform STRING,  -- 'shopee', 'lazada', 'tiktok', etc.
    shop_id STRING,
    shop_name STRING,
    order_status STRING,
    order_status_normalized STRING,  -- 'completed', 'pending', 'cancelled', 'refunded'
    payment_method STRING,
    gross_amount FLOAT64,
    discount_amount FLOAT64,
    net_amount FLOAT64,
    currency STRING,
    amount_thb FLOAT64,  -- normalized to THB
    order_date DATE,
    order_timestamp TIMESTAMP,
    updated_at TIMESTAMP,
    _ingested_at TIMESTAMP
);

-- stg_order_items
CREATE TABLE staging.order_items (
    order_id STRING,
    platform STRING,
    item_id STRING,
    sku STRING,
    sku_normalized STRING,  -- mapped SKU across platforms
    product_name STRING,
    quantity INT64,
    unit_price FLOAT64,
    unit_price_thb FLOAT64,
    total_price FLOAT64,
    total_price_thb FLOAT64,
    _ingested_at TIMESTAMP
);

-- stg_ads_performance (unified ads from all platforms)
CREATE TABLE staging.ads_performance (
    date DATE,
    platform STRING,  -- 'facebook', 'google', 'tiktok', 'line', 'shopee_ads', 'lazada_ads'
    account_id STRING,
    account_name STRING,
    campaign_id STRING,
    campaign_name STRING,
    campaign_type STRING,
    adset_id STRING,
    adset_name STRING,
    ad_id STRING,
    ad_name STRING,
    impressions INT64,
    clicks INT64,
    spend FLOAT64,
    spend_thb FLOAT64,
    conversions INT64,
    conversion_value FLOAT64,
    conversion_value_thb FLOAT64,
    reach INT64,
    video_views INT64,
    engagement INT64,
    _ingested_at TIMESTAMP
);

-- stg_products (master product list with SKU mapping)
CREATE TABLE staging.products (
    sku_master STRING,  -- unified SKU
    product_name STRING,
    category STRING,
    brand STRING,
    cost FLOAT64,
    platforms ARRAY<STRUCT<
        platform STRING,
        platform_sku STRING,
        platform_product_id STRING,
        current_price FLOAT64,
        stock_quantity INT64
    >>,
    _updated_at TIMESTAMP
);

-- stg_shops (shop master)
CREATE TABLE staging.shops (
    shop_id STRING,
    platform STRING,
    shop_name STRING,
    shop_url STRING,
    is_active BOOL,
    _updated_at TIMESTAMP
);

-- stg_ga4_sessions (aggregated from GA4 events)
CREATE TABLE staging.ga4_sessions (
    date DATE,
    session_id STRING,
    user_pseudo_id STRING,
    session_start TIMESTAMP,
    session_end TIMESTAMP,
    session_duration_seconds INT64,
    pageviews INT64,
    events_count INT64,
    -- Traffic source
    source STRING,
    medium STRING,
    campaign STRING,
    channel_grouping STRING,  -- 'Organic Search', 'Paid Search', 'Direct', 'Social', etc.
    -- Device
    device_category STRING,
    operating_system STRING,
    browser STRING,
    -- Geography
    country STRING,
    city STRING,
    -- Engagement
    is_engaged BOOL,
    is_bounced BOOL,
    -- Conversion
    has_purchase BOOL,
    purchase_revenue FLOAT64,
    _ingested_at TIMESTAMP
);

-- stg_ga4_traffic (daily traffic summary)
CREATE TABLE staging.ga4_traffic (
    date DATE,
    source STRING,
    medium STRING,
    campaign STRING,
    channel_grouping STRING,
    sessions INT64,
    users INT64,
    new_users INT64,
    pageviews INT64,
    avg_session_duration FLOAT64,
    bounce_rate FLOAT64,
    transactions INT64,
    revenue FLOAT64,
    _ingested_at TIMESTAMP
);

-- stg_ga4_pages (page performance)
CREATE TABLE staging.ga4_pages (
    date DATE,
    page_path STRING,
    page_title STRING,
    pageviews INT64,
    unique_pageviews INT64,
    avg_time_on_page FLOAT64,
    entrances INT64,
    exits INT64,
    exit_rate FLOAT64,
    _ingested_at TIMESTAMP
);
```

### 2.3 Mart Layer Tables

```sql
-- mart_daily_performance (daily aggregated metrics)
CREATE TABLE mart.daily_performance (
    date DATE,
    -- Revenue metrics
    total_revenue FLOAT64,
    total_orders INT64,
    total_units INT64,
    avg_order_value FLOAT64,
    -- Ads metrics
    total_ad_spend FLOAT64,
    total_impressions INT64,
    total_clicks INT64,
    total_conversions INT64,
    -- Calculated metrics
    roas FLOAT64,  -- revenue / ad_spend
    cpa FLOAT64,   -- ad_spend / conversions
    ctr FLOAT64,   -- clicks / impressions
    conversion_rate FLOAT64,  -- conversions / clicks
    -- Period comparisons
    revenue_vs_yesterday FLOAT64,
    revenue_vs_last_week FLOAT64,
    revenue_vs_last_month FLOAT64,
    roas_vs_yesterday FLOAT64,
    -- Flags
    is_anomaly BOOL,
    anomaly_type STRING
);

-- mart_shop_performance
CREATE TABLE mart.shop_performance (
    date DATE,
    platform STRING,
    shop_id STRING,
    shop_name STRING,
    revenue FLOAT64,
    orders INT64,
    units INT64,
    avg_order_value FLOAT64,
    refund_amount FLOAT64,
    refund_rate FLOAT64,
    -- Growth metrics
    revenue_mom FLOAT64,
    revenue_yoy FLOAT64,
    orders_mom FLOAT64
);

-- mart_ads_channel_performance
CREATE TABLE mart.ads_channel_performance (
    date DATE,
    platform STRING,
    account_id STRING,
    account_name STRING,
    spend FLOAT64,
    impressions INT64,
    clicks INT64,
    conversions INT64,
    conversion_value FLOAT64,
    roas FLOAT64,
    cpa FLOAT64,
    ctr FLOAT64,
    cpc FLOAT64,
    cpm FLOAT64,
    -- Budget metrics
    daily_budget FLOAT64,
    budget_utilization FLOAT64
);

-- mart_campaign_performance
CREATE TABLE mart.campaign_performance (
    date DATE,
    platform STRING,
    account_id STRING,
    campaign_id STRING,
    campaign_name STRING,
    campaign_type STRING,
    spend FLOAT64,
    impressions INT64,
    clicks INT64,
    conversions INT64,
    conversion_value FLOAT64,
    roas FLOAT64,
    cpa FLOAT64,
    ctr FLOAT64,
    -- Status
    is_active BOOL,
    performance_status STRING  -- 'good', 'warning', 'poor'
);

-- mart_product_performance
CREATE TABLE mart.product_performance (
    date DATE,
    sku_master STRING,
    product_name STRING,
    category STRING,
    -- Sales by platform
    shopee_units INT64,
    shopee_revenue FLOAT64,
    lazada_units INT64,
    lazada_revenue FLOAT64,
    tiktok_units INT64,
    tiktok_revenue FLOAT64,
    other_units INT64,
    other_revenue FLOAT64,
    -- Total
    total_units INT64,
    total_revenue FLOAT64,
    -- Margin
    cost FLOAT64,
    gross_profit FLOAT64,
    margin_percent FLOAT64,
    -- Rank
    revenue_rank INT64,
    units_rank INT64
);

-- mart_simple_alerts (Rule-based alerts for MVP)
-- Note: mart_ai_recommendations (ML-based) moved to Phase 2
CREATE TABLE mart.simple_alerts (
    generated_at TIMESTAMP,
    alert_type STRING,  -- 'roas_low', 'revenue_drop', 'cpa_high'
    severity STRING,  -- 'warning', 'critical'
    title STRING,
    description STRING,
    metric_name STRING,
    metric_value FLOAT64,
    threshold_value FLOAT64,
    affected_platform STRING,
    affected_campaign_id STRING,
    is_acknowledged BOOL,
    acknowledged_at TIMESTAMP
);

-- mart_website_analytics (GA4 aggregated for dashboard)
CREATE TABLE mart.website_analytics (
    date DATE,
    -- Traffic overview
    sessions INT64,
    users INT64,
    new_users INT64,
    returning_users INT64,
    pageviews INT64,
    pages_per_session FLOAT64,
    avg_session_duration FLOAT64,
    bounce_rate FLOAT64,
    -- Engagement
    engaged_sessions INT64,
    engagement_rate FLOAT64,
    -- Conversions
    transactions INT64,
    revenue FLOAT64,
    conversion_rate FLOAT64,
    avg_order_value FLOAT64,
    -- Period comparisons
    sessions_vs_yesterday FLOAT64,
    sessions_vs_last_week FLOAT64,
    revenue_vs_yesterday FLOAT64
);

-- mart_traffic_sources (GA4 traffic by source)
CREATE TABLE mart.traffic_sources (
    date DATE,
    channel_grouping STRING,
    source STRING,
    medium STRING,
    campaign STRING,
    sessions INT64,
    users INT64,
    new_users INT64,
    bounce_rate FLOAT64,
    pages_per_session FLOAT64,
    avg_session_duration FLOAT64,
    transactions INT64,
    revenue FLOAT64,
    conversion_rate FLOAT64,
    -- Share metrics
    sessions_share FLOAT64,
    revenue_share FLOAT64
);

-- mart_cross_channel_attribution (Ads → GA4 → E-commerce)
CREATE TABLE mart.cross_channel_attribution (
    date DATE,
    ads_platform STRING,
    campaign_id STRING,
    campaign_name STRING,
    -- Ads metrics
    ad_spend FLOAT64,
    ad_clicks INT64,
    ad_impressions INT64,
    -- GA4 metrics (matched by UTM)
    ga_sessions INT64,
    ga_users INT64,
    ga_transactions INT64,
    ga_revenue FLOAT64,
    -- E-commerce metrics (if matched)
    ecom_orders INT64,
    ecom_revenue FLOAT64,
    -- Attribution metrics
    roas_ga FLOAT64,        -- GA revenue / Ad spend
    roas_ecom FLOAT64,      -- E-commerce revenue / Ad spend
    cpa_ga FLOAT64,         -- Ad spend / GA transactions
    cpa_ecom FLOAT64        -- Ad spend / E-commerce orders
);
```

### 2.4 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐
│     shops       │       │    products     │
├─────────────────┤       ├─────────────────┤
│ shop_id (PK)    │       │ sku_master (PK) │
│ platform        │       │ product_name    │
│ shop_name       │       │ category        │
└────────┬────────┘       │ cost            │
         │                └────────┬────────┘
         │                         │
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│     orders      │       │   order_items   │
├─────────────────┤       ├─────────────────┤
│ order_id (PK)   │◄──────│ order_id (FK)   │
│ platform        │       │ sku_normalized  │───▶ products.sku_master
│ shop_id (FK)    │───────│ quantity        │
│ amount_thb      │       │ unit_price_thb  │
│ order_date      │       └─────────────────┘
└─────────────────┘

┌─────────────────┐
│ ads_performance │
├─────────────────┤
│ date            │
│ platform        │
│ campaign_id     │
│ spend_thb       │
│ conversions     │
└─────────────────┘

┌──────────────────────┐
│  daily_performance   │ (Aggregated from orders + ads_performance)
├──────────────────────┤
│ date (PK)            │
│ total_revenue        │
│ total_ad_spend       │
│ roas                 │
└──────────────────────┘
```

---

## 3. Airbyte Setup

### 3.1 Airbyte Deployment Options

| Option | Pros | Cons | Recommended For |
|--------|------|------|-----------------|
| **Airbyte Cloud** | Managed, no maintenance, quick setup | Monthly cost (~$300-500+) | Production, less DevOps |
| **Airbyte OSS (Self-hosted)** | Free, full control | Requires server maintenance | Cost-sensitive, DevOps available |
| **Airbyte on GCP (Cloud Run)** | Balance of control & managed | Some setup required | GCP-native stack |

**Recommendation:** Start with **Airbyte Cloud** for quick setup, migrate to self-hosted if cost becomes concern.

### 3.2 Airbyte Connectors Configuration

#### Facebook Ads Connector
```yaml
connector: source-facebook-marketing
config:
  account_id: "${FACEBOOK_ACCOUNT_ID}"
  access_token: "${FACEBOOK_ACCESS_TOKEN}"
  start_date: "2024-01-01"
  end_date: ""  # Empty for ongoing sync
  insights_lookback_window: 28
  fetch_thumbnail_images: false
  custom_insights:
    - name: "daily_ads_insights"
      fields:
        - impressions
        - clicks
        - spend
        - reach
        - frequency
        - cpc
        - cpm
        - ctr
        - actions
        - action_values
        - conversions
        - conversion_values
      breakdowns:
        - age
        - gender
      action_breakdowns:
        - action_type
      level: ad
      time_increment: 1
sync_mode: incremental
destination_sync_mode: append_dedup
```

#### Google Ads Connector
```yaml
connector: source-google-ads
config:
  credentials:
    developer_token: "${GOOGLE_ADS_DEVELOPER_TOKEN}"
    client_id: "${GOOGLE_ADS_CLIENT_ID}"
    client_secret: "${GOOGLE_ADS_CLIENT_SECRET}"
    refresh_token: "${GOOGLE_ADS_REFRESH_TOKEN}"
  customer_id: "${GOOGLE_ADS_CUSTOMER_ID}"
  start_date: "2024-01-01"
  end_date: ""
  custom_queries:
    - query: |
        SELECT
          campaign.id,
          campaign.name,
          campaign.advertising_channel_type,
          ad_group.id,
          ad_group.name,
          segments.date,
          metrics.impressions,
          metrics.clicks,
          metrics.cost_micros,
          metrics.conversions,
          metrics.conversions_value
        FROM ad_group
      table_name: ad_group_performance
sync_mode: incremental
destination_sync_mode: append_dedup
```

#### Google Analytics 4 Connector
```yaml
connector: source-google-analytics-data-api
config:
  credentials:
    credentials_json: "${GA4_CREDENTIALS_JSON}"
  property_id: "${GA4_PROPERTY_ID}"
  date_ranges_start_date: "2024-01-01"
  custom_reports:
    - name: "daily_traffic"
      dimensions:
        - date
        - sessionSource
        - sessionMedium
        - sessionCampaignName
        - deviceCategory
        - country
      metrics:
        - sessions
        - totalUsers
        - newUsers
        - screenPageViews
        - averageSessionDuration
        - bounceRate
        - transactions
        - purchaseRevenue
    - name: "page_performance"
      dimensions:
        - date
        - pagePath
        - pageTitle
      metrics:
        - screenPageViews
        - averageSessionDuration
        - bounceRate
    - name: "ecommerce_events"
      dimensions:
        - date
        - eventName
        - transactionId
      metrics:
        - eventCount
        - purchaseRevenue
        - itemsPurchased
sync_mode: incremental
destination_sync_mode: append_dedup
```

### 3.3 Airbyte to BigQuery Destination

```yaml
connector: destination-bigquery
config:
  project_id: "${GCP_PROJECT_ID}"
  dataset_id: "raw"
  dataset_location: "asia-southeast1"
  credentials_json: "${BIGQUERY_CREDENTIALS_JSON}"
  loading_method:
    method: "GCS Staging"
    gcs_bucket_name: "${GCS_STAGING_BUCKET}"
    gcs_bucket_path: "airbyte-staging"
  transformation_priority: "interactive"
  big_query_client_buffer_size_mb: 15
```

#### TikTok Ads (Marketing) Connector
```yaml
connector: source-tiktok-marketing
config:
  credentials:
    auth_type: "oauth2.0"  # or "sandbox_access_token" for testing
    access_token: "${TIKTOK_ACCESS_TOKEN}"
    advertiser_id: "${TIKTOK_ADVERTISER_ID}"
  start_date: "2024-01-01"
  end_date: ""
  attribution_window: 3  # days, default 3
  include_deleted: false
streams:
  # Entity streams
  - advertisers
  - campaigns
  - ad_groups
  - ads
  - audiences
  - creative_assets_images
  - creative_assets_videos
  # Report streams (with daily granularity)
  - ads_reports_daily
  - ad_groups_reports_daily
  - campaigns_reports_daily
  - advertisers_reports_daily
  # Audience reports
  - ads_reports_by_age_and_gender
  - ads_reports_by_country
  - ads_reports_by_platform
sync_mode: incremental
destination_sync_mode: append_dedup
```

> **Note:** TikTok API มี Data Latency ~11 ชั่วโมง จึงควรตั้ง sync หลังเที่ยงคืน

### 3.4 Airbyte Sync Schedule

| Connection | Frequency | Time (BKK) | Duration Est. |
|------------|-----------|------------|---------------|
| Facebook Ads → BigQuery | Every 6 hours | 00:00, 06:00, 12:00, 18:00 | ~10-15 min |
| Google Ads → BigQuery | Every 6 hours | 00:30, 06:30, 12:30, 18:30 | ~10-15 min |
| GA4 → BigQuery | Every 6 hours | 01:00, 07:00, 13:00, 19:00 | ~15-20 min |
| TikTok Ads → BigQuery | Every 6 hours | 01:30, 07:30, 13:30, 19:30 | ~15-20 min |

---

## 4. API Definitions & Data Extractors (Python)

### 4.1 E-commerce Platform APIs

#### Shopee API
```python
# Endpoints to use:
# - GET /api/v2/order/get_order_list - List orders
# - GET /api/v2/order/get_order_detail - Order details
# - GET /api/v2/product/get_item_list - Product list
# - GET /api/v2/shop/get_shop_info - Shop info

class ShopeeExtractor:
    base_url = "https://partner.shopeemobile.com"

    def get_orders(self, time_from: int, time_to: int) -> List[Dict]
    def get_order_detail(self, order_sn_list: List[str]) -> List[Dict]
    def get_products(self, offset: int, page_size: int) -> List[Dict]
    def get_shop_info(self) -> Dict
```

#### Lazada API
```python
# Endpoints to use:
# - GET /orders/get - Get orders
# - GET /order/items/get - Get order items
# - GET /products/get - Get products

class LazadaExtractor:
    base_url = "https://api.lazada.co.th/rest"

    def get_orders(self, created_after: str, created_before: str) -> List[Dict]
    def get_order_items(self, order_id: int) -> List[Dict]
    def get_products(self, offset: int, limit: int) -> List[Dict]
```

#### TikTok Shop API
```python
# Endpoints to use:
# - POST /api/orders/search - Search orders
# - GET /api/orders/detail/query - Order detail
# - POST /api/products/search - Search products

class TikTokShopExtractor:
    base_url = "https://open-api.tiktokglobalshop.com"

    def search_orders(self, create_time_from: int, create_time_to: int) -> List[Dict]
    def get_order_detail(self, order_id: str) -> Dict
    def search_products(self, page_number: int, page_size: int) -> List[Dict]
```

### 3.2 Advertising Platform APIs

#### Facebook Marketing API
```python
# Endpoints to use:
# - GET /{ad_account_id}/insights - Account insights
# - GET /{campaign_id}/insights - Campaign insights
# - GET /{adset_id}/insights - Ad set insights
# - GET /{ad_id}/insights - Ad insights

class FacebookAdsExtractor:
    base_url = "https://graph.facebook.com/v18.0"

    fields = [
        "impressions", "clicks", "spend", "reach", "frequency",
        "cpc", "cpm", "ctr", "actions", "action_values",
        "cost_per_action_type", "conversions", "conversion_values"
    ]

    breakdowns = ["age", "gender", "placement", "device_platform"]

    def get_account_insights(self, account_id: str, date_preset: str) -> List[Dict]
    def get_campaign_insights(self, account_id: str, date_from: str, date_to: str) -> List[Dict]
    def get_adset_insights(self, campaign_id: str, date_from: str, date_to: str) -> List[Dict]
    def get_ad_insights(self, adset_id: str, date_from: str, date_to: str) -> List[Dict]
```

#### Google Ads API
```python
# Using Google Ads Query Language (GAQL)

class GoogleAdsExtractor:

    queries = {
        "campaign_performance": """
            SELECT
                campaign.id,
                campaign.name,
                campaign.advertising_channel_type,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                metrics.conversions_value
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        """,
        "ad_group_performance": """
            SELECT
                ad_group.id,
                ad_group.name,
                campaign.id,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions
            FROM ad_group
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        """,
        "keyword_performance": """
            SELECT
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                metrics.impressions,
                metrics.clicks,
                metrics.cost_micros,
                metrics.conversions,
                ad_group_criterion.quality_info.quality_score
            FROM keyword_view
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
        """
    }

    def get_campaign_performance(self, customer_id: str, start_date: str, end_date: str) -> List[Dict]
    def get_ad_group_performance(self, customer_id: str, start_date: str, end_date: str) -> List[Dict]
    def get_keyword_performance(self, customer_id: str, start_date: str, end_date: str) -> List[Dict]
```

#### TikTok Ads API
> **Note:** TikTok Ads ใช้ Airbyte connector แทน Python extractor แล้ว (ดู Section 3.2)
>
> Airbyte TikTok Marketing connector รองรับ 50+ streams รวมถึง:
> - Entity streams: advertisers, campaigns, ad_groups, ads, audiences
> - Report streams: daily, hourly, lifetime granularities
> - Audience reports: by age/gender, country, platform

---

## 5. Project Structure

```
central-marketing-dashboard/
├── .docs/
│   ├── 01-spec.md              # Product specification
│   ├── 02-plan.md              # Technical plan (this file)
│   └── 03-tasks.md             # Development tasks
│
├── .claude/
│   └── commands/               # Claude commands
│
├── airbyte/                    # Airbyte configurations
│   ├── connections/            # Connection configs
│   │   ├── facebook_ads.yaml
│   │   ├── google_ads.yaml
│   │   ├── ga4.yaml
│   │   └── tiktok_ads.yaml     # TikTok Marketing connector
│   ├── destinations/           # Destination configs
│   │   └── bigquery.yaml
│   └── README.md               # Airbyte setup guide
│
├── src/
│   ├── __init__.py
│   │
│   ├── extractors/             # Custom API clients (Python-based)
│   │   ├── __init__.py
│   │   ├── base.py             # Base extractor class
│   │   ├── shopee.py           # Shopee API client
│   │   ├── lazada.py           # Lazada API client
│   │   ├── tiktok_shop.py      # TikTok Shop API client
│   │   ├── line_ads.py         # LINE Ads API client
│   │   ├── shopee_ads.py       # Shopee Ads API client
│   │   └── lazada_ads.py       # Lazada Ads API client
│   │   # Note: Facebook Ads, Google Ads, GA4, TikTok Ads ใช้ Airbyte แทน
│   │
│   ├── transformers/           # Data transformation logic
│   │   ├── __init__.py
│   │   ├── base.py             # Base transformer class
│   │   ├── orders.py           # Order data transformers
│   │   ├── products.py         # Product data transformers
│   │   ├── ads.py              # Ads data transformers (unified)
│   │   ├── ga4.py              # GA4 data transformers
│   │   └── sku_mapper.py       # Cross-platform SKU mapping
│   │
│   ├── loaders/                # BigQuery loaders
│   │   ├── __init__.py
│   │   ├── base.py             # Base loader class
│   │   └── bigquery.py         # BigQuery loader
│   │
│   ├── models/                 # Rule-based alerts (MVP) / AI models (Phase 2)
│   │   ├── __init__.py
│   │   ├── simple_alerts.py        # Rule-based alerts (ROAS < 2, Revenue drop > 20%)
│   │   # Phase 2: anomaly_detection.py, budget_optimizer.py, forecaster.py
│   │
│   ├── pipelines/              # ETL pipeline orchestration
│   │   ├── __init__.py
│   │   ├── ecommerce_pipeline.py   # E-commerce data pipeline
│   │   ├── ads_pipeline.py         # Ads data pipeline
│   │   └── mart_pipeline.py        # Mart layer pipeline
│   │
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── logging.py          # Logging setup
│   │   ├── currency.py         # Currency conversion
│   │   └── datetime.py         # Timezone handling
│   │
│   └── main.py                 # Main entry point
│
├── sql/                        # BigQuery SQL scripts
│   ├── schemas/                # Table schemas
│   │   ├── raw/
│   │   ├── staging/
│   │   └── mart/
│   │
│   └── transformations/        # SQL transformations
│       ├── staging/
│       └── mart/
│
├── cloud_functions/            # Cloud Functions for scheduling
│   ├── etl_ecommerce/
│   │   ├── main.py
│   │   └── requirements.txt
│   ├── etl_ads/
│   │   ├── main.py
│   │   └── requirements.txt
│   └── etl_mart/
│       ├── main.py
│       └── requirements.txt
│
├── tests/                      # Unit and integration tests
│   ├── __init__.py
│   ├── test_extractors/
│   ├── test_transformers/
│   ├── test_loaders/
│   └── test_pipelines/
│
├── config/                     # Configuration files
│   ├── platforms.yaml          # Platform configurations
│   ├── credentials.yaml.example # Credentials template
│   └── sku_mapping.csv         # SKU mapping table
│
├── looker_studio/              # Looker Studio configurations
│   └── data_sources.md         # Data source documentation
│
├── scripts/                    # Utility scripts
│   ├── setup_bigquery.py       # Initialize BigQuery
│   ├── deploy_functions.sh     # Deploy Cloud Functions
│   └── backfill_data.py        # Historical data backfill
│
├── requirements.txt            # Python dependencies
├── requirements-dev.txt        # Dev dependencies
├── pyproject.toml              # Project configuration
├── Makefile                    # Common commands
├── .env.example                # Environment variables template
├── .gitignore
└── README.md
```

---

## 5. Third-Party Integrations

### 5.1 Required Libraries

```txt
# requirements.txt

# API Clients
requests>=2.31.0
httpx>=0.25.0
aiohttp>=3.9.0

# Google Cloud
google-cloud-bigquery>=3.13.0
google-cloud-storage>=2.13.0
google-cloud-secret-manager>=2.17.0
google-auth>=2.23.0
google-ads>=22.1.0

# Facebook/Meta
facebook-business>=18.0.0

# Data Processing
pandas>=2.1.0
numpy>=1.26.0
pyarrow>=14.0.0

# Scheduling & Async
apscheduler>=3.10.0
asyncio>=3.4.3

# Configuration
pyyaml>=6.0.0
python-dotenv>=1.0.0
pydantic>=2.5.0
pydantic-settings>=2.1.0

# Logging & Monitoring
structlog>=23.2.0
sentry-sdk>=1.35.0

# Date/Time
python-dateutil>=2.8.0
pytz>=2023.3

# Currency
forex-python>=1.8

# AI/ML (Phase 1 - Simple)
scipy>=1.11.0
statsmodels>=0.14.0
```

### 5.2 External Services

| Service | Purpose | Cost Estimate |
|---------|---------|---------------|
| **Google Cloud Platform** | | |
| - BigQuery | Data warehouse | ~$5-20/month (usage-based) |
| - Cloud Functions | ETL execution | ~$0-5/month |
| - Cloud Scheduler | Job scheduling | Free tier |
| - Secret Manager | Credentials storage | ~$0.03/secret/month |
| - Cloud Storage | Backup/staging | ~$0.02/GB/month |
| **Looker Studio** | Dashboard | Free |

---

## 6. Security & Scalability

### 6.1 Security Measures

#### API Credentials Management
```yaml
# Store in Google Secret Manager
secrets:
  - shopee_partner_id
  - shopee_partner_key
  - shopee_shop_id
  - shopee_access_token
  - lazada_app_key
  - lazada_app_secret
  - lazada_access_token
  - tiktok_app_id
  - tiktok_app_secret
  - tiktok_access_token
  - facebook_app_id
  - facebook_app_secret
  - facebook_access_token
  - google_ads_developer_token
  - google_ads_client_id
  - google_ads_client_secret
  - google_ads_refresh_token
```

#### Access Control
- BigQuery: IAM roles for service account
- Looker Studio: Share via Google account (no public access)
- Cloud Functions: Service account with minimal permissions

#### Data Protection
- No PII stored (customer names, emails masked/hashed)
- Data encrypted at rest (BigQuery default)
- Data encrypted in transit (HTTPS)
- API tokens rotated regularly

### 6.2 Scalability Considerations

#### Current Design (Phase 1)
- Single tenant, all data in one BigQuery project
- Cloud Functions auto-scale with load
- BigQuery handles large data volumes natively

#### Future-Proofing for Phase 2
```yaml
# Design patterns for multi-tenant readiness:

# Option 1: Schema-based isolation
bigquery_project/
  ├── tenant_001/
  │   ├── raw/
  │   ├── staging/
  │   └── mart/
  ├── tenant_002/
  │   ├── raw/
  │   ├── staging/
  │   └── mart/
  └── shared/
      └── reference_data/

# Option 2: Table-based isolation (chosen for Phase 1)
bigquery_project/
  ├── raw/
  │   └── shopee_orders  # Add tenant_id column later
  ├── staging/
  │   └── orders         # Add tenant_id column later
  └── mart/
      └── daily_performance  # Add tenant_id column later
```

### 6.3 Rate Limit Handling

```python
# Rate limit configuration per platform
RATE_LIMITS = {
    "shopee": {
        "requests_per_minute": 60,
        "retry_after_seconds": 60,
        "max_retries": 3
    },
    "lazada": {
        "requests_per_minute": 50,
        "retry_after_seconds": 60,
        "max_retries": 3
    },
    "facebook_ads": {
        "requests_per_hour": 200,
        "retry_after_seconds": 300,
        "max_retries": 5
    },
    "google_ads": {
        "requests_per_day": 15000,
        "retry_after_seconds": 60,
        "max_retries": 3
    },
    "tiktok": {
        "requests_per_minute": 100,
        "retry_after_seconds": 60,
        "max_retries": 3
    }
}
```

### 6.4 Error Handling & Monitoring

```python
# Error handling strategy
class ETLErrorHandler:
    def handle_api_error(self, error, platform, endpoint):
        # Log error with context
        # Retry with exponential backoff
        # Log to Cloud Logging (manual check)

    def handle_data_quality_error(self, error, table, record):
        # Log to dead letter queue
        # Continue processing
        # Generate report

    def handle_bigquery_error(self, error, query):
        # Log error
        # Retry once
        # Log and fail if persists
```

#### Monitoring (MVP - Manual)
> **Phase 1 MVP:** Manual monitoring ผ่าน Cloud Logging Console
> **Phase 2:** Automated alerts via Cloud Monitoring + Slack/Email

- ETL job failures → Check Cloud Logging manually
- Data freshness → Check BigQuery table metadata
- API rate limit hits → Check Cloud Logging
- BigQuery quota → Check GCP Console

---

## 7. Deployment Strategy

### 7.1 Environments

| Environment | Purpose | BigQuery Dataset |
|-------------|---------|------------------|
| Development | Local testing | `dev_marketing` |
| Staging | Pre-production testing | `stg_marketing` |
| Production | Live data | `prod_marketing` |

### 7.2 CI/CD Pipeline

> **Phase 1 MVP:** Manual deployment via scripts
> **Phase 2:** Automated CI/CD via GitHub Actions

```bash
# MVP: Manual deployment
./scripts/deploy_functions.sh
./scripts/setup_bigquery.py

# Phase 2: GitHub Actions workflow (future)
# - Automated testing
# - Automated deployment on push to main
```

### 7.3 ETL Schedule

| Pipeline | Schedule | Duration (Est.) |
|----------|----------|-----------------|
| E-commerce orders | Every 6 hours | ~10-15 min |
| Ads performance | Every 6 hours | ~15-20 min |
| Product sync | Daily 6:00 AM | ~5-10 min |
| Mart refresh | Every 6 hours (after ETL) | ~5-10 min |
| Simple alerts | Daily 7:00 AM | ~2-5 min |

---

## 8. Implementation Phases (MVP Scope)

> **Scope Reduction for MVP:**
> - Dashboard: 9 → 5 หน้า
> - AI/ML: Statistical models → Rule-based
> - Monitoring: Automated alerts → Manual check
> - Testing: 100% coverage → Critical paths only

### Phase 1.1: Foundation
- Setup GCP project & BigQuery
- Create base project structure
- Implement config management
- Setup basic logging (Cloud Logging)

### Phase 1.2: Extractors
- Setup Airbyte (Facebook, Google, GA4, TikTok Ads)
- Implement Shopee extractor (Python)
- Implement Lazada extractor (Python)
- Implement TikTok Shop extractor (Python)
- Implement LINE/Shopee/Lazada Ads extractors (Python)

### Phase 1.3: Transformers & Loaders
- Implement order transformers
- Implement ads transformers
- Implement GA4 transformers
- Implement BigQuery loader
- Create staging layer tables

### Phase 1.4: Mart Layer & Simple Alerts
- Create mart layer tables
- Implement aggregation queries
- **Implement simple alerts (Rule-based)**
  - ROAS < 2 → Alert
  - Revenue drop > 20% → Alert
  - CPA > threshold → Alert

### Phase 1.5: Dashboard (5 pages MVP)
- Create Looker Studio dashboard
  1. Executive Overview
  2. Shop Performance
  3. Ads Performance Overview
  4. Product Analytics
  5. Website Analytics (GA4 basic)
- Connect to BigQuery data sources
- Basic testing
- Essential documentation

---

## 9. Phase 2 Features (Future)

> **ย้ายไป Phase 2:**

### Dashboard Deep Dives
- Facebook Ads Deep Dive
- Google Ads Deep Dive
- TikTok & Others Deep Dive
- AI Insights page

### AI/ML Models
- Anomaly Detection (Statistical)
- Performance Forecaster (Time series)
- Budget Optimizer (ML-based)

### Automation & Monitoring
- Cloud Monitoring dashboards
- Automated alerts (Slack/Email)
- CI/CD pipeline (GitHub Actions)
- Comprehensive unit tests

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | - | Initial technical plan |
| 1.1 | Dec 2025 | - | Added GA4, Airbyte hybrid architecture |
| 1.2 | Dec 2025 | - | TikTok Ads moved to Airbyte (official connector available) |
| 1.3 | Dec 2025 | - | **MVP Scope Reduction:** Dashboard 9→5 หน้า, ML→Rule-based, ย้าย Automation/Monitoring ไป Phase 2 |
