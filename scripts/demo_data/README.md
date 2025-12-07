# Demo Data Generator

Generate realistic demo data for the Central Marketing Dashboard.

## Overview

This module generates fake but realistic data for:
- **E-commerce**: Orders, products, shops (Shopee, Lazada, TikTok Shop)
- **Ads**: Campaigns, ad groups, ads, daily performance (Facebook, Google, TikTok, LINE)
- **GA4**: Sessions, traffic sources, page performance

## Quick Start

### 1. Generate and Load All Data

```bash
cd /path/to/central-marketing-dashboard

# Load 90 days of demo data (default)
uv run python scripts/demo_data/load_to_bigquery.py

# Or specify days
uv run python scripts/demo_data/load_to_bigquery.py --days 30
```

### 2. Load Specific Data Type

```bash
# E-commerce only
uv run python scripts/demo_data/load_to_bigquery.py --type ecommerce

# Ads only
uv run python scripts/demo_data/load_to_bigquery.py --type ads

# GA4 only
uv run python scripts/demo_data/load_to_bigquery.py --type ga4
```

### 3. Specify Project

```bash
uv run python scripts/demo_data/load_to_bigquery.py --project your-project-id
```

## Data Generated

### E-commerce Data

| Table | Description | Records (90 days) |
|-------|-------------|-------------------|
| `stg_shops` | Shop information | ~9 shops |
| `stg_products` | Product catalog | ~300 products |
| `stg_orders` | Order records | ~10,000+ orders |
| `stg_order_items` | Order line items | ~20,000+ items |

**Features:**
- 3 platforms: Shopee, Lazada, TikTok Shop
- 3 shops per platform
- 10 product categories with Thai names
- Realistic order patterns (weekday/weekend, holidays)
- Order statuses: completed, shipped, pending, cancelled, refunded
- Payment methods: credit_card, bank_transfer, COD, wallet, installment

### Ads Data

| Table | Description | Records (90 days) |
|-------|-------------|-------------------|
| `stg_ads_campaigns` | Campaign data | ~50 campaigns |
| `stg_ads_ad_groups` | Ad group/Ad set data | ~150 ad groups |
| `stg_ads_creatives` | Ad creative data | ~400 ads |
| `stg_ads_daily_performance` | Daily metrics | ~4,000+ records |

**Features:**
- 4 platforms: Facebook, Google, TikTok Ads, LINE
- Multiple campaign types per platform
- Realistic metrics (CTR, CPC, CPA, ROAS)
- Budget and spend variations
- Seasonality patterns

### GA4 Data

| Table | Description | Records (90 days) |
|-------|-------------|-------------------|
| `stg_ga4_traffic` | Traffic by source/medium | ~1,000 records |
| `stg_ga4_pages` | Page performance | ~1,000 records |
| `stg_ga4_devices` | Device breakdown | ~270 records |
| `stg_ga4_daily` | Daily overview | 90 records |

**Features:**
- Multiple traffic sources (organic, cpc, social, direct, referral)
- Page paths with realistic exit rates
- Device categories (mobile 65%, desktop 30%, tablet 5%)
- Conversion tracking
- Thai market focus (92% Thailand traffic)

## Customization

### Change Date Range

```python
from scripts.demo_data import create_default_config, EcommerceGenerator

config = create_default_config(days_back=30)  # Last 30 days
generator = EcommerceGenerator(config)
data = generator.generate()
```

### Change Random Seed

```python
config = create_default_config(days_back=90)
config.seed = 123  # Different seed = different data
```

### Scale Data Volume

```python
config = create_default_config(days_back=90)
config.scale = 2.0  # Double the data volume
```

## Data Characteristics

### Seasonality Patterns

The generator applies realistic patterns:
- **Weekends**: +30% orders/sessions
- **End of month**: +20% (payday effect)
- **December**: +50% (holiday shopping)
- **November**: +40% (11.11 sales)
- **February**: +20% (Valentine)

### Metric Ranges

| Metric | Min | Max | Mean |
|--------|-----|-----|------|
| Order value (THB) | 100 | 5,000 | 800 |
| Items per order | 1 | 5 | 2 |
| CTR (%) | 0.5 | 5.0 | 2.0 |
| Conversion rate (%) | 0.5 | 5.0 | 2.0 |
| ROAS | 0.5 | 8.0 | 3.0 |
| Daily ad spend (THB) | 500 | 50,000 | 10,000 |
| Sessions per day | 100 | 5,000 | 1,000 |

## After Loading Data

1. **Refresh Mart Layer**
   ```bash
   uv run python -m src.main mart --all
   ```

2. **Connect Looker Studio**
   - Go to Looker Studio
   - Add BigQuery data source
   - Select `mart` dataset tables

3. **Verify Data**
   ```sql
   -- Check order count
   SELECT COUNT(*) FROM `your-project.staging.stg_orders`;

   -- Check ads performance
   SELECT platform, SUM(spend), SUM(revenue)
   FROM `your-project.staging.stg_ads_daily_performance`
   GROUP BY platform;
   ```

## Troubleshooting

### Authentication Error

```bash
gcloud auth application-default login
```

### Module Not Found

```bash
cd /path/to/central-marketing-dashboard
uv sync
```

### BigQuery Permission Error

Ensure your account has BigQuery Data Editor role.
