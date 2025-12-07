# Dashboard Specification

## Overview

This document provides detailed specifications for 5 MVP dashboard pages in Looker Studio.

## Global Settings

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Primary Blue | `#1A73E8` | Headers, primary metrics |
| Success Green | `#34A853` | Positive trends, good performance |
| Warning Orange | `#FBBC04` | Warnings, moderate issues |
| Error Red | `#EA4335` | Alerts, poor performance |
| Neutral Gray | `#5F6368` | Secondary text |
| Background | `#F8F9FA` | Page background |

### Platform Colors

| Platform | Hex | Usage |
|----------|-----|-------|
| Shopee | `#EE4D2D` | Shopee metrics |
| Lazada | `#0F146D` | Lazada metrics |
| TikTok Shop | `#000000` | TikTok Shop metrics |
| Facebook | `#1877F2` | Facebook Ads |
| Google | `#4285F4` | Google Ads |
| LINE | `#00B900` | LINE Ads |

### Performance Flags

| Flag | Condition | Color |
|------|-----------|-------|
| Poor | ROAS < 2 | Red `#EA4335` |
| OK | ROAS 2-4 | Orange `#FBBC04` |
| Good | ROAS > 4 | Green `#34A853` |

---

## Page 1: Executive Overview (D-005)

### Purpose
High-level business overview with key KPIs and alerts for executives.

### Data Source
- Primary: `mart_daily_performance`
- Secondary: `mart_alerts_summary`

### Layout (1920x1080)

```
+------------------------------------------------------------------+
| [Logo]  EXECUTIVE OVERVIEW          [Date Filter] [Platform Filter]|
+------------------------------------------------------------------+
|                                                                    |
|  +------------+  +------------+  +------------+  +------------+    |
|  | REVENUE    |  | ORDERS     |  | AD SPEND   |  | ROAS       |    |
|  | ฿1.2M      |  | 5,432      |  | ฿250K      |  | 4.8x       |    |
|  | ▲ +12%     |  | ▲ +8%      |  | ▼ -5%      |  | ▲ +15%     |    |
|  +------------+  +------------+  +------------+  +------------+    |
|                                                                    |
|  +----------------------------------+  +------------------------+  |
|  |     REVENUE TREND (7 days)      |  |    ALERTS SUMMARY      |  |
|  |    ___                          |  |                        |  |
|  |   /   \    ___                  |  |  🔴 2 Critical         |  |
|  |  /     \__/   \                 |  |  🟡 5 Warning          |  |
|  | /              \___             |  |  🔵 3 Info             |  |
|  +----------------------------------+  +------------------------+  |
|                                                                    |
|  +----------------------------------+  +------------------------+  |
|  |   PERIOD COMPARISON             |  |   PLATFORM BREAKDOWN   |  |
|  |   This Week vs Last Week        |  |                        |  |
|  |   Revenue:  ฿1.2M vs ฿1.1M      |  |   Shopee    45%        |  |
|  |   Orders:   5,432 vs 5,100      |  |   Lazada    35%        |  |
|  |   ROAS:     4.8x vs 4.2x        |  |   TikTok    20%        |  |
|  +----------------------------------+  +------------------------+  |
|                                                                    |
+------------------------------------------------------------------+
```

### Components

#### 1. KPI Scorecards (4 cards)

| Scorecard | Metric | Comparison | Format |
|-----------|--------|------------|--------|
| Revenue | `SUM(revenue)` | vs previous period | Currency ฿ |
| Orders | `SUM(orders)` | vs previous period | Number |
| Ad Spend | `SUM(ad_spend)` | vs previous period | Currency ฿ |
| ROAS | `SUM(revenue)/SUM(ad_spend)` | vs previous period | Decimal (1 place) + "x" |

**Scorecard Settings:**
- Size: 200x120 px
- Show comparison: Yes
- Comparison type: Previous period
- Positive change: Green arrow up
- Negative change: Red arrow down

#### 2. Revenue Trend Chart

| Property | Value |
|----------|-------|
| Chart Type | Time series (Line) |
| Dimension | `date` |
| Metric | `SUM(revenue)` |
| Date Range | Last 7 days |
| Style | Smooth line, area fill |

#### 3. Alerts Summary

| Property | Value |
|----------|-------|
| Chart Type | Scorecard or Table |
| Data Source | `mart_alerts_summary` |
| Filter | `status = 'active'` |
| Group By | `severity` |
| Metric | `COUNT(alert_id)` |

**Conditional Formatting:**
- Critical: Red background
- Warning: Orange background
- Info: Blue background

