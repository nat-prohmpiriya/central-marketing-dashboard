# Product Specification: Centralized Marketing Dashboard

## Overview

**Project Name:** Centralized Marketing Dashboard
**Version:** 1.0
**Last Updated:** December 2025

### Project Phases

| Phase | รูปแบบ | Scope | Status |
|-------|--------|-------|--------|
| **Phase 1** | Single Tenant | 1 ธุรกิจ, MVP พิสูจน์ concept | **Current Focus** |
| **Phase 2** | Multi-Tenant SaaS | หลายธุรกิจ, subscription model | Future (หลังลูกค้า approve) |

---

# PHASE 1: Single Tenant MVP

## Context
สร้าง Dashboard กลางสำหรับ **1 ธุรกิจ** ที่เชื่อมโยงข้อมูลจากหลายร้านค้าบนหลาย E-commerce platforms และหลาย Advertising platforms เพื่อให้ทีม Marketing สามารถดูภาพรวม วิเคราะห์ และตัดสินใจได้อย่างมีประสิทธิภาพ

### Target Audience (Phase 1)
- เจ้าของธุรกิจ E-commerce ที่มีหลายร้านบนหลาย platform
- Marketing Team ของธุรกิจนั้น
- Data Analyst ของธุรกิจนั้น

### Problem to Solve
1. ข้อมูลกระจายอยู่หลายแพลตฟอร์ม ต้อง login หลายที่เพื่อดูข้อมูล
2. ไม่สามารถเห็นภาพรวม ROI ของทั้งธุรกิจได้ในที่เดียว
3. ใช้เวลามากในการรวบรวมข้อมูลเพื่อทำรายงาน
4. ขาด insight เชื่อมโยงระหว่าง Ads spend กับยอดขายจริง
5. ไม่มีระบบแนะนำการจัดสรร budget อย่าง data-driven

---

## Data Sources Configuration (Phase 1)

> **Note:** จำนวนร้านและ accounts จะระบุภายหลังตามข้อมูลลูกค้าจริง

### E-commerce Platforms (Supported)

| Platform | API Support | Data Available | Notes |
|----------|-------------|----------------|-------|
| **Shopee** | Shopee Open Platform API | Orders, Products, Shop metrics | 30-day historical via API |
| **Lazada** | Lazada Open Platform API | Orders, Products, Shop metrics | Rate limits apply |
| **TikTok Shop** | TikTok Shop API | Orders, Products | Limited historical data |
| **JD Central** | JD Open Platform API | Orders, Products | Thailand specific |
| **LINE Shopping** | LINE API | Orders, Products | Integration via LINE OA |
| **NocNoc** | Custom API/CSV | Orders, Products | May require manual export |
| **Own Website** | WooCommerce/Shopify API | Full e-commerce data | Depends on platform |

### Advertising Platforms (Supported)

| Platform | API Support | Data Available | Notes |
|----------|-------------|----------------|-------|
| **Facebook/Meta Ads** | Marketing API | Campaigns, Ad Sets, Ads | Attribution window configurable |
| **Google Ads** | Google Ads API | Search, Display, Shopping, PMax, YouTube | Requires GCP project |
| **TikTok Ads** | TikTok Marketing API | Campaigns, Creatives | Regional restrictions |
| **LINE Ads** | LINE Ads API | Campaigns, Targeting | Thailand focused |
| **Shopee Ads** | Shopee Ads API | Product Ads, Shop Ads | In-platform advertising |
| **Lazada Ads** | Lazada Sponsored Solutions | Product Ads, Display | In-platform advertising |

### Analytics Platforms (Supported)

| Platform | API Support | Data Available | Notes |
|----------|-------------|----------------|-------|
| **Google Analytics 4** | GA4 Data API | Sessions, Users, Conversions, Events, Traffic sources | Requires GCP project |

### Configuration Required
- [ ] ระบุ platforms ที่ลูกค้าใช้จริง
- [ ] ระบุจำนวนร้านต่อ platform
- [ ] ระบุจำนวน ad accounts ต่อ platform
- [ ] เก็บ API credentials

---

## 1. User Personas

### Persona 1: Marketing Manager (Primary User)
**ชื่อ:** คุณแพร (Age 32)
**ตำแหน่ง:** Digital Marketing Manager
**ประสบการณ์:** 5 ปีในสาย Performance Marketing

**พฤติกรรม:**
- เช็ค metrics ทุกเช้า 8:00-9:00
- ต้องรายงานผลต่อ Management ทุกสัปดาห์
- ตัดสินใจเรื่อง budget allocation ระหว่างแพลตฟอร์ม
- ใช้ Excel เป็นหลักในการวิเคราะห์

