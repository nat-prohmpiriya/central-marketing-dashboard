# Development Tasks: Centralized Marketing Dashboard

## Overview

**Document Type:** Development Task Breakdown
**Phase:** Phase 1 - Single Tenant MVP
**Last Updated:** December 2025

### Reference Documents
- Product Specification: `.docs/01-spec.md`
- Technical Plan: `.docs/02-plan.md`

### Task Status Legend
- [ ] Pending
- [x] Completed
- [🔄] In Progress
- [⏸️] Blocked

---

## [🔄] Phase 1.1: Foundation (Week 1-2)

### [x]  1.1.1 Project Setup

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| F-001 | Initialize Python project | สร้าง project structure พื้นฐาน | `pyproject.toml`, `requirements.txt`, `.gitignore` | - สามารถ `pip install -e .` ได้ <br> - มี virtual environment |
| F-002 | Setup Git repository | Initialize git และ create `.gitignore` | Root directory | - มี `.gitignore` ครอบคลุม Python, IDE, secrets <br> - Initial commit สำเร็จ |
| F-003 | Create folder structure | สร้างโครงสร้างโฟลเดอร์ตาม technical plan | `src/`, `tests/`, `config/`, `sql/`, `scripts/` | - ทุกโฟลเดอร์มี `__init__.py` <br> - โครงสร้างตรงตาม plan |
| F-004 | Setup configuration management | สร้างระบบจัดการ config | `src/utils/config.py`, `config/*.yaml` | - Load config จาก YAML ได้ <br> - Support environment variables |
| F-005 | Setup logging | สร้างระบบ logging | `src/utils/logging.py` | - Log ออก console และ file <br> - มี log levels (DEBUG, INFO, ERROR) |
| F-006 | Create .env template | สร้าง template สำหรับ environment variables | `.env.example` | - มีทุก variables ที่จำเป็น <br> - มี comments อธิบาย |

**Checklist:**
- [x] F-001: Initialize Python project
- [x] F-002: Setup Git repository
- [x] F-003: Create folder structure
- [x] F-004: Setup configuration management
- [x] F-005: Setup logging
- [x] F-006: Create .env template

---

### [x]  1.1.2 GCP Setup

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| G-001 | Create GCP project | สร้าง Google Cloud Project | GCP Console | - Project created <br> - Billing enabled |
| G-002 | Enable required APIs | Enable BigQuery, Cloud Functions, etc. | GCP Console | - BigQuery API enabled <br> - Cloud Functions enabled <br> - Cloud Scheduler enabled <br> - Secret Manager enabled <br> - Cloud Storage enabled |
| G-003 | Create service account | สร้าง service account สำหรับ ETL | IAM & Admin | - Service account created <br> - JSON key downloaded <br> - Key stored securely |
| G-004 | Setup BigQuery datasets | สร้าง datasets: raw, staging, mart | BigQuery Console / `scripts/setup_bigquery.py` | - 3 datasets created <br> - Proper permissions set |
| G-005 | Setup Secret Manager | สร้าง secrets สำหรับ API credentials | Secret Manager | - Secrets created for each platform <br> - Service account has access |
| G-006 | Create GCS staging bucket | สร้าง bucket สำหรับ Airbyte staging | Cloud Storage | - Bucket created <br> - Service account has access |
| G-007 | Create setup script | Script สำหรับ initialize BigQuery | `scripts/setup_bigquery.py` | - Script runs without error <br> - Creates all datasets and tables |

**Checklist:**
- [x] G-001: Create GCP project (script: `01-create-project.sh`)
- [x] G-002: Enable required APIs (script: `02-enable-apis.sh`)
- [x] G-003: Create service account (script: `03-create-service-account.sh`)
- [x] G-004: Setup BigQuery datasets (script: `04-setup-bigquery.sh`)
- [x] G-005: Setup Secret Manager (script: `05-setup-secret-manager.sh`)
- [x] G-006: Create GCS staging bucket (script: `06-create-gcs-bucket.sh`)
- [x] G-007: Create setup script (all scripts in `scripts/setup_gcloud/`)

---

### [ ]  1.1.3 Base Classes

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| B-001 | Create BaseExtractor class | Abstract base class สำหรับ extractors | `src/extractors/base.py` | - มี abstract methods: `extract()`, `authenticate()` <br> - มี retry logic <br> - มี rate limiting |
| B-002 | Create BaseTransformer class | Abstract base class สำหรับ transformers | `src/transformers/base.py` | - มี abstract methods: `transform()`, `validate()` <br> - มี error handling |
| B-003 | Create BaseLoader class | Abstract base class สำหรับ loaders | `src/loaders/base.py` | - มี abstract methods: `load()` <br> - มี batch support |
| B-004 | Create BigQuery loader | BigQuery loader implementation | `src/loaders/bigquery.py` | - Connect to BigQuery ได้ <br> - Insert data ได้ <br> - Handle duplicates |
| B-005 | Create utility functions | Helper functions ต่างๆ | `src/utils/datetime.py`, `src/utils/currency.py` | - Timezone conversion works <br> - Currency conversion works |
| B-006 | Write unit tests for base classes | Tests สำหรับ base classes | `tests/test_base.py` | - All tests pass <br> - Coverage > 80% |