#### 4. Period Comparison Table

| Property | Value |
|----------|-------|
| Chart Type | Table with comparison |
| Metrics | Revenue, Orders, ROAS |
| Comparison | Previous period % change |

#### 5. Platform Breakdown

| Property | Value |
|----------|-------|
| Chart Type | Pie chart or Donut |
| Dimension | `platform` |
| Metric | `SUM(revenue)` |
| Colors | Platform-specific colors |

### Simple Alerts (Calculated Fields)

```
Alert: Low ROAS
Formula: CASE WHEN SUM(revenue)/SUM(ad_spend) < 2 THEN "⚠️ ROAS Below Target" ELSE "" END

Alert: Revenue Drop
Formula: CASE WHEN (SUM(revenue) - SUM(revenue_prev_period))/SUM(revenue_prev_period) < -0.1 THEN "📉 Revenue Dropped >10%" ELSE "" END
```

---

## Page 2: Shop Performance (D-006)

### Purpose
Compare performance across different shops and platforms.

### Data Source
- Primary: `mart_shop_performance`

### Layout

```
+------------------------------------------------------------------+
| [Logo]  SHOP PERFORMANCE            [Date Filter] [Platform Filter]|
+------------------------------------------------------------------+
|                                                                    |
|  +----------------------------------------------------------------+|
|  |                    SHOP COMPARISON TABLE                       ||
|  |----------------------------------------------------------------||
|  | Shop      | Platform | Revenue  | Orders | ROAS | Growth      ||
|  |-----------|----------|----------|--------|------|-------------||
|  | Shop A    | Shopee   | ฿500K    | 2,100  | 5.2x | ▲ +15%      ||
|  | Shop B    | Lazada   | ฿420K    | 1,800  | 4.8x | ▲ +8%       ||
|  | Shop C    | TikTok   | ฿280K    | 1,532  | 3.9x | ▼ -3%       ||
|  +----------------------------------------------------------------+|
|                                                                    |
|  +----------------------------------+  +------------------------+  |
|  |   REVENUE BY PLATFORM           |  |   GROWTH METRICS       |  |
|  |                                  |  |                        |  |
|  |   ████████████  Shopee 45%      |  |   WoW Growth: +12%     |  |
|  |   █████████     Lazada 35%      |  |   MoM Growth: +25%     |  |
|  |   ████          TikTok 20%      |  |   YoY Growth: +45%     |  |
|  +----------------------------------+  +------------------------+  |
|                                                                    |
|  +----------------------------------------------------------------+|
|  |              SHOP PERFORMANCE TREND                            ||
|  |   Shop A ────  Shop B ----  Shop C ····                        ||
|  |      ___                                                       ||
|  |     /   \___    ___                                            ||
|  |    /        \__/   \___                                        ||
|  +----------------------------------------------------------------+|
|                                                                    |
+------------------------------------------------------------------+
```

### Components

#### 1. Shop Comparison Table

| Column | Field | Format |
|--------|-------|--------|
| Shop | `shop_name` | Text |
| Platform | `platform` | Text with icon |
| Revenue | `SUM(revenue)` | Currency |
| Orders | `SUM(orders)` | Number |
| ROAS | `SUM(revenue)/SUM(ad_spend)` | Decimal + "x" |
| Growth | `growth_rate` | Percent with arrow |

**Table Settings:**
- Sortable: Yes (default by Revenue desc)
- Pagination: 10 rows per page
- Heatmap: Apply to ROAS column

#### 2. Revenue by Platform (Bar Chart)

| Property | Value |
|----------|-------|
| Chart Type | Horizontal bar |
| Dimension | `platform` |
| Metric | `SUM(revenue)` |
| Colors | Platform-specific |
| Sort | By metric descending |

#### 3. Growth Metrics Scorecards

| Metric | Calculation |
|--------|-------------|
| WoW Growth | `(This Week - Last Week) / Last Week * 100` |
| MoM Growth | `(This Month - Last Month) / Last Month * 100` |
| YoY Growth | `(This Year - Last Year) / Last Year * 100` |

#### 4. Shop Performance Trend

| Property | Value |
|----------|-------|
| Chart Type | Time series (Multi-line) |
| Dimension | `date` |
| Breakdown | `shop_name` |
| Metric | `SUM(revenue)` |
| Max Series | 5 shops |

---

## Page 3: Ads Performance Overview (D-007)

### Purpose
Unified view of advertising performance across all platforms.