**Pain Points:**
- ใช้เวลา 2-3 ชั่วโมง/วัน ในการรวบรวมข้อมูลจากหลายแพลตฟอร์ม
- ข้อมูลมักไม่ตรงกันระหว่างแพลตฟอร์ม (attribution window ต่างกัน)
- ยากที่จะเห็นภาพ cross-platform performance

**Goals:**
- ดูภาพรวมทั้งหมดในที่เดียว
- ลดเวลาทำรายงานลง 80%
- มี data-driven recommendations

---

### Persona 2: Business Owner
**ชื่อ:** คุณโจ้ (Age 45)
**ตำแหน่ง:** CEO / Founder
**ประสบการณ์:** 10+ ปี ในธุรกิจ E-commerce

**พฤติกรรม:**
- ดู high-level metrics สัปดาห์ละ 1-2 ครั้ง
- ต้องการรู้ ROI โดยรวมและ trend
- ไม่มีเวลา drill-down ลึก
- ตัดสินใจเชิงกลยุทธ์ระดับปี/ไตรมาส

**Pain Points:**
- ได้รับรายงานจาก Marketing ที่ format ต่างกันทุกสัปดาห์
- ไม่แน่ใจว่าตัวเลขที่ได้รับถูกต้องหรือไม่
- อยากเห็น trend และ forecast

**Goals:**
- Executive summary ที่เข้าใจง่าย
- เปรียบเทียบ period-over-period
- ดู ROI/ROAS ของแต่ละ channel ได้ทันที

---

### Persona 3: Data Analyst
**ชื่อ:** คุณบอส (Age 28)
**ตำแหน่ง:** Data Analyst
**ประสบการณ์:** 3 ปี ในสาย Data

**พฤติกรรม:**
- ต้อง export ข้อมูลเพื่อทำ deep analysis
- สร้าง custom reports ตามคำขอ
- ดูแล data quality และ accuracy

**Pain Points:**
- ต้อง manual export จากหลายแหล่งแล้วมา join กัน
- Data format ไม่ consistent
- ขาด historical data ที่รวมศูนย์

**Goals:**
- Single source of truth
- Clean, normalized data
- สามารถ query raw data ได้

---

## 2. User Journeys

### Journey 1: Daily Performance Check (Marketing Manager)

**Scenario:** คุณแพรเริ่มทำงานตอนเช้าและต้องการดู performance ของเมื่อวาน

| Step | Action | System Response | Outcome |
|------|--------|-----------------|---------|
| 1 | เปิด Dashboard | แสดงหน้า Overview พร้อม metrics หลัก | เห็นภาพรวมทันที |
| 2 | ดู Overall Metrics | แสดง Total Revenue, Ad Spend, ROAS, Orders | รู้ว่าเมื่อวานเป็นอย่างไร |
| 3 | เห็นว่า ROAS ต่ำกว่าปกติ | Highlight ตัวเลขที่ผิดปกติด้วยสีแดง | รู้ว่ามี anomaly |
| 4 | Drill-down ไป Channel | แสดง breakdown ตาม Ad Platform | เห็นว่า channel ไหนมีปัญหา |
| 5 | ดู Campaign Performance | แสดงรายละเอียด campaign ที่ performance ต่ำ | ระบุได้ว่า campaign ไหนต้องแก้ |
| 6 | Export รายงาน | สร้าง PDF/Excel report | พร้อมส่งให้ทีม/หัวหน้า |

---

### Journey 2: Weekly Budget Reallocation (Marketing Manager)

**Scenario:** คุณแพรต้องตัดสินใจจัดสรร budget ใหม่สำหรับสัปดาห์หน้า

| Step | Action | System Response | Outcome |
|------|--------|-----------------|---------|
| 1 | เปิดหน้า Channel Comparison | แสดง ROAS/CPA เปรียบเทียบทุก channel | เห็นว่า channel ไหน efficient ที่สุด |
| 2 | ดู Trend 7 วัน | แสดง graph trend ของแต่ละ channel | เข้าใจ pattern |
| 3 | ดู AI Recommendations | ระบบแนะนำ budget allocation | มี suggestion เป็นข้อมูลประกอบ |
| 4 | เปรียบเทียบ Scenario | What-if analysis ถ้าย้าย budget | ประมาณการผลลัพธ์ |
| 5 | ตัดสินใจ | - | Informed decision |

---

### Journey 3: Monthly Executive Report (Business Owner)

