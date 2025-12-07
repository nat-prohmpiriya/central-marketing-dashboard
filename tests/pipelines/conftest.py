"""Pytest configuration for pipeline tests."""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.gcp_project_id = "test-project"
    settings.bigquery_dataset_raw = "raw"
    settings.bigquery_dataset_staging = "staging"
    settings.bigquery_dataset_mart = "mart"
    return settings


@pytest.fixture
def sample_date_range():
    """Create sample date range."""
    return (
        datetime(2024, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 31, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_shopee_orders():
    """Create sample Shopee order data."""
    return [
        {
            "platform": "shopee",
            "data": {
                "order_sn": "SHP001",
                "order_status": "COMPLETED",
                "create_time": 1704067200,
                "total_amount": 1000.0,
                "buyer_username": "buyer1",
                "item_list": [
                    {
                        "item_id": 12345,
                        "item_name": "Product A",
                        "model_sku": "SKU-A",
                        "model_quantity_purchased": 2,
                        "model_discounted_price": 500.0,
                    }
                ],
            },
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
        {
            "platform": "shopee",
            "data": {
                "order_sn": "SHP002",
                "order_status": "SHIPPED",
                "create_time": 1704153600,
                "total_amount": 2000.0,
                "buyer_username": "buyer2",
                "item_list": [
                    {
                        "item_id": 12346,
                        "item_name": "Product B",
                        "model_sku": "SKU-B",
                        "model_quantity_purchased": 1,
                        "model_discounted_price": 2000.0,
                    }
                ],
            },
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_lazada_orders():
    """Create sample Lazada order data."""
    return [
        {
            "platform": "lazada",
            "data": {
                "order_id": "LAZ001",
                "statuses": ["delivered"],
                "created_at": "2024-01-01T00:00:00+07:00",
                "price": 1500.0,
                "customer_first_name": "John",
                "order_items": [
                    {
                        "sku": "LAZ-SKU-A",
                        "name": "Lazada Product A",
                        "paid_price": 1500.0,
                    }
                ],
            },
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_facebook_ads():
    """Create sample Facebook Ads data."""
    return [
        {
            "platform": "facebook_ads",
            "data_type": "ads",
            "data": {
                "campaign_id": "FB001",
                "campaign_name": "Campaign 1",
                "adset_id": "ADSET001",
                "ad_id": "AD001",
                "date_start": "2024-01-01",
                "spend": 100.0,
                "impressions": 10000,
                "clicks": 500,
                "conversions": 50,
            },
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_ga4_data():
    """Create sample GA4 data."""
    return [
        {
            "platform": "ga4",
            "data_type": "ga4",
            "data": {
                "dimensions": {
                    "date": "20240101",
                    "sessionSource": "google",
                    "sessionMedium": "cpc",
                },
                "metrics": {
                    "sessions": 1000,
                    "totalUsers": 800,
                    "bounceRate": 0.45,
                },
            },
            "property_id": "123456",
            "type": "sessions",
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
    ]


@pytest.fixture
def sample_products():
    """Create sample product data."""
    return [
        {
            "platform": "shopee",
            "data": {
                "item_id": 12345,
                "item_name": "Shopee Product",
                "model_sku": "SHP-SKU-001",
                "price": 500.0,
                "stock": 100,
                "category_id": 1001,
            },
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
        {
            "platform": "lazada",
            "data": {
                "sku_id": "67890",
                "name": "Lazada Product",
                "seller_sku": "LAZ-SKU-001",
                "price": 600.0,
                "quantity": 50,
            },
            "extracted_at": "2024-01-15T00:00:00+00:00",
        },
    ]


@pytest.fixture
def mock_extractors():
    """Create mock extractors that return sample data."""
    def create_mock_extractor(data):
        extractor = MagicMock()
        extractor.extract.return_value = iter(data)
        extractor.extract_products.return_value = iter(data)
        extractor.__enter__ = MagicMock(return_value=extractor)
        extractor.__exit__ = MagicMock(return_value=False)
        return extractor

    return create_mock_extractor


@pytest.fixture
def mock_loaders():
    """Create mock loaders."""
    raw_loader = MagicMock()
    raw_loader.load_raw_orders.return_value = 10
    raw_loader.load_raw_ads.return_value = 5
    raw_loader.load_raw_ga4.return_value = 5
    raw_loader.load_raw_products.return_value = 5
    raw_loader.set_batch_id = MagicMock()

    staging_loader = MagicMock()
    staging_loader.load_orders.return_value = 10
    staging_loader.load_ads.return_value = 5
    staging_loader.load_ga4_sessions.return_value = 5
    staging_loader.load_ga4_traffic.return_value = 5
    staging_loader.load_products.return_value = 5
    staging_loader.load_sku_mappings.return_value = 3

    return raw_loader, staging_loader