### Data Source
- Primary: `mart_daily_performance` (filtered to ads platforms)
- Secondary: `mart_channel_comparison`

### Layout

```
+------------------------------------------------------------------+
| [Logo]  ADS PERFORMANCE             [Date Filter] [Platform Filter]|
+------------------------------------------------------------------+
|                                                                    |
|  +------------+  +------------+  +------------+  +------------+    |
|  | TOTAL SPEND|  | IMPRESSIONS|  | CLICKS     |  | AVG ROAS   |    |
|  | ฿500K      |  | 2.5M       |  | 125K       |  | 4.2x       |    |
|  +------------+  +------------+  +------------+  +------------+    |
|                                                                    |
|  +----------------------------------+  +------------------------+  |
|  |      SPEND BY PLATFORM          |  |    ROAS COMPARISON     |  |
|  |                                  |  |                        |  |
|  |   Facebook  ████████  40%       |  |   Google    ████ 5.2x  |  |
|  |   Google    ██████    30%       |  |   Facebook  ███  4.1x  |  |
|  |   TikTok    ████      20%       |  |   TikTok    ██   3.8x  |  |
|  |   LINE      ██        10%       |  |   LINE      ██   3.5x  |  |
|  +----------------------------------+  +------------------------+  |
|                                                                    |
|  +----------------------------------------------------------------+|
|  |                    CAMPAIGN PERFORMANCE TABLE                  ||
|  |----------------------------------------------------------------||
|  | Campaign         | Platform | Spend   | ROAS | CTR   | Flag   ||
|  |------------------|----------|---------|------|-------|--------||
|  | Summer Sale      | Facebook | ฿150K   | 5.2x | 2.1%  | 🟢 Good||
|  | Brand Awareness  | Google   | ฿120K   | 4.1x | 1.8%  | 🟢 Good||
|  | Flash Sale       | TikTok   | ฿80K    | 1.5x | 3.2%  | 🔴 Poor||
|  +----------------------------------------------------------------+|
|                                                                    |
+------------------------------------------------------------------+
```

### Components

#### 1. KPI Scorecards (4 cards)

| Scorecard | Metric | Format |
|-----------|--------|--------|
| Total Spend | `SUM(ad_spend)` | Currency |
| Impressions | `SUM(impressions)` | Number (K/M) |
| Clicks | `SUM(clicks)` | Number (K) |
| Avg ROAS | `SUM(revenue)/SUM(ad_spend)` | Decimal + "x" |

#### 2. Spend by Platform (Donut Chart)

| Property | Value |
|----------|-------|
| Chart Type | Donut |
| Dimension | `platform` |
| Metric | `SUM(ad_spend)` |
| Filter | Ads platforms only |
| Show | Percentage labels |

#### 3. ROAS Comparison (Bar Chart)

| Property | Value |
|----------|-------|
| Chart Type | Horizontal bar |
| Dimension | `platform` |
| Metric | `SUM(revenue)/SUM(ad_spend)` |
| Reference Line | ROAS = 2 (minimum target) |
| Conditional Color | Poor/OK/Good |

#### 4. Campaign Performance Table

| Column | Field | Format |
|--------|-------|--------|
| Campaign | `campaign_name` | Text |
| Platform | `platform` | Text with icon |
| Spend | `SUM(ad_spend)` | Currency |
| ROAS | `SUM(revenue)/SUM(ad_spend)` | Decimal + "x" |
| CTR | `SUM(clicks)/SUM(impressions)*100` | Percent |
| Flag | Performance flag | Emoji + text |

**Performance Flag Calculated Field:**
```
CASE
  WHEN SUM(revenue)/SUM(ad_spend) >= 4 THEN "🟢 Good"
  WHEN SUM(revenue)/SUM(ad_spend) >= 2 THEN "🟡 OK"
  ELSE "🔴 Poor"
END
```

---

## Page 4: Product Analytics (D-008)

### Purpose
Analyze product performance across platforms.

### Data Source
- Primary: `mart_product_performance`

### Layout

