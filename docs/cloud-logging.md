# Cloud Logging Guide

## Overview

Cloud Functions automatically send logs to Google Cloud Logging. This document describes how to view and monitor logs for the ETL pipelines.

## Viewing Logs in GCP Console

### 1. Access Cloud Logging

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Navigate to **Logging** > **Logs Explorer**

Or use direct URL:
```
https://console.cloud.google.com/logs/query?project=YOUR_PROJECT_ID
```

### 2. Filter by Cloud Function

To view logs for a specific function, use these queries:

**E-commerce ETL:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-ecommerce"
```

**Ads ETL:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-ads"
```

**Mart ETL:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-mart"
```

**Alerts ETL:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-alerts"
```

### 3. Filter by Severity

Add severity filter to narrow down logs:

```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-ecommerce"
severity>=ERROR
```

Severity levels:
- `DEBUG` - Detailed information for debugging
- `INFO` - General operational information
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

### 4. Filter by Time Range

Use the time picker in Logs Explorer or add timestamp filter:

```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-ecommerce"
timestamp>="2024-01-01T00:00:00Z"
timestamp<="2024-01-02T00:00:00Z"
```

## Log Structure

Our Cloud Functions use structured logging with the following fields:

```json
{
  "message": "E-commerce ETL completed successfully",
  "severity": "INFO",
  "component": "cloud_function.etl_ecommerce",
  "start_date": "2024-01-01T00:00:00+00:00",
  "end_date": "2024-01-07T00:00:00+00:00",
  "platforms": ["shopee", "lazada", "tiktok_shop"],
  "records_extracted": 1000,
  "records_loaded": 950,
  "duration_seconds": 120.5
}
```

### Key Log Fields

| Field | Description |
|-------|-------------|
| `message` | Log message |
| `severity` | Log level (INFO, ERROR, etc.) |
| `component` | Logger name/source |
| `start_date` | ETL start date |
| `end_date` | ETL end date |
| `platforms` | Platforms processed |
| `records_extracted` | Number of records extracted |
| `records_loaded` | Number of records loaded |
| `duration_seconds` | Execution time |
| `error` | Error message (if failed) |

## Common Log Queries

### View All ETL Errors (Last 24 hours)

```
resource.type="cloud_run_revision"
(resource.labels.service_name="etl-ecommerce" OR
 resource.labels.service_name="etl-ads" OR
 resource.labels.service_name="etl-mart" OR
 resource.labels.service_name="etl-alerts")
severity>=ERROR
```

### View Pipeline Execution Summary

```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-ecommerce"
jsonPayload.message=~"completed"
```

### View Failed Executions

```
resource.type="cloud_run_revision"
(resource.labels.service_name="etl-ecommerce" OR
 resource.labels.service_name="etl-ads")
jsonPayload.success=false
```

### View Scheduler Triggered Executions

```
resource.type="cloud_run_revision"
resource.labels.service_name="etl-ecommerce"
jsonPayload.message="E-commerce ETL function triggered"
```

## Using gcloud CLI

### View Recent Logs

```bash
# E-commerce function logs
gcloud functions logs read etl-ecommerce \
  --gen2 \
  --region=asia-southeast1 \
  --limit=50

# Ads function logs
gcloud functions logs read etl-ads \
  --gen2 \
  --region=asia-southeast1 \
  --limit=50

# Mart function logs
gcloud functions logs read etl-mart \
  --gen2 \
  --region=asia-southeast1 \
  --limit=50

# Alerts function logs
gcloud functions logs read etl-alerts \
  --gen2 \
  --region=asia-southeast1 \
  --limit=50
```

### Stream Logs in Real-time

```bash
gcloud functions logs read etl-ecommerce \
  --gen2 \
  --region=asia-southeast1 \
  --limit=50 \
  --start-time=$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ)
```

### View Error Logs Only

```bash
gcloud logging read \
  'resource.type="cloud_run_revision" AND resource.labels.service_name="etl-ecommerce" AND severity>=ERROR' \
  --project=YOUR_PROJECT_ID \
  --limit=20 \
  --format="table(timestamp, severity, jsonPayload.message)"
```

## Manual Check Process

### Daily Health Check (Recommended)

1. **Check Scheduler Execution**
   - Go to Cloud Scheduler in GCP Console
   - Verify all jobs show "Success" for last run
   - Note any failed executions

2. **Review Error Logs**
   - Use "View All ETL Errors" query above
   - Investigate any ERROR or CRITICAL logs
   - Check for patterns in failures

3. **Verify Data Freshness**
   - Check BigQuery tables for recent data
   - Verify `_loaded_at` timestamps are current

### Weekly Review

1. **Execution Statistics**
   - Count successful vs failed executions
   - Calculate average execution time
   - Identify slow-running pipelines

2. **Error Analysis**
   - Group errors by type
   - Identify recurring issues
   - Plan fixes for common errors

## Troubleshooting

### Common Issues

#### 1. Function Timeout
- **Symptom**: Logs show execution stopped at 540s
- **Solution**: Reduce batch size or increase timeout in deploy script

#### 2. Memory Exceeded
- **Symptom**: Logs show "Memory limit exceeded"
- **Solution**: Increase memory in deploy script (e.g., `--memory=1024MB`)

#### 3. API Rate Limits
- **Symptom**: Logs show rate limit errors from external APIs
- **Solution**: Implement backoff/retry or reduce request frequency

#### 4. Authentication Errors
- **Symptom**: Logs show "Permission denied" or auth errors
- **Solution**: Check service account permissions in GCP IAM

### Debug Mode

To enable debug logging for a specific execution:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"debug": true, "days_back": 1}' \
  https://REGION-PROJECT_ID.cloudfunctions.net/etl-ecommerce
```

## Log Retention

Default Cloud Logging retention:
- **Admin Activity logs**: 400 days (free)
- **Data Access logs**: 30 days (configurable)
- **System Event logs**: 400 days (free)
- **User-written logs**: 30 days (configurable)

To configure longer retention:
1. Go to **Logging** > **Logs Router**
2. Create a sink to Cloud Storage or BigQuery for long-term storage

## Alerts (Phase 2)

> Note: Automated log-based alerts will be configured in Phase 2.
> Current approach: Manual daily check of error logs.

Future alerting will include:
- Email/Slack notifications on ERROR logs
- Alert on function failure
- Alert on unusual execution times
