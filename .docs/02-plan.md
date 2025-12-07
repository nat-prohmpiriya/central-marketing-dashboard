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
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA SOURCES                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  E-commerce Platforms          │  Advertising Platforms                     │
│  ┌─────────┐ ┌─────────┐       │  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ Shopee  │ │ Lazada  │       │  │Facebook │ │ Google  │ │ TikTok  │      │
│  │   API   │ │   API   │       │  │Ads API  │ │Ads API  │ │Ads API  │      │
│  └────┬────┘ └────┬────┘       │  └────┬────┘ └────┬────┘ └────┬────┘      │
│       │           │            │       │           │           │            │
│  ┌────┴────┐ ┌────┴────┐       │  ┌────┴────┐ ┌────┴────┐ ┌────┴────┐      │
│  │ TikTok  │ │  LINE   │       │  │  LINE   │ │ Shopee  │ │ Lazada  │      │
│  │Shop API │ │Shop API │       │  │Ads API  │ │Ads API  │ │Ads API  │      │
│  └────┬────┘ └────┬────┘       │  └────┬────┘ └────┬────┘ └────┬────┘      │
└───────┼───────────┼────────────┴───────┼───────────┼───────────┼───────────┘
        │           │                    │           │           │
        ▼           ▼                    ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ETL LAYER (Python)                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │    Extractors   │  │  Transformers   │  │     Loaders     │              │
│  │  (API Clients)  │──▶│ (Data Cleaning) │──▶│  (BigQuery)    │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐                                   │
│  │   Schedulers    │  │  Error Handling │                                   │
│  │(Cloud Scheduler)│  │   & Logging     │                                   │
│  └─────────────────┘  └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA WAREHOUSE (BigQuery)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                         RAW LAYER (raw_*)                           │    │
│  │  raw_shopee_orders │ raw_lazada_orders │ raw_facebook_ads │ ...    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      STAGING LAYER (stg_*)                          │    │
│  │  stg_orders │ stg_products │ stg_ads_performance │ stg_shops        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        MART LAYER (mart_*)                          │    │
│  │  mart_daily_performance │ mart_shop_metrics │ mart_product_sales    │    │
│  │  mart_ads_summary │ mart_ai_recommendations                         │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       VISUALIZATION (Looker Studio)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │Executive │ │  Shop    │ │   Ads    │ │ Facebook │ │  Google  │          │
│  │ Overview │ │Performance│ │ Overview │ │Deep Dive │ │Deep Dive │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                                     │
│  │  TikTok  │ │ Product  │ │   AI     │                                     │
│  │Deep Dive │ │Analytics │ │ Insights │                                     │
│  └──────────┘ └──────────┘ └──────────┘                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| **ETL Scripts** | Python 3.11+ | Ecosystem, libraries for APIs |
| **Data Warehouse** | Google BigQuery | Serverless, scalable, cost-effective |
| **Orchestration** | Cloud Scheduler + Cloud Functions | Serverless, low maintenance |
| **Dashboard** | Google Looker Studio | Free, native BigQuery integration |
| **Version Control** | Git + GitHub | Standard practice |
| **Secrets Management** | Google Secret Manager | Secure API credentials |
| **Monitoring** | Cloud Logging + Cloud Monitoring | Native GCP integration |

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