**Checklist:**
- [ ] B-001: Create BaseExtractor class
- [ ] B-002: Create BaseTransformer class
- [ ] B-003: Create BaseLoader class
- [ ] B-004: Create BigQuery loader
- [ ] B-005: Create utility functions
- [ ] B-006: Write unit tests for base classes

---

## [ ] Phase 1.2: Extractors (Week 3-4)

### [ ]  1.2.1 E-commerce Extractors

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| E-001 | Shopee authentication | Implement Shopee API authentication | `src/extractors/shopee.py` | - Generate access token <br> - Refresh token works <br> - Handle token expiry |
| E-002 | Shopee orders extractor | ดึง orders จาก Shopee | `src/extractors/shopee.py` | - Get orders by date range <br> - Get order details <br> - Handle pagination |
| E-003 | Shopee products extractor | ดึง products จาก Shopee | `src/extractors/shopee.py` | - Get product list <br> - Get product details <br> - Handle pagination |
| E-004 | Shopee extractor tests | Unit tests สำหรับ Shopee extractor | `tests/test_extractors/test_shopee.py` | - Mock API calls <br> - All tests pass |
| E-005 | Lazada authentication | Implement Lazada API authentication | `src/extractors/lazada.py` | - Generate access token <br> - Refresh token works |
| E-006 | Lazada orders extractor | ดึง orders จาก Lazada | `src/extractors/lazada.py` | - Get orders by date range <br> - Get order items <br> - Handle pagination |
| E-007 | Lazada products extractor | ดึง products จาก Lazada | `src/extractors/lazada.py` | - Get product list <br> - Handle pagination |
| E-008 | Lazada extractor tests | Unit tests สำหรับ Lazada extractor | `tests/test_extractors/test_lazada.py` | - Mock API calls <br> - All tests pass |
| E-009 | TikTok Shop authentication | Implement TikTok Shop API authentication | `src/extractors/tiktok_shop.py` | - Generate access token <br> - Handle token expiry |
| E-010 | TikTok Shop orders extractor | ดึง orders จาก TikTok Shop | `src/extractors/tiktok_shop.py` | - Search orders by date <br> - Get order details <br> - Handle pagination |
| E-011 | TikTok Shop products extractor | ดึง products จาก TikTok Shop | `src/extractors/tiktok_shop.py` | - Search products <br> - Handle pagination |
| E-012 | TikTok Shop extractor tests | Unit tests สำหรับ TikTok Shop | `tests/test_extractors/test_tiktok_shop.py` | - Mock API calls <br> - All tests pass |

**Checklist:**
- [ ] E-001: Shopee authentication
- [ ] E-002: Shopee orders extractor
- [ ] E-003: Shopee products extractor
- [ ] E-004: Shopee extractor tests
- [ ] E-005: Lazada authentication
- [ ] E-006: Lazada orders extractor
- [ ] E-007: Lazada products extractor
- [ ] E-008: Lazada extractor tests
- [ ] E-009: TikTok Shop authentication
- [ ] E-010: TikTok Shop orders extractor
- [ ] E-011: TikTok Shop products extractor
- [ ] E-012: TikTok Shop extractor tests

---

### [ ]  1.2.2 Ads & Analytics Extractors (Python + Official SDKs)

