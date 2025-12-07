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

## Phase 1.1: Foundation (Week 1-2)

### 1.1.1 Project Setup

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| F-001 | Initialize Python project | สร้าง project structure พื้นฐาน | `pyproject.toml`, `requirements.txt`, `.gitignore` | - สามารถ `pip install -e .` ได้ <br> - มี virtual environment |
| F-002 | Setup Git repository | Initialize git และ create `.gitignore` | Root directory | - มี `.gitignore` ครอบคลุม Python, IDE, secrets <br> - Initial commit สำเร็จ |
| F-003 | Create folder structure | สร้างโครงสร้างโฟลเดอร์ตาม technical plan | `src/`, `tests/`, `config/`, `sql/`, `scripts/` | - ทุกโฟลเดอร์มี `__init__.py` <br> - โครงสร้างตรงตาม plan |
| F-004 | Setup configuration management | สร้างระบบจัดการ config | `src/utils/config.py`, `config/*.yaml` | - Load config จาก YAML ได้ <br> - Support environment variables |
| F-005 | Setup logging | สร้างระบบ logging | `src/utils/logging.py` | - Log ออก console และ file <br> - มี log levels (DEBUG, INFO, ERROR) |
| F-006 | Create .env template | สร้าง template สำหรับ environment variables | `.env.example` | - มีทุก variables ที่จำเป็น <br> - มี comments อธิบาย |

**Checklist:**
- [ ] F-001: Initialize Python project
- [ ] F-002: Setup Git repository
- [ ] F-003: Create folder structure
- [ ] F-004: Setup configuration management
- [ ] F-005: Setup logging
- [ ] F-006: Create .env template

---

### 1.1.2 GCP Setup

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
- [ ] G-001: Create GCP project
- [ ] G-002: Enable required APIs
- [ ] G-003: Create service account
- [ ] G-004: Setup BigQuery datasets
- [ ] G-005: Setup Secret Manager
- [ ] G-006: Create GCS staging bucket
- [ ] G-007: Create setup script

---

### 1.1.3 Airbyte Setup

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| AB-001 | Setup Airbyte Cloud account | สมัคร Airbyte Cloud หรือ deploy self-hosted | Airbyte Cloud / Docker | - Account created <br> - Can access UI |
| AB-002 | Configure BigQuery destination | เชื่อม Airbyte กับ BigQuery | Airbyte UI | - Connection successful <br> - Test sync works |
| AB-003 | Setup Facebook Ads source | Configure Facebook Marketing connector | Airbyte UI, `airbyte/connections/facebook_ads.yaml` | - Auth successful <br> - Test sync works |
| AB-004 | Setup Google Ads source | Configure Google Ads connector | Airbyte UI, `airbyte/connections/google_ads.yaml` | - Auth successful <br> - Test sync works |
| AB-005 | Setup GA4 source | Configure Google Analytics 4 connector | Airbyte UI, `airbyte/connections/ga4.yaml` | - Auth successful <br> - Test sync works |
| AB-006 | Configure sync schedules | ตั้ง schedule สำหรับทุก connection | Airbyte UI | - Schedules set (every 6 hours) |
| AB-007 | Test full sync | ทดสอบ sync ข้อมูลจริง | Airbyte UI, BigQuery | - Data appears in BigQuery <br> - Schema correct |
| AB-008 | Document Airbyte setup | เขียน documentation | `airbyte/README.md` | - Setup steps documented |

**Checklist:**
- [ ] AB-001: Setup Airbyte Cloud account
- [ ] AB-002: Configure BigQuery destination
- [ ] AB-003: Setup Facebook Ads source
- [ ] AB-004: Setup Google Ads source
- [ ] AB-005: Setup GA4 source
- [ ] AB-006: Configure sync schedules
- [ ] AB-007: Test full sync
- [ ] AB-008: Document Airbyte setup

---

### 1.1.4 Base Classes

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

## Phase 1.2: Extractors (Week 3-4)

### 1.2.1 E-commerce Extractors

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