-- mart_ai_recommendations
CREATE TABLE mart.ai_recommendations (
    generated_at TIMESTAMP,
    recommendation_type STRING,  -- 'budget_allocation', 'anomaly', 'prediction', 'action'
    priority STRING,  -- 'high', 'medium', 'low'
    title STRING,
    description STRING,
    current_value FLOAT64,
    recommended_value FLOAT64,
    expected_impact FLOAT64,
    confidence_score FLOAT64,
    affected_platform STRING,
    affected_campaign_id STRING,
    is_acknowledged BOOL,
    acknowledged_at TIMESTAMP
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

## 3. API Definitions & Data Extractors

### 3.1 E-commerce Platform APIs

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
```python
# Endpoints to use:
# - POST /open_api/v1.3/report/integrated/get/ - Get reports

class TikTokAdsExtractor:
    base_url = "https://business-api.tiktok.com"

    metrics = [
        "spend", "impressions", "clicks", "reach",
        "video_views_p25", "video_views_p50", "video_views_p75", "video_views_p100",
        "likes", "shares", "comments", "follows",
        "conversion", "cost_per_conversion", "conversion_rate"
    ]

    dimensions = ["campaign_id", "adgroup_id", "ad_id", "stat_time_day"]

    def get_campaign_report(self, advertiser_id: str, start_date: str, end_date: str) -> List[Dict]
    def get_adgroup_report(self, advertiser_id: str, start_date: str, end_date: str) -> List[Dict]
    def get_ad_report(self, advertiser_id: str, start_date: str, end_date: str) -> List[Dict]
```

---

## 4. Project Structure

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
├── src/
│   ├── __init__.py
│   │
│   ├── extractors/             # API clients for data extraction
│   │   ├── __init__.py
│   │   ├── base.py             # Base extractor class
│   │   ├── shopee.py           # Shopee API client
│   │   ├── lazada.py           # Lazada API client
│   │   ├── tiktok_shop.py      # TikTok Shop API client
│   │   ├── facebook_ads.py     # Facebook Ads API client
│   │   ├── google_ads.py       # Google Ads API client
│   │   ├── tiktok_ads.py       # TikTok Ads API client
│   │   ├── line_ads.py         # LINE Ads API client
│   │   ├── shopee_ads.py       # Shopee Ads API client
│   │   └── lazada_ads.py       # Lazada Ads API client
│   │
│   ├── transformers/           # Data transformation logic
│   │   ├── __init__.py
│   │   ├── base.py             # Base transformer class
│   │   ├── orders.py           # Order data transformers
│   │   ├── products.py         # Product data transformers
│   │   ├── ads.py              # Ads data transformers
│   │   └── sku_mapper.py       # Cross-platform SKU mapping
│   │
│   ├── loaders/                # BigQuery loaders
│   │   ├── __init__.py
│   │   ├── base.py             # Base loader class
│   │   └── bigquery.py         # BigQuery loader
│   │
│   ├── models/                 # AI/ML models
│   │   ├── __init__.py
│   │   ├── anomaly_detection.py    # Anomaly detection
│   │   ├── budget_optimizer.py     # Budget recommendations
│   │   └── forecaster.py           # Performance forecasting
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
        # Alert if critical

    def handle_data_quality_error(self, error, table, record):
        # Log to dead letter queue
        # Continue processing
        # Generate report

    def handle_bigquery_error(self, error, query):
        # Log error
        # Retry once
        # Alert and fail if persists
```

#### Monitoring Alerts
- ETL job failures
- Data freshness > 12 hours
- API rate limit hits
- BigQuery quota warnings
- Anomaly detection alerts

---

## 7. Deployment Strategy

### 7.1 Environments

| Environment | Purpose | BigQuery Dataset |
|-------------|---------|------------------|
| Development | Local testing | `dev_marketing` |
| Staging | Pre-production testing | `stg_marketing` |
| Production | Live data | `prod_marketing` |

### 7.2 CI/CD Pipeline

```yaml
# GitHub Actions workflow
name: Deploy ETL

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: make test

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy Cloud Functions
        run: make deploy-functions
      - name: Update BigQuery schemas
        run: make update-schemas
```

### 7.3 ETL Schedule

| Pipeline | Schedule | Duration (Est.) |
|----------|----------|-----------------|
| E-commerce orders | Every 6 hours | ~10-15 min |
| Ads performance | Every 6 hours | ~15-20 min |
| Product sync | Daily 6:00 AM | ~5-10 min |
| Mart refresh | Every 6 hours (after ETL) | ~5-10 min |
| AI recommendations | Daily 7:00 AM | ~5-10 min |

---

## 8. Implementation Phases

### Phase 1.1: Foundation (Week 1-2)
- Setup GCP project & BigQuery
- Create base project structure
- Implement config management
- Setup logging & monitoring

### Phase 1.2: Extractors (Week 3-4)
- Implement Shopee extractor
- Implement Lazada extractor
- Implement TikTok Shop extractor
- Implement Facebook Ads extractor
- Implement Google Ads extractor
- Implement TikTok Ads extractor

### Phase 1.3: Transformers & Loaders (Week 5-6)
- Implement order transformers
- Implement ads transformers
- Implement BigQuery loader
- Create staging layer tables

### Phase 1.4: Mart Layer & AI (Week 7-8)
- Create mart layer tables
- Implement aggregation queries
- Implement anomaly detection
- Implement budget recommendations

### Phase 1.5: Dashboard & Polish (Week 9-10)
- Create Looker Studio dashboard (8 pages)
- Connect to BigQuery data sources
- Testing & bug fixes
- Documentation

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | - | Initial technical plan |