**Scenario:** คุณโจ้ต้องการดูผลประกอบการของเดือนที่ผ่านมา

| Step | Action | System Response | Outcome |
|------|--------|-----------------|---------|
| 1 | เปิด Executive Dashboard | แสดง high-level KPIs เดือนนี้ vs เดือนก่อน | เห็นภาพรวมทันที |
| 2 | ดู Revenue by Channel | Pie chart แสดงสัดส่วน revenue แต่ละ platform | เข้าใจ channel mix |
| 3 | ดู ROI Summary | Overall ROI และแยกตาม channel | รู้ว่าลงทุนคุ้มไหม |
| 4 | ดู Top Products | แสดง best-selling products | รู้ว่าสินค้าไหนขายดี |
| 5 | ดู YoY Comparison | เทียบกับปีก่อน same period | เห็น growth |
| 6 | Share Report | ส่ง link หรือ PDF ให้ stakeholders | รายงานพร้อมแชร์ |

---

### Journey 4: Shop Performance Analysis (Multi-store Owner)

**Scenario:** เจ้าของกิจการต้องการเปรียบเทียบ performance ของร้านค้าหลายร้าน

| Step | Action | System Response | Outcome |
|------|--------|-----------------|---------|
| 1 | เปิดหน้า Shop Comparison | แสดง table เปรียบเทียบทุกร้าน | เห็นภาพรวม |
| 2 | Sort by Revenue | เรียงลำดับตาม revenue | รู้ว่าร้านไหนทำเงินมากสุด |
| 3 | ดู Profit Margin | แสดง margin ของแต่ละร้าน | เห็นความ profitable |
| 4 | เปรียบเทียบ Conversion Rate | แสดง CR แต่ละ platform | รู้ว่า platform ไหน convert ดี |
| 5 | ดู Growth Rate | แสดง MoM/YoY growth | เห็น trend การเติบโต |

---

## 3. Core Features (Phase 1 MVP)

### 3.1 Dashboard Pages (5 หน้า - MVP)

> **Scope Reduction:** ลดจาก 9 หน้าเหลือ 5 หน้าหลักสำหรับ MVP
> หน้า Deep Dive (Facebook, Google, TikTok) และ AI Insights ย้ายไป Phase 2

#### Page 1: Executive Overview
**Purpose:** ให้ผู้บริหารเห็นภาพรวมธุรกิจในหน้าเดียว

**Key Elements:**
- Total Revenue (all platforms combined)
- Total Ad Spend (all ad platforms combined)
- Overall ROAS
- Total Orders
- Period comparison (vs yesterday, vs last week, vs last month)
- Revenue trend chart (30 days)
- Simple alerts (Rule-based: ROAS < 2, Revenue drop > 20%)

---

#### Page 2: Shop Performance (All Stores)
**Purpose:** เปรียบเทียบ performance ของทุกร้านค้าบนทุก platform

**Key Elements:**
- Revenue breakdown by shop & platform
- Orders by shop
- Average Order Value (AOV) by shop
- Conversion Rate by shop
- Growth rate comparison
- Platform comparison (Shopee vs Lazada vs TikTok vs Others)

---

#### Page 3: Ads Performance Overview
**Purpose:** ภาพรวม advertising performance ทุก platform (รวม Facebook, Google, TikTok, LINE, Marketplace Ads)

**Key Elements:**
- Total Ad Spend by platform
- ROAS by platform
- CPA by platform
- Impressions, Clicks, CTR by platform
- Campaign performance table (all platforms combined)
- Spend vs Revenue correlation chart
- Budget utilization rate
- Simple performance flags (Rule-based: ROAS < 2 = Poor, 2-4 = OK, > 4 = Good)

---

#### Page 4: Product Analytics
**Purpose:** วิเคราะห์ performance ระดับ product

**Key Elements:**
- Top selling products (by revenue, by units)
- Product performance by platform
- Price comparison across platforms
- Product margin analysis
- Category performance

---

#### Page 5: Website Analytics (GA4 - Basic)
**Purpose:** วิเคราะห์ traffic และ user behavior จาก Google Analytics 4

**Key Elements:**
- Sessions & Users overview
- Traffic sources breakdown (Organic, Paid, Direct, Social, Referral)
- Top landing pages
- Basic conversion metrics
- Device breakdown

---

### 3.2 Dashboard Pages (Phase 2 - Future)

> **ย้ายไป Phase 2:**