> **Note:** ใช้ Official SDKs จาก platform ต่างๆ แทน Airbyte
> - Facebook Ads: `facebook-business`
> - Google Ads: `google-ads`
> - TikTok Ads: `tiktok-business-api-sdk`
> - GA4: `google-analytics-data`

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| A-001 | Facebook Ads authentication | Implement Facebook Marketing API auth | `src/extractors/facebook_ads.py` | - OAuth flow works <br> - Handle token refresh |
| A-002 | Facebook Ads extractor | ดึง Facebook Ads insights | `src/extractors/facebook_ads.py` | - Get campaign/adset/ad insights <br> - Handle pagination <br> - Support breakdowns |
| A-003 | Facebook Ads extractor tests | Unit tests | `tests/test_extractors/test_facebook_ads.py` | - Mock API calls <br> - All tests pass |
| A-004 | Google Ads authentication | Implement Google Ads API auth | `src/extractors/google_ads.py` | - OAuth flow works <br> - Developer token setup |
| A-005 | Google Ads extractor | ดึง Google Ads performance | `src/extractors/google_ads.py` | - Get campaign/adgroup/ad metrics <br> - Use GAQL queries |
| A-006 | Google Ads extractor tests | Unit tests | `tests/test_extractors/test_google_ads.py` | - Mock API calls <br> - All tests pass |
| A-007 | TikTok Ads authentication | Implement TikTok Marketing API auth | `src/extractors/tiktok_ads.py` | - OAuth flow works <br> - Handle advertiser_id |
| A-008 | TikTok Ads extractor | ดึง TikTok Ads performance | `src/extractors/tiktok_ads.py` | - Get campaign/adgroup/ad metrics <br> - Get reporting data |
| A-009 | TikTok Ads extractor tests | Unit tests | `tests/test_extractors/test_tiktok_ads.py` | - Mock API calls <br> - All tests pass |
| A-010 | GA4 authentication | Implement GA4 Data API auth | `src/extractors/ga4.py` | - Service account auth <br> - Property ID setup |
| A-011 | GA4 extractor | ดึง GA4 reports | `src/extractors/ga4.py` | - Get traffic reports <br> - Get ecommerce data <br> - Get page performance |
| A-012 | GA4 extractor tests | Unit tests | `tests/test_extractors/test_ga4.py` | - Mock API calls <br> - All tests pass |
| A-013 | LINE Ads authentication | Implement LINE Ads API auth | `src/extractors/line_ads.py` | - Generate access token <br> - Handle token refresh |
| A-014 | LINE Ads extractor | ดึง LINE Ads campaign performance | `src/extractors/line_ads.py` | - Get campaign metrics <br> - Handle pagination |
| A-015 | LINE Ads extractor tests | Unit tests | `tests/test_extractors/test_line_ads.py` | - Mock API calls <br> - All tests pass |
| A-016 | Shopee Ads authentication | Implement Shopee Ads API auth | `src/extractors/shopee_ads.py` | - Reuse Shopee OAuth |
| A-017 | Shopee Ads extractor | ดึง Shopee Ads performance | `src/extractors/shopee_ads.py` | - Get product ads metrics <br> - Get shop ads metrics |
| A-018 | Shopee Ads extractor tests | Unit tests | `tests/test_extractors/test_shopee_ads.py` | - Mock API calls <br> - All tests pass |
| A-019 | Lazada Ads authentication | Implement Lazada Ads API auth | `src/extractors/lazada_ads.py` | - Reuse Lazada OAuth |
| A-020 | Lazada Ads extractor | ดึง Lazada Sponsored Solutions | `src/extractors/lazada_ads.py` | - Get sponsored products metrics |
| A-021 | Lazada Ads extractor tests | Unit tests | `tests/test_extractors/test_lazada_ads.py` | - Mock API calls <br> - All tests pass |

**Checklist:**
- [ ] A-001: Facebook Ads authentication
- [ ] A-002: Facebook Ads extractor
- [ ] A-003: Facebook Ads extractor tests
- [ ] A-004: Google Ads authentication
- [ ] A-005: Google Ads extractor
- [ ] A-006: Google Ads extractor tests
- [ ] A-007: TikTok Ads authentication
- [ ] A-008: TikTok Ads extractor
- [ ] A-009: TikTok Ads extractor tests
- [ ] A-010: GA4 authentication
- [ ] A-011: GA4 extractor
- [ ] A-012: GA4 extractor tests
- [ ] A-013: LINE Ads authentication
- [ ] A-014: LINE Ads extractor
- [ ] A-015: LINE Ads extractor tests
- [ ] A-016: Shopee Ads authentication
- [ ] A-017: Shopee Ads extractor
- [ ] A-018: Shopee Ads extractor tests
- [ ] A-019: Lazada Ads authentication
- [ ] A-020: Lazada Ads extractor
- [ ] A-021: Lazada Ads extractor tests

---

## [ ] Phase 1.3: Transformers & Loaders (Week 5-6)

### [ ]  1.3.1 Order Transformers

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| T-001 | Shopee order transformer | Transform Shopee orders to staging format | `src/transformers/orders.py` | - Normalize status <br> - Convert currency to THB <br> - Convert timezone |
| T-002 | Lazada order transformer | Transform Lazada orders to staging format | `src/transformers/orders.py` | - Normalize status <br> - Convert currency to THB |
| T-003 | TikTok order transformer | Transform TikTok orders to staging format | `src/transformers/orders.py` | - Normalize status <br> - Convert currency to THB |
| T-004 | Unified order transformer | Combine all orders into single format | `src/transformers/orders.py` | - Unified schema <br> - Platform identifier |
| T-005 | Order item transformer | Transform order items | `src/transformers/orders.py` | - Extract items <br> - Map SKU |
| T-006 | Order transformer tests | Unit tests | `tests/test_transformers/test_orders.py` | - All tests pass |

