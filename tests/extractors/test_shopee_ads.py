"""Tests for Shopee Ads extractor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.shopee_ads import ShopeeAdsExtractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.shopee.get_settings") as mock_shopee, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.shopee_partner_id = "12345"
        settings.shopee_partner_key = "test_partner_key"
        settings.shopee_shop_id = "67890"
        settings.shopee_access_token = "test_access_token"
        settings.shopee_refresh_token = "test_refresh_token"
        mock_shopee.return_value = settings
        mock_base.return_value = settings
        mock_rate.return_value = {
            "requests_per_minute": 60,
            "retry_after_seconds": 60,
            "max_retries": 3,
        }
        yield settings


@pytest.fixture
def extractor(mock_settings):
    """Create extractor instance."""
    return ShopeeAdsExtractor()


class TestShopeeAdsExtractorInit:
    """Tests for extractor initialization."""

    def test_init_inherits_from_shopee(self, extractor):
        """Test initialization inherits from ShopeeExtractor."""
        assert extractor.platform_name == "shopee_ads"
        assert extractor.partner_id == 12345
        assert extractor.shop_id == 67890

    def test_has_ads_endpoints(self, extractor):
        """Test has ads-specific endpoints."""
        assert extractor.ADS_CAMPAIGN_LIST_PATH
        assert extractor.ADS_DAILY_REPORT_PATH
        assert extractor.ADS_PRODUCT_ADS_PATH


class TestShopeeAdsExtractCampaigns:
    """Tests for campaign extraction."""

    def test_extract_campaigns_success(self, extractor):
        """Test successful campaign extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "campaign_list": [
                    {"campaign_id": 123, "campaign_name": "Campaign 1"},
                    {"campaign_id": 124, "campaign_name": "Campaign 2"},
                ],
                "more": False,
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 2
        assert results[0]["type"] == "campaign"
        assert results[0]["platform"] == "shopee_ads"
        assert results[0]["data"]["campaign_id"] == 123

    def test_extract_campaigns_with_pagination(self, extractor):
        """Test campaign extraction with pagination."""
        mock_response_page1 = MagicMock()
        mock_response_page1.json.return_value = {
            "response": {
                "campaign_list": [{"campaign_id": 123}],
                "more": True,
            },
        }

        mock_response_page2 = MagicMock()
        mock_response_page2.json.return_value = {
            "response": {
                "campaign_list": [{"campaign_id": 124}],
                "more": False,
            },
        }

        mock_client = MagicMock()
        mock_client.get.side_effect = [mock_response_page1, mock_response_page2]
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 2

    def test_extract_campaigns_with_ad_type_filter(self, extractor):
        """Test campaign extraction with ad type filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "campaign_list": [{"campaign_id": 123}],
                "more": False,
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        list(extractor.extract_campaigns(ad_type="product_search"))

        call_args = mock_client.get.call_args
        assert "ad_type" in str(call_args)

    def test_extract_campaigns_api_error(self, extractor):
        """Test campaign extraction with API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "invalid_access_token",
            "message": "Access token is invalid",
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 0


class TestShopeeAdsExtractDailyReports:
    """Tests for daily report extraction."""

    def test_extract_daily_reports_success(self, extractor):
        """Test successful daily report extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "report_list": [
                    {
                        "date": "2024-01-01",
                        "impressions": 1000,
                        "clicks": 50,
                        "cost": 100.00,
                    },
                    {
                        "date": "2024-01-02",
                        "impressions": 1200,
                        "clicks": 60,
                        "cost": 120.00,
                    },
                ],
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_daily_reports(start_date, end_date))

        assert len(results) == 2
        assert results[0]["type"] == "daily_report"
        assert results[0]["data"]["impressions"] == 1000

    def test_extract_daily_reports_with_campaign_filter(self, extractor):
        """Test daily reports extraction with campaign filter."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "report_list": [{"date": "2024-01-01"}],
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract_daily_reports(start_date, end_date, campaign_id=123))

        call_args = mock_client.get.call_args
        assert "campaign_id" in str(call_args)


class TestShopeeAdsExtractProductAds:
    """Tests for product ads extraction."""

    def test_extract_product_ads_success(self, extractor):
        """Test successful product ads extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "ads_list": [
                    {"ad_id": 456, "item_id": 789, "status": "active"},
                ],
                "more": False,
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_product_ads())

        assert len(results) == 1
        assert results[0]["type"] == "product_ad"
        assert results[0]["data"]["ad_id"] == 456


class TestShopeeAdsExtractShopAds:
    """Tests for shop ads extraction."""

    def test_extract_shop_ads_success(self, extractor):
        """Test successful shop ads extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "shop_ads": [
                    {"ad_id": 999, "status": "active"},
                ],
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_shop_ads())

        assert len(results) == 1
        assert results[0]["type"] == "shop_ad"


class TestShopeeAdsGetCampaignDetail:
    """Tests for getting campaign detail."""

    def test_get_campaign_detail_success(self, extractor):
        """Test successful campaign detail retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "campaign_id": 123,
                "campaign_name": "Test Campaign",
                "status": "active",
                "budget": 1000.00,
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        result = extractor.get_campaign_detail(campaign_id=123)

        assert result is not None
        assert result["campaign_id"] == 123

    def test_get_campaign_detail_not_found(self, extractor):
        """Test campaign detail not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": "campaign_not_found",
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        result = extractor.get_campaign_detail(campaign_id=999)

        assert result is None


class TestShopeeAdsExtract:
    """Tests for main extract method."""

    def test_extract_all_data_types(self, extractor):
        """Test extract with default data_type (all)."""
        mock_response_campaigns = MagicMock()
        mock_response_campaigns.json.return_value = {
            "response": {
                "campaign_list": [{"campaign_id": 123}],
                "more": False,
            },
        }

        mock_response_reports = MagicMock()
        mock_response_reports.json.return_value = {
            "response": {
                "report_list": [{"date": "2024-01-01"}],
            },
        }

        mock_client = MagicMock()
        mock_client.get.side_effect = [mock_response_campaigns, mock_response_reports]
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract(start_date, end_date))

        # Should have campaigns + reports
        assert len(results) == 2

    def test_extract_campaigns_only(self, extractor):
        """Test extract with campaigns data_type."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "campaign_list": [{"campaign_id": 123}],
                "more": False,
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract(start_date, end_date, data_type="campaigns"))

        assert len(results) == 1
        assert results[0]["type"] == "campaign"

    def test_extract_reports_only(self, extractor):
        """Test extract with reports data_type."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": {
                "report_list": [{"date": "2024-01-01"}],
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract(start_date, end_date, data_type="reports"))

        assert len(results) == 1
        assert results[0]["type"] == "daily_report"