#### Page 6: Facebook/Meta Ads Deep Dive (Phase 2)
- Campaign performance table (spend, revenue, ROAS, CPA)
- Ad Set breakdown
- Audience performance (age, gender, placement)
- Creative performance
- Hourly/Daily trend
- Funnel metrics

#### Page 7: Google Ads Deep Dive (Phase 2)
- Campaign type breakdown (Search, Display, Shopping, PMax, YouTube)
- Keyword performance
- Search terms report
- Device & Geographic performance
- Quality Score tracking

#### Page 8: TikTok & Other Ads Deep Dive (Phase 2)
- TikTok Ads: Video creative, Engagement metrics
- LINE Ads: Campaign performance, LAP metrics
- Marketplace Ads: Product Ads, Shop Ads performance

#### Page 9: AI Insights & Recommendations (Phase 2)
- Budget allocation recommendations (ML-based)
- Anomaly detection alerts (Statistical models)
- Performance predictions (Time series forecasting)
- Cross-channel attribution insights

---

### 3.3 Data Pipeline (Phase 1)

**ETL Strategy: Hybrid Approach (Airbyte + Python)**

| Data Source | ETL Tool | Reason |
|-------------|----------|--------|
| Facebook Ads | Airbyte | มี connector สำเร็จรูป (11 streams, 18 insight reports) |
| Google Ads | Airbyte | มี connector สำเร็จรูป (19 tables, custom GAQL) |
| Google Analytics 4 | Airbyte | มี connector สำเร็จรูป |
| TikTok Ads | Airbyte | มี connector สำเร็จรูป (50+ streams, reports by demographics) |
| Shopee | Python | ไม่มี Airbyte connector |
| Lazada | Python | ไม่มี Airbyte connector |
| TikTok Shop | Python | ไม่มี Airbyte connector (TikTok Marketing ≠ TikTok Shop) |
| LINE Ads | Python | ไม่มี Airbyte connector |
| Shopee Ads | Python | ไม่มี Airbyte connector |
| Lazada Ads | Python | ไม่มี Airbyte connector |

**Data Flow:**
```
                    ┌─────────────┐
[Facebook Ads] ────►│             │
[Google Ads]   ────►│   Airbyte   │────┐
[GA4]          ────►│  (4 sources)│    │
[TikTok Ads]   ────►│             │    │
                    └─────────────┘    │
                                       ▼
[Shopee]       ────►┌─────────────┐  ┌─────────────┐   ┌───────────────┐
[Lazada]       ────►│   Python    │─►│  BigQuery   │──►│ Looker Studio │
[TikTok Shop]  ────►│   Scripts   │  │             │   │               │
[LINE Ads]     ────►│  (6 sources)│  └─────────────┘   └───────────────┘
[Shopee Ads]   ────►│             │
[Lazada Ads]   ────►└─────────────┘
[CSV Uploads]  ────►
```

**Update Frequency:**
- Ads data: Every 6 hours
- Orders data: Every 6 hours
- Product data: Daily

**Data Normalization:**
- Currency: THB
- Timezone: Asia/Bangkok
- SKU Mapping: Cross-platform product matching

---

### 3.4 AI/ML Features (Phase 1 MVP - Rule-based)

> **Scope Reduction:** ใช้ Rule-based แทน ML Model สำหรับ MVP
> ML Models ย้ายไป Phase 2

**Simple Alerts (Rule-based):**
- ROAS < 2 → แจ้งเตือน "Campaign ต้องปรับปรุง"
- Revenue drop > 20% (vs yesterday) → แจ้งเตือน "Revenue ลดลงผิดปกติ"
- CPA > target threshold → แจ้งเตือน "CPA สูงเกินไป"

**Performance Flags:**
- ROAS < 2 = 🔴 Poor
- ROAS 2-4 = 🟡 OK
- ROAS > 4 = 🟢 Good

**Budget Recommendations (Simple):**
- ถ้า ROAS สูง → แนะนำเพิ่ม budget
- ถ้า ROAS ต่ำ → แนะนำลด budget
- Method: Simple threshold rules (ไม่ใช้ ML)

---

### 3.5 AI/ML Features (Phase 2 - Future)

> **ย้ายไป Phase 2:**

**Advanced Anomaly Detection:**
- Method: Z-score / IQR threshold / Statistical models

**Performance Prediction:**
- 7-day forecast per platform
- Method: Time series (moving average, ARIMA)

**Budget Optimization:**
- ML-based budget allocation
- Method: Optimization algorithms

---

## 4. Success Metrics (Phase 1)