**Checklist:**
- [ ] T-001: Shopee order transformer
- [ ] T-002: Lazada order transformer
- [ ] T-003: TikTok order transformer
- [ ] T-004: Unified order transformer
- [ ] T-005: Order item transformer
- [ ] T-006: Order transformer tests

---

### [ ]  1.3.2 Ads Transformers

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| T-007 | Facebook Ads transformer | Transform Facebook Ads to staging format | `src/transformers/ads.py` | - Normalize metrics <br> - Convert currency to THB |
| T-008 | Google Ads transformer | Transform Google Ads to staging format | `src/transformers/ads.py` | - Convert cost_micros <br> - Normalize campaign types |
| T-009 | TikTok Ads transformer | Transform TikTok Ads to staging format | `src/transformers/ads.py` | - Normalize metrics <br> - Convert currency |
| T-010 | Unified ads transformer | Combine all ads into single format | `src/transformers/ads.py` | - Unified schema <br> - Platform identifier |
| T-011 | Ads transformer tests | Unit tests | `tests/test_transformers/test_ads.py` | - All tests pass |

**Checklist:**
- [ ] T-007: Facebook Ads transformer
- [ ] T-008: Google Ads transformer
- [ ] T-009: TikTok Ads transformer
- [ ] T-010: Unified ads transformer
- [ ] T-011: Ads transformer tests

---

### [ ]  1.3.3 GA4 Transformers

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| T-012 | GA4 sessions transformer | Transform raw GA4 events to sessions | `src/transformers/ga4.py` | - Aggregate events by session <br> - Calculate session duration |
| T-013 | GA4 traffic transformer | Transform to traffic summary | `src/transformers/ga4.py` | - Aggregate by source/medium <br> - Calculate channel grouping |
| T-014 | GA4 pages transformer | Transform to page performance | `src/transformers/ga4.py` | - Aggregate by page path <br> - Calculate metrics |
| T-015 | GA4 transformer tests | Unit tests | `tests/test_transformers/test_ga4.py` | - All tests pass |

**Checklist:**
- [ ] T-012: GA4 sessions transformer
- [ ] T-013: GA4 traffic transformer
- [ ] T-014: GA4 pages transformer
- [ ] T-015: GA4 transformer tests

---

### [ ]  1.3.4 Product & SKU Mapping

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| T-016 | Product transformer | Transform product data | `src/transformers/products.py` | - Unified product schema |
| T-017 | SKU mapper | Map SKUs across platforms | `src/transformers/sku_mapper.py` | - Load mapping from CSV <br> - Handle unmapped SKUs |
| T-018 | SKU mapping CSV template | สร้าง template สำหรับ SKU mapping | `config/sku_mapping.csv` | - Template with examples |
| T-019 | Product transformer tests | Unit tests | `tests/test_transformers/test_products.py` | - All tests pass |

**Checklist:**
- [ ] T-016: Product transformer
- [ ] T-017: SKU mapper
- [ ] T-018: SKU mapping CSV template
- [ ] T-019: Product transformer tests

---

### [ ]  1.3.5 BigQuery Schemas & Loading

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| L-001 | Create raw layer schemas | SQL schemas สำหรับ raw tables | `sql/schemas/raw/*.sql` | - All raw tables defined |
| L-002 | Create staging layer schemas | SQL schemas สำหรับ staging tables | `sql/schemas/staging/*.sql` | - All staging tables defined |
| L-003 | Create mart layer schemas | SQL schemas สำหรับ mart tables | `sql/schemas/mart/*.sql` | - All mart tables defined |
| L-004 | Implement raw data loader | Load data to raw layer | `src/loaders/bigquery.py` | - Insert with _ingested_at <br> - Handle duplicates |
| L-005 | Implement staging data loader | Load data to staging layer | `src/loaders/bigquery.py` | - Upsert logic <br> - Handle updates |
| L-006 | Loader tests | Unit tests | `tests/test_loaders/test_bigquery.py` | - All tests pass |

**Checklist:**
- [ ] L-001: Create raw layer schemas
- [ ] L-002: Create staging layer schemas
- [ ] L-003: Create mart layer schemas
- [ ] L-004: Implement raw data loader
- [ ] L-005: Implement staging data loader
- [ ] L-006: Loader tests

---

## [ ] Phase 1.4: Pipelines & Mart Layer (Week 7-8)