```
+------------------------------------------------------------------+
| [Logo]  PRODUCT ANALYTICS           [Date Filter] [Platform Filter]|
+------------------------------------------------------------------+
|                                                                    |
|  +------------+  +------------+  +------------+  +------------+    |
|  | PRODUCTS   |  | TOTAL SALES|  | AVG PRICE  |  | TOP SKU    |    |
|  | 1,234      |  | ฿2.5M      |  | ฿450       |  | SKU-001    |    |
|  +------------+  +------------+  +------------+  +------------+    |
|                                                                    |
|  +----------------------------------------------------------------+|
|  |                     TOP PRODUCTS TABLE                         ||
|  |----------------------------------------------------------------||
|  | Rank | Product Name        | SKU     | Sales   | Units | Rev % ||
|  |------|---------------------|---------|---------|-------|-------||
|  | 1    | Product A           | SKU-001 | ฿500K   | 1,200 | 20%   ||
|  | 2    | Product B           | SKU-002 | ฿420K   | 980   | 17%   ||
|  | 3    | Product C           | SKU-003 | ฿350K   | 850   | 14%   ||
|  +----------------------------------------------------------------+|
|                                                                    |
|  +----------------------------------+  +------------------------+  |
|  |     CATEGORY BREAKDOWN          |  |  PLATFORM COMPARISON   |  |
|  |                                  |  |                        |  |
|  |   Electronics  ████████  35%    |  |  Product A:            |  |
|  |   Fashion      ██████    25%    |  |    Shopee: ฿200K       |  |
|  |   Home         █████     20%    |  |    Lazada: ฿180K       |  |
|  |   Beauty       ████      15%    |  |    TikTok: ฿120K       |  |
|  |   Other        ██         5%    |  |                        |  |
|  +----------------------------------+  +------------------------+  |
|                                                                    |
+------------------------------------------------------------------+
```

### Components

#### 1. KPI Scorecards

| Scorecard | Metric | Format |
|-----------|--------|--------|
| Products | `COUNT(DISTINCT product_id)` | Number |
| Total Sales | `SUM(revenue)` | Currency |
| Avg Price | `AVG(price)` | Currency |
| Top SKU | `MAX(sku) BY revenue` | Text |

#### 2. Top Products Table

| Column | Field | Format |
|--------|-------|--------|
| Rank | Row number | Number |
| Product Name | `product_name` | Text |
| SKU | `sku` | Text |
| Sales | `SUM(revenue)` | Currency |
| Units | `SUM(quantity)` | Number |
| Rev % | `% of total revenue` | Percent |

**Table Settings:**
- Rows: 10
- Sort: By Sales descending
- Heatmap: Apply to Sales column

#### 3. Category Breakdown (Treemap or Bar)

| Property | Value |
|----------|-------|
| Chart Type | Treemap or Horizontal bar |
| Dimension | `category` |
| Metric | `SUM(revenue)` |
| Show | Percentage labels |

#### 4. Platform Comparison (Stacked Bar)

| Property | Value |
|----------|-------|
| Chart Type | Stacked bar |
| Dimension | `product_name` (top 5) |
| Breakdown | `platform` |
| Metric | `SUM(revenue)` |
| Colors | Platform-specific |

---

## Page 5: Website Analytics - GA4 Basic (D-009)

### Purpose
Basic website analytics from Google Analytics 4.

### Data Source
- Primary: GA4 data in BigQuery (or direct GA4 connector)
- Tables: `staging_ga4_*` or GA4 native connector

### Layout

```
+------------------------------------------------------------------+
| [Logo]  WEBSITE ANALYTICS (GA4)     [Date Filter]                  |
+------------------------------------------------------------------+
|                                                                    |
|  +------------+  +------------+  +------------+  +------------+    |
|  | SESSIONS   |  | USERS      |  | PAGE VIEWS |  | BOUNCE RATE|    |
|  | 125K       |  | 85K        |  | 450K       |  | 42%        |    |
|  | ▲ +15%     |  | ▲ +12%     |  | ▲ +18%     |  | ▼ -3%      |    |
|  +------------+  +------------+  +------------+  +------------+    |
|                                                                    |
|  +----------------------------------------------------------------+|
|  |              SESSIONS & USERS TREND                            ||
|  |                                                                ||
|  |   Sessions ────  Users ----                                    ||
|  |      ___                                                       ||
|  |     /   \___    ___                                            ||
|  |    /        \__/   \___                                        ||
|  +----------------------------------------------------------------+|
|                                                                    |
|  +----------------------------------+  +------------------------+  |
|  |     TRAFFIC SOURCES             |  |    TOP PAGES           |  |
|  |                                  |  |                        |  |
|  |   Organic    ████████  40%      |  |  1. /home      25K     |  |
|  |   Direct     ██████    30%      |  |  2. /products  18K     |  |
|  |   Social     ████      15%      |  |  3. /cart      12K     |  |
|  |   Referral   ███       10%      |  |  4. /checkout  8K      |  |
|  |   Paid       ██         5%      |  |  5. /account   5K      |  |
|  +----------------------------------+  +------------------------+  |
|                                                                    |
|  +----------------------------------------------------------------+|
|  |              CONVERSION METRICS                                ||
|  |----------------------------------------------------------------||
|  | Goal              | Completions | Rate   | Value              ||
|  |-------------------|-------------|--------|--------------------||
|  | Purchase          | 2,500       | 2.0%   | ฿1.2M              ||
|  | Add to Cart       | 15,000      | 12.0%  | -                  ||
|  | Sign Up           | 3,200       | 2.6%   | -                  ||
|  +----------------------------------------------------------------+|
|                                                                    |
+------------------------------------------------------------------+
```