### Primary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to Insight | < 5 minutes | เวลาตั้งแต่เปิด dashboard จนตัดสินใจได้ |
| Report Generation Time | < 2 minutes | เวลาสร้าง weekly/monthly report |
| Data Freshness | < 6 hours | ความล่าช้าของข้อมูลล่าสุด |

### Business Impact

| Metric | Target | Measurement |
|--------|--------|-------------|
| ROAS Improvement | +15% | หลังใช้ AI recommendations |
| Report Time Saved | 10+ hours/week | เวลาที่ประหยัดได้ |
| Customer Satisfaction | Approve Phase 2 | ลูกค้าพอใจและต้องการ scale |

---

## 5. Edge Cases & Risk Mitigation

### Data Issues

| Edge Case | Mitigation |
|-----------|------------|
| API rate limit exceeded | Retry logic, queue system |
| Platform API changes | Version monitoring, alerts |
| Missing data | Data quality checks, gap highlighting |
| Duplicate orders | Deduplication logic |
| Currency inconsistency | Normalize to THB |
| Timezone mismatch | Standardize to Asia/Bangkok |

### System Issues

| Edge Case | Mitigation |
|-----------|------------|
| BigQuery quota exceeded | Monitor usage, set quotas |
| Looker Studio timeout | Optimize queries, aggregate data |
| ETL job failure | Monitoring, auto-retry, alerts |

---

## 6. Out of Scope (Phase 1 MVP)

สิ่งที่ **ไม่รวม** ใน Phase 1 MVP:

**User & Multi-tenant:**
- ❌ User registration / authentication system
- ❌ Multi-tenant data isolation
- ❌ Subscription & billing
- ❌ Self-service platform connection (ต้อง dev เชื่อมให้)
- ❌ White-label / custom branding

**Dashboard Deep Dives:**
- ❌ Facebook Ads Deep Dive page (ใช้ Ads Overview รวมแทน)
- ❌ Google Ads Deep Dive page (ใช้ Ads Overview รวมแทน)
- ❌ TikTok & Others Deep Dive page (ใช้ Ads Overview รวมแทน)
- ❌ AI Insights page (ใช้ Simple alerts ใน Overview แทน)

**AI/ML:**
- ❌ Advanced ML models (ใช้ Rule-based แทน)
- ❌ Anomaly Detection models (ใช้ threshold alerts แทน)
- ❌ Performance Forecasting (ย้ายไป Phase 2)
- ❌ Budget Optimizer ML (ใช้ simple rules แทน)

**Automation & Monitoring:**
- ❌ Cloud Monitoring dashboards (manual check แทน)
- ❌ Automated alerting system (Slack/Email) - ย้ายไป Phase 2
- ❌ Unit Test 100% coverage (ทำแค่ critical paths)
- ❌ CI/CD pipeline (manual deploy แทน)

---

# PHASE 2: Multi-Tenant SaaS (Future Roadmap)

> **Trigger:** เมื่อลูกค้า Phase 1 approve และต้องการ scale

## Additional Features (Phase 2)

### User Management
- User registration / login
- Role-based access control (Admin, Manager, Viewer)
- Team invitation system

### Multi-Tenant Architecture
- Data isolation per tenant
- Tenant-specific configurations
- Shared infrastructure with logical separation

### Self-Service Onboarding
- OAuth connection flow for each platform
- Guided setup wizard
- API credential management UI

### Subscription & Billing
- Pricing tiers (Free, Pro, Enterprise)
- Usage-based billing
- Payment integration (Stripe/Omise)

### Advanced AI/ML
- Machine learning models for predictions
- Custom recommendation engines
- Automated optimization

### Admin Dashboard
- Customer management
- Usage analytics
- System health monitoring

---

## Phase 2 Technical Additions

| Component | Phase 1 | Phase 2 |
|-----------|---------|---------|
| Frontend | Looker Studio | Custom Web App (Next.js) |
| Backend | Python Scripts | FastAPI/Django |
| Database | BigQuery only | BigQuery + PostgreSQL |
| Auth | None (shared access) | Firebase Auth / Auth0 |
| Hosting | Cloud Functions | Cloud Run / GKE |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | - | Initial specification |
| 1.1 | Dec 2025 | - | Restructured to Phase 1 (Single Tenant) + Phase 2 roadmap |
| 1.2 | Dec 2025 | - | Added GA4, updated ETL strategy (TikTok Ads now uses Airbyte) |
| 1.3 | Dec 2025 | - | **MVP Scope Reduction:** ลด Dashboard 9→5 หน้า, เปลี่ยน ML เป็น Rule-based, ย้าย Automation/Deep Dive ไป Phase 2 |
