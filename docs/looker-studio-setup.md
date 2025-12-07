# Looker Studio Setup Guide

## Overview

This guide provides step-by-step instructions for setting up Looker Studio dashboards connected to the Central Marketing Dashboard BigQuery data.

## Prerequisites

- Google Cloud Project with BigQuery enabled
- Access to Looker Studio (https://lookerstudio.google.com)
- BigQuery tables populated with data:
  - `mart.mart_daily_performance`
  - `mart.mart_shop_performance`
  - `mart.mart_product_performance`
  - `mart.mart_channel_comparison`
  - `mart.mart_alerts_summary`

## Task D-001: Connect BigQuery Data Sources

### Step 1: Create New Report

1. Go to [Looker Studio](https://lookerstudio.google.com)
2. Click **Create** > **Report**
3. Select **BigQuery** as the data source

### Step 2: Connect to BigQuery

1. Select your **Google Cloud Project**
2. Choose **Dataset**: `mart`
3. Select the first table: `mart_daily_performance`
4. Click **Add**

### Step 3: Add Additional Data Sources

Repeat for each mart table:

| Table Name | Purpose |
|------------|---------|
| `mart_daily_performance` | Daily metrics across all platforms |
| `mart_shop_performance` | Shop-level aggregated metrics |
| `mart_product_performance` | Product-level performance |
| `mart_channel_comparison` | Cross-channel comparison |
| `mart_alerts_summary` | Active marketing alerts |

To add more data sources:
1. Click **Resource** > **Manage added data sources**
2. Click **Add a data source**
3. Select **BigQuery** and choose the next table
4. Repeat for all tables

### Step 4: Verify Connections

Ensure all tables show:
- ✅ Connected status
- ✅ All fields visible
- ✅ Correct data types detected

## Task D-002: Create Calculated Fields

### Access Calculated Fields

1. Click **Resource** > **Manage added data sources**
2. Select the data source (e.g., `mart_daily_performance`)
3. Click **Edit**
4. Click **Add a field** (bottom left)

### Required Calculated Fields

#### 1. ROAS (Return on Ad Spend)

```
Field Name: ROAS
Formula: revenue / ad_spend
Type: Number (Decimal)
```

**With null handling:**
```
CASE
  WHEN ad_spend > 0 THEN revenue / ad_spend
  ELSE 0
END
```

#### 2. CPA (Cost per Acquisition)

```
Field Name: CPA
Formula: ad_spend / conversions
Type: Number (Decimal)
```

**With null handling:**
```
CASE
  WHEN conversions > 0 THEN ad_spend / conversions
  ELSE 0
END
```

#### 3. CTR (Click-through Rate)

```
Field Name: CTR
Formula: (clicks / impressions) * 100
Type: Number (Percent)
```

**With null handling:**
```
CASE
  WHEN impressions > 0 THEN (clicks / impressions) * 100
  ELSE 0
END
```

#### 4. Conversion Rate

```
Field Name: Conversion Rate
Formula: (conversions / clicks) * 100
Type: Number (Percent)
```

**With null handling:**
```
CASE
  WHEN clicks > 0 THEN (conversions / clicks) * 100
  ELSE 0
END
```

#### 5. Average Order Value (AOV)

```
Field Name: AOV
Formula: revenue / orders
Type: Number (Currency)
```

**With null handling:**
```
CASE
  WHEN orders > 0 THEN revenue / orders
  ELSE 0
END
```

### Calculated Fields Summary

| Field | Formula | Format |
|-------|---------|--------|
| ROAS | `revenue / ad_spend` | Decimal (2 places) |
| CPA | `ad_spend / conversions` | Currency |
| CTR | `(clicks / impressions) * 100` | Percent |
| Conversion Rate | `(conversions / clicks) * 100` | Percent |
| AOV | `revenue / orders` | Currency |

## Task D-003: Create Date Filters

### Add Date Range Control

1. Click **Add a control** in the toolbar
2. Select **Date range control**
3. Position it at the top of your dashboard

### Configure Date Range

1. Select the date range control
2. In the **Properties** panel:
   - **Date range dimension**: Select `date` field
   - **Default date range**: Choose appropriate default
     - Recommended: "Last 7 days" or "Last 30 days"

### Available Date Range Options

| Option | Use Case |
|--------|----------|
| Auto | Uses data source default |
| Custom | Specific date range |
| Last 7 days | Weekly review |
| Last 14 days | Bi-weekly analysis |
| Last 28 days | Monthly comparison |
| Last 30 days | Monthly review |
| This month | Current month analysis |
| Last month | Previous month review |
| This quarter | Quarterly analysis |

### Apply to All Charts

To make date filter work across all pages:
1. Select the date range control
2. Right-click > **Make report-level**
3. This ensures filter applies to all pages

## Task D-004: Create Platform Filters

### Add Drop-down List Control

1. Click **Add a control** in the toolbar
2. Select **Drop-down list**
3. Position it next to the date filter

### Configure Platform Filter

1. Select the drop-down control
2. In the **Properties** panel:
   - **Control field**: Select `platform` field
   - **Metric**: Leave empty (for dimension filter)
   - **Order**: Alphabetical or by metric

### Platform Values

Expected platform values in the filter:

| Platform | Description |
|----------|-------------|
| `shopee` | Shopee marketplace |
| `lazada` | Lazada marketplace |
| `tiktok_shop` | TikTok Shop |
| `facebook` | Facebook Ads |
| `google` | Google Ads |
| `tiktok_ads` | TikTok Ads |
| `line` | LINE Ads |

### Add Multi-select Capability

1. Select the drop-down control
2. In **Properties** > **Control field**
3. Enable **Allow multiple selections**
4. This lets users compare multiple platforms

### Make Filter Report-level

1. Select the platform filter
2. Right-click > **Make report-level**
3. Filter will now apply to all pages and charts

## Additional Recommended Filters

### Shop Filter

```
Control Type: Drop-down list
Field: shop_id or shop_name
Multi-select: Yes
```

### Campaign Filter

```
Control Type: Drop-down list
Field: campaign_name
Multi-select: Yes
```

### Alert Severity Filter (for alerts page)

```
Control Type: Drop-down list
Field: severity
Values: critical, warning, info
```

## Dashboard Layout Recommendations

### Filter Bar Layout

```
+------------------------------------------------------------------+
| [Date Range: Last 7 days ▼] [Platform: All ▼] [Shop: All ▼]      |
+------------------------------------------------------------------+
```

### Recommended Page Structure

1. **Overview Page**
   - Key metrics scorecards (Revenue, Orders, ROAS, etc.)
   - Trend charts
   - Platform comparison

2. **E-commerce Performance**
   - Shop performance table
   - Product performance
   - Daily trends

3. **Ads Performance**
   - Ad spend vs revenue
   - Campaign performance
   - Channel comparison

4. **Alerts**
   - Active alerts table
   - Alert trends
   - Severity breakdown

## Verification Checklist

### D-001: Data Sources
- [ ] `mart_daily_performance` connected
- [ ] `mart_shop_performance` connected
- [ ] `mart_product_performance` connected
- [ ] `mart_channel_comparison` connected
- [ ] `mart_alerts_summary` connected
- [ ] All fields properly detected

### D-002: Calculated Fields
- [ ] ROAS field created and working
- [ ] CPA field created and working
- [ ] CTR field created and working
- [ ] Conversion Rate field created (optional)
- [ ] AOV field created (optional)

### D-003: Date Filters
- [ ] Date range control added
- [ ] Default range set appropriately
- [ ] Filter is report-level
- [ ] Filter works across all charts

### D-004: Platform Filters
- [ ] Platform drop-down added
- [ ] All platforms visible in filter
- [ ] Multi-select enabled
- [ ] Filter is report-level
- [ ] Filter works across all charts

## Troubleshooting

### Data Not Showing

1. **Check BigQuery permissions**
   - User needs BigQuery Data Viewer role
   - Check project and dataset access

2. **Verify data exists**
   ```sql
   SELECT COUNT(*) FROM `project.mart.mart_daily_performance`
   ```

3. **Check date range**
   - Ensure selected date range has data
   - Try expanding the date range

### Calculated Fields Not Working

1. **Check field names**
   - Field names are case-sensitive
   - Verify exact field names in data source

2. **Handle null values**
   - Use CASE statements for division
   - Avoid division by zero

### Filters Not Applying

1. **Check filter scope**
   - Ensure filter is report-level (not page-level)
   - Check filter field matches chart dimensions

2. **Verify data source**
   - All charts must use the same data source
   - Or use blended data with matching keys

## Resources

- [Looker Studio Help Center](https://support.google.com/looker-studio)
- [BigQuery Connector Documentation](https://support.google.com/looker-studio/answer/6370296)
- [Calculated Fields Reference](https://support.google.com/looker-studio/table/6379764)
- [Filter Controls Guide](https://support.google.com/looker-studio/answer/6291066)