### [ ]  1.4.1 ETL Pipelines

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| P-001 | E-commerce pipeline | Pipeline รวม extract-transform-load orders | `src/pipelines/ecommerce_pipeline.py` | - Run all e-commerce extractors <br> - Transform and load to BigQuery |
| P-002 | Ads pipeline | Pipeline รวม extract-transform-load ads | `src/pipelines/ads_pipeline.py` | - Run all ads extractors <br> - Transform and load to BigQuery |
| P-003 | Product pipeline | Pipeline สำหรับ products | `src/pipelines/product_pipeline.py` | - Sync products <br> - Update SKU mapping |
| P-004 | Main entry point | Main script to run pipelines | `src/main.py` | - CLI interface <br> - Select pipeline to run |
| P-005 | Pipeline tests | Integration tests | `tests/test_pipelines/` | - End-to-end test with mocks |

**Checklist:**
- [ ] P-001: E-commerce pipeline
- [ ] P-002: Ads pipeline
- [ ] P-003: Product pipeline
- [ ] P-004: Main entry point
- [ ] P-005: Pipeline tests

---

### [ ]  1.4.2 Mart Layer SQL

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| M-001 | Daily performance mart | SQL สำหรับ mart_daily_performance | `sql/transformations/mart/daily_performance.sql` | - Aggregate orders + ads <br> - Calculate ROAS, CPA |
| M-002 | Shop performance mart | SQL สำหรับ mart_shop_performance | `sql/transformations/mart/shop_performance.sql` | - Aggregate by shop <br> - Calculate growth rates |
| M-003 | Ads channel performance mart | SQL สำหรับ mart_ads_channel_performance | `sql/transformations/mart/ads_channel.sql` | - Aggregate by platform <br> - Calculate metrics |
| M-004 | Campaign performance mart | SQL สำหรับ mart_campaign_performance | `sql/transformations/mart/campaign.sql` | - Campaign-level metrics <br> - Performance status |
| M-005 | Product performance mart | SQL สำหรับ mart_product_performance | `sql/transformations/mart/product.sql` | - Product-level sales <br> - Cross-platform aggregation |
| M-006 | Mart pipeline | Pipeline to refresh mart layer | `src/pipelines/mart_pipeline.py` | - Run all mart SQL <br> - Handle dependencies |

**Checklist:**
- [ ] M-001: Daily performance mart
- [ ] M-002: Shop performance mart
- [ ] M-003: Ads channel performance mart
- [ ] M-004: Campaign performance mart
- [ ] M-005: Product performance mart
- [ ] M-006: Mart pipeline

---

### [ ]  1.4.3 Simple Alerts (Rule-based - MVP)

> **Scope Reduction:** เปลี่ยนจาก AI/ML Models เป็น Rule-based alerts
> AI/ML Models (Anomaly, Forecaster, Budget Optimizer) ย้ายไป Phase 2

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| SA-001 | Simple alerts module | สร้าง rule-based alerts | `src/models/simple_alerts.py` | - ROAS < 2 → Alert <br> - Revenue drop > 20% → Alert <br> - CPA > threshold → Alert |
| SA-002 | Alerts mart SQL | SQL สำหรับ mart_simple_alerts | `sql/transformations/mart/simple_alerts.sql` | - Generate alerts based on rules |
| SA-003 | Alerts pipeline | Pipeline to generate alerts | `src/pipelines/alerts_pipeline.py` | - Run rules <br> - Save to mart_simple_alerts |

**Checklist:**
- [ ] SA-001: Simple alerts module
- [ ] SA-002: Alerts mart SQL
- [ ] SA-003: Alerts pipeline

---

### [ ]  1.4.4 AI/ML Features (Phase 2 - Future)

> **ย้ายไป Phase 2:**

| Task ID | Task Name | Description | Technical Context |
|---------|-----------|-------------|-------------------|
| AI-001 | Anomaly detection | Z-score detection | `src/models/anomaly_detection.py` |
| AI-002 | Budget optimizer | ML-based budget allocation | `src/models/budget_optimizer.py` |
| AI-003 | Performance forecaster | Time series forecasting | `src/models/forecaster.py` |
| AI-004 | AI recommendations pipeline | Generate ML-based recommendations | `src/pipelines/ai_pipeline.py` |

---

## [ ] Phase 1.5: Cloud Deployment (MVP)

### [ ]  1.5.1 Cloud Functions

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| C-001 | E-commerce Cloud Function | Deploy e-commerce pipeline | `cloud_functions/etl_ecommerce/` | - Function deployed <br> - Triggered successfully |
| C-002 | Ads Cloud Function | Deploy ads pipeline | `cloud_functions/etl_ads/` | - Function deployed <br> - Triggered successfully |
| C-003 | Mart Cloud Function | Deploy mart pipeline | `cloud_functions/etl_mart/` | - Function deployed <br> - Triggered successfully |
| C-004 | Alerts Cloud Function | Deploy simple alerts pipeline | `cloud_functions/etl_alerts/` | - Function deployed <br> - Triggered successfully |
| C-005 | Setup Cloud Scheduler | สร้าง scheduled jobs | GCP Console | - E-commerce: every 6 hours <br> - Ads: every 6 hours <br> - Mart: after ETL <br> - Alerts: daily 7 AM |
| C-006 | Deploy script | Script to deploy all functions | `scripts/deploy_functions.sh` | - One command deploy |

