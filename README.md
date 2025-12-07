# Central Marketing Dashboard

Centralized Marketing Dashboard - ETL pipeline for e-commerce and advertising platforms.

## Overview

This project consolidates data from multiple e-commerce platforms (Shopee, Lazada, TikTok Shop) and advertising platforms (Facebook Ads, Google Ads, TikTok Ads, LINE Ads, GA4) into a unified BigQuery data warehouse with Looker Studio dashboards.

## Architecture

- **ETL Layer**: Hybrid approach using Airbyte (pre-built connectors) + Python (custom extractors)
- **Data Warehouse**: Google BigQuery (raw → staging → mart layers)
- **Orchestration**: Cloud Scheduler + Cloud Functions
- **Dashboard**: Google Looker Studio

## Quick Start

```bash
# Install dependencies
uv sync

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
```

## Project Structure

```
├── src/                    # Source code
│   ├── extractors/         # API clients (Python)
│   ├── transformers/       # Data transformation
│   ├── loaders/            # BigQuery loaders
│   ├── models/             # Alert models
│   ├── pipelines/          # ETL pipelines
│   └── utils/              # Utilities
├── sql/                    # BigQuery SQL scripts
├── config/                 # Configuration files
├── airbyte/                # Airbyte configurations
├── cloud_functions/        # GCP Cloud Functions
├── tests/                  # Test files
└── scripts/                # Utility scripts
```

## Documentation

- [Product Specification](.docs/01-spec.md)
- [Technical Plan](.docs/02-plan.md)
- [Development Tasks](.docs/03-tasks.md)