### 1.2.2 Ads Extractors

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| A-001 | Facebook Ads authentication | Implement Facebook Marketing API auth | `src/extractors/facebook_ads.py` | - Use access token <br> - Handle token refresh |
| A-002 | Facebook Ads account insights | ดึง account-level insights | `src/extractors/facebook_ads.py` | - Get daily insights <br> - Include all required metrics |
| A-003 | Facebook Ads campaign insights | ดึง campaign-level insights | `src/extractors/facebook_ads.py` | - Get campaign performance <br> - Include breakdowns |
| A-004 | Facebook Ads adset/ad insights | ดึง adset และ ad-level insights | `src/extractors/facebook_ads.py` | - Get adset performance <br> - Get ad performance |
| A-005 | Facebook Ads extractor tests | Unit tests | `tests/test_extractors/test_facebook_ads.py` | - Mock API calls <br> - All tests pass |
| A-006 | Google Ads authentication | Implement Google Ads API auth | `src/extractors/google_ads.py` | - OAuth2 flow <br> - Refresh token works |
| A-007 | Google Ads campaign report | ดึง campaign performance | `src/extractors/google_ads.py` | - GAQL query works <br> - Get all campaign types |
| A-008 | Google Ads ad group report | ดึง ad group performance | `src/extractors/google_ads.py` | - Get ad group metrics |
| A-009 | Google Ads keyword report | ดึง keyword performance | `src/extractors/google_ads.py` | - Get keyword metrics <br> - Include quality score |
| A-010 | Google Ads extractor tests | Unit tests | `tests/test_extractors/test_google_ads.py` | - Mock API calls <br> - All tests pass |
| A-011 | TikTok Ads authentication | Implement TikTok Ads API auth | `src/extractors/tiktok_ads.py` | - Generate access token |
| A-012 | TikTok Ads campaign report | ดึง campaign performance | `src/extractors/tiktok_ads.py` | - Get campaign metrics <br> - Include video metrics |
| A-013 | TikTok Ads adgroup/ad report | ดึง adgroup และ ad performance | `src/extractors/tiktok_ads.py` | - Get adgroup metrics <br> - Get ad metrics |
| A-014 | TikTok Ads extractor tests | Unit tests | `tests/test_extractors/test_tiktok_ads.py` | - Mock API calls <br> - All tests pass |
| A-015 | LINE Ads extractor | ดึง LINE Ads performance (ถ้าใช้) | `src/extractors/line_ads.py` | - Get campaign metrics |
| A-016 | Shopee Ads extractor | ดึง Shopee Ads performance (ถ้าใช้) | `src/extractors/shopee_ads.py` | - Get product ads metrics |
| A-017 | Lazada Ads extractor | ดึง Lazada Ads performance (ถ้าใช้) | `src/extractors/lazada_ads.py` | - Get sponsored products metrics |

**Checklist:**
- [ ] A-001: Facebook Ads authentication
- [ ] A-002: Facebook Ads account insights
- [ ] A-003: Facebook Ads campaign insights
- [ ] A-004: Facebook Ads adset/ad insights
- [ ] A-005: Facebook Ads extractor tests
- [ ] A-006: Google Ads authentication
- [ ] A-007: Google Ads campaign report
- [ ] A-008: Google Ads ad group report
- [ ] A-009: Google Ads keyword report
- [ ] A-010: Google Ads extractor tests
- [ ] A-011: TikTok Ads authentication
- [ ] A-012: TikTok Ads campaign report
- [ ] A-013: TikTok Ads adgroup/ad report
- [ ] A-014: TikTok Ads extractor tests
- [ ] A-015: LINE Ads extractor (optional)
- [ ] A-016: Shopee Ads extractor (optional)
- [ ] A-017: Lazada Ads extractor (optional)

---

## Phase 1.3: Transformers & Loaders (Week 5-6)

### 1.3.1 Order Transformers

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

### 1.3.2 Ads Transformers

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

### 1.3.3 GA4 Transformers

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

### 1.3.4 Product & SKU Mapping

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

### 1.3.5 BigQuery Schemas & Loading

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

## Phase 1.4: Pipelines & Mart Layer (Week 7-8)

### 1.4.1 ETL Pipelines

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

### 1.4.2 Mart Layer SQL

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

### 1.4.3 AI/ML Features

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| AI-001 | Anomaly detection | ตรวจจับ metrics ที่ผิดปกติ | `src/models/anomaly_detection.py` | - Z-score detection <br> - Flag anomalies in daily_performance |
| AI-002 | Budget optimizer | แนะนำ budget allocation | `src/models/budget_optimizer.py` | - Based on historical ROAS <br> - Generate recommendations |
| AI-003 | Performance forecaster | พยากรณ์ 7 วัน | `src/models/forecaster.py` | - Moving average <br> - Trend analysis |
| AI-004 | AI recommendations pipeline | Pipeline to generate recommendations | `src/pipelines/ai_pipeline.py` | - Run all AI models <br> - Save to mart_ai_recommendations |
| AI-005 | AI model tests | Unit tests | `tests/test_models/` | - All tests pass |