**Checklist:**
- [ ] C-001: E-commerce Cloud Function
- [ ] C-002: Ads Cloud Function
- [ ] C-003: Mart Cloud Function
- [ ] C-004: Alerts Cloud Function
- [ ] C-005: Setup Cloud Scheduler
- [ ] C-006: Deploy script

---

### [ ]  1.5.2 Basic Logging (MVP)

> **Scope Reduction:** ใช้ Cloud Logging พื้นฐาน, manual check
> Automated Monitoring & Alerts ย้ายไป Phase 2

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| LOG-001 | Setup Cloud Logging | Configure logging for all functions | GCP Console | - Logs visible in Cloud Logging <br> - Manual check process documented |

**Checklist:**
- [ ] LOG-001: Setup Cloud Logging

---

### [ ]  1.5.3 Monitoring & Alerts (Phase 2 - Future)

> **ย้ายไป Phase 2:**

| Task ID | Task Name | Description | Technical Context |
|---------|-----------|-------------|-------------------|
| MON-001 | Setup error alerts | Alert on function failures | Cloud Monitoring |
| MON-002 | Setup data freshness alert | Alert if data > 12 hours old | Cloud Monitoring |
| MON-003 | Create monitoring dashboard | GCP monitoring dashboard | Cloud Monitoring |
| MON-004 | Slack/Email integration | Automated notifications | Cloud Monitoring + Slack |

---

## [ ] Phase 1.6: Dashboard (MVP - 5 pages)

> **Scope Reduction:** ลดจาก 9 หน้าเหลือ 5 หน้า
> Deep Dive pages (Facebook, Google, TikTok) และ AI Insights ย้ายไป Phase 2

### [ ]  1.6.1 Looker Studio Setup

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| D-001 | Connect BigQuery data sources | เชื่อม BigQuery กับ Looker Studio | Looker Studio | - All mart tables connected |
| D-002 | Create calculated fields | สร้าง calculated fields ที่จำเป็น | Looker Studio | - ROAS, CPA, CTR calculated |
| D-003 | Create date filters | Date range filters | Looker Studio | - Filter works across all pages |
| D-004 | Create platform filters | Platform selection filters | Looker Studio | - Filter by platform works |

**Checklist:**
- [ ] D-001: Connect BigQuery data sources
- [ ] D-002: Create calculated fields
- [ ] D-003: Create date filters
- [ ] D-004: Create platform filters

---

### [ ]  1.6.2 Dashboard Pages (MVP - 5 pages)

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| D-005 | Page 1: Executive Overview | หน้า overview + simple alerts | Looker Studio | - KPI scorecards <br> - Revenue trend chart <br> - Period comparison <br> - Simple alerts (ROAS < 2, Revenue drop) |
| D-006 | Page 2: Shop Performance | หน้า shop comparison | Looker Studio | - Shop comparison table <br> - Platform breakdown <br> - Growth metrics |
| D-007 | Page 3: Ads Performance Overview | หน้า ads summary (รวมทุก platform) | Looker Studio | - Spend by platform <br> - ROAS comparison <br> - Campaign table (all platforms) <br> - Performance flags (Poor/OK/Good) |
| D-008 | Page 4: Product Analytics | หน้า product analysis | Looker Studio | - Top products table <br> - Category breakdown <br> - Platform comparison |
| D-009 | Page 5: Website Analytics (GA4 Basic) | หน้า GA4 พื้นฐาน | Looker Studio | - Sessions & users trend <br> - Traffic sources breakdown <br> - Top pages table <br> - Basic conversion metrics |

**Checklist:**
- [ ] D-005: Page 1: Executive Overview
- [ ] D-006: Page 2: Shop Performance
- [ ] D-007: Page 3: Ads Performance Overview
- [ ] D-008: Page 4: Product Analytics
- [ ] D-009: Page 5: Website Analytics (GA4 Basic)

---

### [ ]  1.6.3 Dashboard Pages (Phase 2 - Future)

> **ย้ายไป Phase 2:**

| Task ID | Task Name | Description | Technical Context |
|---------|-----------|-------------|-------------------|
| D-010 | Page 6: Facebook Deep Dive | Campaign, Audience, Funnel | Looker Studio |
| D-011 | Page 7: Google Deep Dive | Campaign types, Keywords, Quality Score | Looker Studio |
| D-012 | Page 8: TikTok & Others Deep Dive | TikTok, LINE, Marketplace Ads | Looker Studio |
| D-013 | Page 9: AI Insights | ML Recommendations, Predictions | Looker Studio |