### Components

#### 1. KPI Scorecards (4 cards)

| Scorecard | Metric | Format |
|-----------|--------|--------|
| Sessions | `SUM(sessions)` | Number (K) |
| Users | `SUM(users)` | Number (K) |
| Page Views | `SUM(page_views)` | Number (K) |
| Bounce Rate | `AVG(bounce_rate)` | Percent |

#### 2. Sessions & Users Trend

| Property | Value |
|----------|-------|
| Chart Type | Time series (Dual line) |
| Dimension | `date` |
| Metrics | `sessions`, `users` |
| Style | Two lines, different colors |

#### 3. Traffic Sources (Pie/Donut)

| Property | Value |
|----------|-------|
| Chart Type | Donut |
| Dimension | `source_medium` or `channel_grouping` |
| Metric | `SUM(sessions)` |
| Max Slices | 5 + Other |

**Common Traffic Sources:**
- Organic Search
- Direct
- Social
- Referral
- Paid Search
- Email

#### 4. Top Pages Table

| Column | Field | Format |
|--------|-------|--------|
| Rank | Row number | Number |
| Page | `page_path` | Text |
| Views | `SUM(page_views)` | Number |
| Avg Time | `AVG(time_on_page)` | Duration |

#### 5. Conversion Metrics Table

| Column | Field | Format |
|--------|-------|--------|
| Goal | `goal_name` or `event_name` | Text |
| Completions | `SUM(conversions)` | Number |
| Rate | `conversions / sessions * 100` | Percent |
| Value | `SUM(conversion_value)` | Currency |

**Key Conversion Events:**
- `purchase` - Completed purchases
- `add_to_cart` - Add to cart clicks
- `begin_checkout` - Checkout initiated
- `sign_up` - New registrations

---

## Implementation Checklist

### Page 1: Executive Overview (D-005)
- [ ] Create page and set layout
- [ ] Add 4 KPI scorecards with comparison
- [ ] Add revenue trend line chart
- [ ] Add alerts summary component
- [ ] Add period comparison table
- [ ] Add platform breakdown pie chart
- [ ] Configure date and platform filters
- [ ] Test filter interactions

### Page 2: Shop Performance (D-006)
- [ ] Create page and set layout
- [ ] Add shop comparison table
- [ ] Add revenue by platform bar chart
- [ ] Add growth metrics scorecards
- [ ] Add shop performance trend chart
- [ ] Configure conditional formatting
- [ ] Test sorting and filtering

### Page 3: Ads Performance Overview (D-007)
- [ ] Create page and set layout
- [ ] Add 4 KPI scorecards
- [ ] Add spend by platform donut
- [ ] Add ROAS comparison bar chart
- [ ] Add campaign performance table
- [ ] Create performance flag calculated field
- [ ] Add reference line for ROAS target

### Page 4: Product Analytics (D-008)
- [ ] Create page and set layout
- [ ] Add 4 KPI scorecards
- [ ] Add top products table
- [ ] Add category breakdown chart
- [ ] Add platform comparison stacked bar
- [ ] Configure table pagination
- [ ] Test product filtering

### Page 5: Website Analytics (D-009)
- [ ] Connect GA4 data source
- [ ] Create page and set layout
- [ ] Add 4 KPI scorecards
- [ ] Add sessions/users trend chart
- [ ] Add traffic sources donut
- [ ] Add top pages table
- [ ] Add conversion metrics table
- [ ] Test date filtering

---

## Best Practices

### Performance
- Limit data to necessary date range
- Use aggregated mart tables instead of raw data
- Avoid complex calculated fields in large tables
- Enable caching for frequently accessed reports

### User Experience
- Keep consistent layout across pages
- Use clear, descriptive labels
- Add tooltips for complex metrics
- Ensure mobile responsiveness

### Maintenance
- Document all calculated fields
- Use naming conventions for components
- Test filters across all pages
- Schedule regular data refresh verification