**Checklist:**
- [ ] AI-001: Anomaly detection
- [ ] AI-002: Budget optimizer
- [ ] AI-003: Performance forecaster
- [ ] AI-004: AI recommendations pipeline
- [ ] AI-005: AI model tests

---

## Phase 1.5: Cloud Deployment (Week 8-9)

### 1.5.1 Cloud Functions

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| C-001 | E-commerce Cloud Function | Deploy e-commerce pipeline | `cloud_functions/etl_ecommerce/` | - Function deployed <br> - Triggered successfully |
| C-002 | Ads Cloud Function | Deploy ads pipeline | `cloud_functions/etl_ads/` | - Function deployed <br> - Triggered successfully |
| C-003 | Mart Cloud Function | Deploy mart pipeline | `cloud_functions/etl_mart/` | - Function deployed <br> - Triggered successfully |
| C-004 | AI Cloud Function | Deploy AI pipeline | `cloud_functions/etl_ai/` | - Function deployed <br> - Triggered successfully |
| C-005 | Setup Cloud Scheduler | สร้าง scheduled jobs | GCP Console / Terraform | - E-commerce: every 6 hours <br> - Ads: every 6 hours <br> - Mart: after ETL <br> - AI: daily 7 AM |
| C-006 | Deploy script | Script to deploy all functions | `scripts/deploy_functions.sh` | - One command deploy |

**Checklist:**
- [ ] C-001: E-commerce Cloud Function
- [ ] C-002: Ads Cloud Function
- [ ] C-003: Mart Cloud Function
- [ ] C-004: AI Cloud Function
- [ ] C-005: Setup Cloud Scheduler
- [ ] C-006: Deploy script

---

### 1.5.2 Monitoring & Alerts

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| MON-001 | Setup Cloud Logging | Configure logging for all functions | GCP Console | - Logs visible in Cloud Logging |
| MON-002 | Setup error alerts | Alert on function failures | Cloud Monitoring | - Email/Slack on error |
| MON-003 | Setup data freshness alert | Alert if data > 12 hours old | Cloud Monitoring | - Alert when stale |
| MON-004 | Create monitoring dashboard | GCP monitoring dashboard | Cloud Monitoring | - Show function status <br> - Show BigQuery usage |

**Checklist:**
- [ ] MON-001: Setup Cloud Logging
- [ ] MON-002: Setup error alerts
- [ ] MON-003: Setup data freshness alert
- [ ] MON-004: Create monitoring dashboard

---

## Phase 1.6: Dashboard (Week 9-10)

### 1.6.1 Looker Studio Setup

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

### 1.6.2 Dashboard Pages

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| D-005 | Page 1: Executive Overview | หน้า overview | Looker Studio | - KPI scorecards <br> - Revenue trend chart <br> - Period comparison |
| D-006 | Page 2: Shop Performance | หน้า shop comparison | Looker Studio | - Shop comparison table <br> - Platform breakdown <br> - Growth metrics |
| D-007 | Page 3: Ads Overview | หน้า ads summary | Looker Studio | - Spend by platform <br> - ROAS comparison <br> - CTR/CPA metrics |
| D-008 | Page 4: Facebook Deep Dive | หน้า Facebook Ads | Looker Studio | - Campaign table <br> - Audience breakdown <br> - Funnel chart |
| D-009 | Page 5: Google Deep Dive | หน้า Google Ads | Looker Studio | - Campaign type breakdown <br> - Keyword table <br> - Quality score |
| D-010 | Page 6: TikTok & Others | หน้า TikTok และอื่นๆ | Looker Studio | - TikTok metrics <br> - Video engagement <br> - Other platforms |
| D-011 | Page 7: Product Analytics | หน้า product analysis | Looker Studio | - Top products table <br> - Category breakdown <br> - Platform comparison |
| D-012 | Page 8: Website Analytics (GA4) | หน้า GA4 website analytics | Looker Studio | - Sessions & users trend <br> - Traffic sources breakdown <br> - Top pages table <br> - Conversion funnel |
| D-013 | Page 9: AI Insights | หน้า AI recommendations | Looker Studio | - Recommendations list <br> - Anomaly alerts <br> - Predictions chart |