---

### [ ]  1.6.4 Dashboard Polish (MVP)

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| D-014 | Apply consistent styling | สร้าง theme และ styling | Looker Studio | - Consistent colors <br> - Professional look |
| D-015 | Basic performance check | ตรวจสอบ query performance | Looker Studio / BigQuery | - Load time acceptable |

**Checklist:**
- [ ] D-014: Apply consistent styling
- [ ] D-015: Basic performance check

---

### [ ]  1.6.5 Dashboard Polish (Phase 2 - Future)

> **ย้ายไป Phase 2:**

| Task ID | Task Name | Description | Technical Context |
|---------|-----------|-------------|-------------------|
| D-016 | Add tooltips & labels | เพิ่ม tooltips อธิบาย metrics | Looker Studio |
| D-017 | Mobile responsiveness | ปรับให้ดูบน mobile ได้ | Looker Studio |
| D-018 | Performance optimization | Optimize query performance | Looker Studio / BigQuery |

---

### [ ]  1.6.6 Demo Data (for Pitch/Testing)

> **Purpose:** สร้าง realistic demo data เพื่อใช้ในการ pitch และทดสอบระบบโดยไม่ต้องมี data จริง
> **Timing:** ทำหลังจาก Dashboard structure พร้อมแล้ว เพื่อให้มี schema และ visualization รองรับ

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| DEMO-001 | Create data generator framework | สร้าง base framework สำหรับ generate fake data | `scripts/demo_data/generator.py` | - Configurable date ranges <br> - Reproducible with seed |
| DEMO-002 | Generate e-commerce orders | สร้าง fake orders สำหรับ Shopee, Lazada, TikTok Shop | `scripts/demo_data/ecommerce.py` | - 10,000+ orders <br> - Realistic patterns (weekday/weekend, seasonal) <br> - Multiple shops |
| DEMO-003 | Generate ads performance data | สร้าง fake ads data สำหรับ Facebook, Google, TikTok, LINE | `scripts/demo_data/ads.py` | - 90 days of data <br> - Realistic metrics (CTR 1-3%, ROAS 1-5) <br> - Multiple campaigns |
| DEMO-004 | Generate GA4 analytics data | สร้าง fake GA4 sessions และ events | `scripts/demo_data/ga4.py` | - Sessions, pageviews, conversions <br> - Traffic sources breakdown |
| DEMO-005 | Generate product catalog | สร้าง fake product catalog พร้อม SKU mapping | `scripts/demo_data/products.py` | - 100+ products <br> - Cross-platform SKU mapping |
| DEMO-006 | Create data loader script | Script สำหรับ load demo data เข้า BigQuery | `scripts/demo_data/load_to_bigquery.py` | - Load to raw/staging layer <br> - Trigger mart refresh |
| DEMO-007 | Create demo data documentation | Document วิธีใช้และ customize demo data | `scripts/demo_data/README.md` | - Usage instructions <br> - Customization guide |

**Checklist:**
- [ ] DEMO-001: Create data generator framework
- [ ] DEMO-002: Generate e-commerce orders
- [ ] DEMO-003: Generate ads performance data
- [ ] DEMO-004: Generate GA4 analytics data
- [ ] DEMO-005: Generate product catalog
- [ ] DEMO-006: Create data loader script
- [ ] DEMO-007: Create demo data documentation

---

## [ ] Phase 1.7: Testing & Documentation (MVP)

> **Scope Reduction:** เน้น critical path testing, ลด comprehensive testing ไป Phase 2

### [ ]  1.7.1 Testing (MVP - Critical Paths Only)

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| TEST-001 | End-to-end testing | ทดสอบ full pipeline | Test environment | - Data flows correctly <br> - Dashboard shows data |
| TEST-002 | Data validation | ตรวจสอบความถูกต้องของข้อมูล | BigQuery | - Spot check with source <br> - No duplicates |

**Checklist:**
- [ ] TEST-001: End-to-end testing
- [ ] TEST-002: Data validation

---

### [ ]  1.7.2 Testing (Phase 2 - Future)

> **ย้ายไป Phase 2:**

| Task ID | Task Name | Description | Technical Context |
|---------|-----------|-------------|-------------------|
| TEST-003 | Performance testing | ทดสอบ performance | All components |
| TEST-004 | Error handling testing | ทดสอบ error scenarios | All components |
| TEST-005 | Unit tests (100% coverage) | Comprehensive unit tests | All modules |

---

### [ ]  1.7.3 Documentation (MVP - Essential Only)

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| DOC-001 | README.md | Project overview และ setup instructions | `README.md` | - Clear setup steps <br> - Architecture overview |
| DOC-002 | API credentials guide | วิธีการขอ API credentials | `.docs/api_credentials.md` | - Step-by-step for each platform |
| DOC-003 | Basic runbook | วิธี deploy และ check logs | `.docs/runbook.md` | - How to deploy <br> - How to check logs |

**Checklist:**
- [ ] DOC-001: README.md
- [ ] DOC-002: API credentials guide
- [ ] DOC-003: Basic runbook

---

### [ ]  1.7.4 Documentation (Phase 2 - Future)

> **ย้ายไป Phase 2:**

| Task ID | Task Name | Description | Technical Context |
|---------|-----------|-------------|-------------------|
| DOC-004 | Dashboard user guide | วิธีใช้งาน dashboard | `.docs/user_guide.md` |
| DOC-005 | Troubleshooting guide | วิธีแก้ปัญหาที่พบบ่อย | `.docs/troubleshooting.md` |
| DOC-006 | Comprehensive runbook | Full operations runbook | `.docs/runbook.md` |

---

## Summary

### Task Count by Phase (MVP)

| Phase | MVP Tasks | Phase 2 Tasks | Status |
|-------|-----------|---------------|--------|
| 1.1 Foundation (Base Classes) | 19 | 0 | In Progress |
| 1.2 Extractors (E-commerce + Ads/Analytics) | 33 | 0 | Pending |
| 1.3 Transformers & Loaders (incl. GA4) | 25 | 0 | Pending |
| 1.4 Pipelines & Mart & Simple Alerts | 14 | 4 (AI/ML) | Pending |
| 1.5 Cloud Deployment & Logging | 7 | 4 (Monitoring) | Pending |
| 1.6 Dashboard (5 pages MVP + Demo Data) | 18 | 7 (Deep Dive) | Pending |
| 1.7 Testing & Documentation | 5 | 6 (Comprehensive) | Pending |
| **Total MVP** | **~121** | - | **In Progress** |
| **Total Phase 2** | - | **21** | **Future** |

> **Scope Summary:**
> - Total MVP tasks: **~121 tasks** (ลบ Airbyte 9, เพิ่ม Ads/GA4 extractors 12)
> - ETL: Python Only (ไม่ใช้ Airbyte)
> - Ads SDKs: facebook-business, google-ads, tiktok-business-api-sdk
> - Analytics SDK: google-analytics-data
> - Dashboard: 5 หน้า (MVP)
> - AI/ML: Rule-based alerts (MVP), ML models in Phase 2

### Priority Order

1. **Critical Path:** F-001 → G-001 → B-001 → E-001 → A-001 → T-001 → L-001 → P-001 → M-001 → SA-001 → C-001 → D-001
2. **Dependencies:** ทำตาม Phase order (1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7)
3. **Parallelizable:**
   - E-commerce extractors: Shopee, Lazada, TikTok Shop ทำ parallel ได้
   - Ads extractors: Facebook, Google, TikTok, LINE, Shopee Ads, Lazada Ads ทำ parallel ได้
   - GA4 extractor: ทำ parallel กับ Ads extractors ได้

---

## Phase 2 Summary (Future)

> **สิ่งที่ย้ายไป Phase 2:**

| Category | Tasks |
|----------|-------|
| Dashboard Deep Dives | D-010, D-011, D-012, D-013 (Facebook, Google, TikTok, AI) |
| Dashboard Polish | D-016, D-017, D-018 (Tooltips, Mobile, Performance) |
| AI/ML Models | AI-001, AI-002, AI-003, AI-004 (Anomaly, Optimizer, Forecaster) |
| Monitoring & Alerts | MON-001, MON-002, MON-003, MON-004 (Cloud Monitoring, Slack) |
| Testing | TEST-003, TEST-004, TEST-005 (Performance, Error, Unit tests) |
| Documentation | DOC-004, DOC-005, DOC-006 (User guide, Troubleshooting) |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | - | Initial task breakdown |
| 1.1 | Dec 2025 | - | Added Airbyte setup tasks, GA4 transformers, GA4 dashboard page |
| 1.2 | Dec 2025 | - | TikTok Ads moved to Airbyte (AB-006), removed Python TikTok Ads tasks (A-011 to A-014), reduced total to 126 tasks |
| 1.3 | Dec 2025 | - | **MVP Scope Reduction:** 126 → 111 tasks, Dashboard 9→5, ML→Rule-based, ย้าย Monitoring/Deep Dive/AI ไป Phase 2 |
| 1.4 | Dec 2025 | - | **Added Demo Data:** +7 tasks (DEMO-001 to DEMO-007) for pitch/testing without real data, total 118 tasks |
| 1.5 | Dec 2025 | - | **Airbyte → Python Only:** ลบ 1.1.3 Airbyte Setup (9 tasks), เพิ่ม Ads/GA4 extractors ใน 1.2.2 (A-001 to A-021), ใช้ Official SDKs ทั้งหมด |