**Checklist:**
- [ ] D-005: Page 1: Executive Overview
- [ ] D-006: Page 2: Shop Performance
- [ ] D-007: Page 3: Ads Overview
- [ ] D-008: Page 4: Facebook Deep Dive
- [ ] D-009: Page 5: Google Deep Dive
- [ ] D-010: Page 6: TikTok & Others
- [ ] D-011: Page 7: Product Analytics
- [ ] D-012: Page 8: Website Analytics (GA4)
- [ ] D-013: Page 9: AI Insights

---

### 1.6.3 Dashboard Polish

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| D-014 | Apply consistent styling | สร้าง theme และ styling | Looker Studio | - Consistent colors <br> - Professional look |
| D-015 | Add tooltips & labels | เพิ่ม tooltips อธิบาย metrics | Looker Studio | - All metrics have tooltips |
| D-016 | Mobile responsiveness | ปรับให้ดูบน mobile ได้ | Looker Studio | - Readable on mobile |
| D-017 | Performance optimization | Optimize query performance | Looker Studio / BigQuery | - Load time < 3 seconds |

**Checklist:**
- [ ] D-014: Apply consistent styling
- [ ] D-015: Add tooltips & labels
- [ ] D-016: Mobile responsiveness
- [ ] D-017: Performance optimization

---

## Phase 1.7: Testing & Documentation (Week 10)

### 1.7.1 Testing

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| TEST-001 | End-to-end testing | ทดสอบ full pipeline | Test environment | - Data flows correctly <br> - Dashboard shows data |
| TEST-002 | Data validation | ตรวจสอบความถูกต้องของข้อมูล | BigQuery | - Spot check with source <br> - No duplicates |
| TEST-003 | Performance testing | ทดสอบ performance | All components | - ETL completes in time <br> - Dashboard loads fast |
| TEST-004 | Error handling testing | ทดสอบ error scenarios | All components | - Graceful error handling <br> - Alerts work |

**Checklist:**
- [ ] TEST-001: End-to-end testing
- [ ] TEST-002: Data validation
- [ ] TEST-003: Performance testing
- [ ] TEST-004: Error handling testing

---

### 1.7.2 Documentation

| Task ID | Task Name | Description | Technical Context | Acceptance Criteria |
|---------|-----------|-------------|-------------------|---------------------|
| DOC-001 | README.md | Project overview และ setup instructions | `README.md` | - Clear setup steps <br> - Architecture overview |
| DOC-002 | API credentials guide | วิธีการขอ API credentials | `.docs/api_credentials.md` | - Step-by-step for each platform |
| DOC-003 | Dashboard user guide | วิธีใช้งาน dashboard | `.docs/user_guide.md` | - Feature walkthrough |
| DOC-004 | Troubleshooting guide | วิธีแก้ปัญหาที่พบบ่อย | `.docs/troubleshooting.md` | - Common issues & solutions |
| DOC-005 | Runbook | Operations runbook | `.docs/runbook.md` | - How to monitor <br> - How to fix issues |

**Checklist:**
- [ ] DOC-001: README.md
- [ ] DOC-002: API credentials guide
- [ ] DOC-003: Dashboard user guide
- [ ] DOC-004: Troubleshooting guide
- [ ] DOC-005: Runbook

---

## Summary

### Task Count by Phase

| Phase | Tasks | Status |
|-------|-------|--------|
| 1.1 Foundation (incl. Airbyte) | 27 | Pending |
| 1.2 Extractors | 29 | Pending |
| 1.3 Transformers & Loaders (incl. GA4) | 25 | Pending |
| 1.4 Pipelines & Mart | 16 | Pending |
| 1.5 Cloud Deployment | 10 | Pending |
| 1.6 Dashboard (incl. GA4 page) | 17 | Pending |
| 1.7 Testing & Documentation | 9 | Pending |
| **Total** | **133** | **Pending** |

### Priority Order

1. **Critical Path:** F-001 → G-001 → AB-001 → B-001 → E-001 → T-001 → L-001 → P-001 → M-001 → C-001 → D-001
2. **Dependencies:** ทำตาม Phase order (1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7)
3. **Parallelizable:**
   - Extractors สามารถทำ parallel ได้ (Shopee, Lazada, TikTok ทำพร้อมกัน)
   - Airbyte setup (AB-003, AB-004, AB-005) สามารถทำ parallel ได้

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | - | Initial task breakdown |
| 1.1 | Dec 2025 | - | Added Airbyte setup tasks (AB-001 to AB-008), GA4 transformers (T-012 to T-015), GA4 dashboard page |
