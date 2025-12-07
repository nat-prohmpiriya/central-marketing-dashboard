"""Tests for Lazada Ads extractor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.lazada_ads import LazadaAdsExtractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.lazada.get_settings") as mock_lazada, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.lazada_app_key = "test_app_key"
        settings.lazada_app_secret = "test_app_secret"
        settings.lazada_access_token = "test_access_token"
        settings.lazada_refresh_token = "test_refresh_token"
        mock_lazada.return_value = settings
        mock_base.return_value = settings
        mock_rate.return_value = {
            "requests_per_minute": 50,
            "retry_after_seconds": 60,
            "max_retries": 3,
        }
        yield settings


@pytest.fixture
def extractor(mock_settings):
    """Create extractor instance."""
    return LazadaAdsExtractor()


class TestLazadaAdsExtractorInit:
    """Tests for extractor initialization."""

    def test_init_inherits_from_lazada(self, extractor):
        """Test initialization inherits from LazadaExtractor."""
        assert extractor.platform_name == "lazada_ads"
        assert extractor.app_key == "test_app_key"
        assert extractor.app_secret == "test_app_secret"

    def test_has_ads_endpoints(self, extractor):
        """Test has ads-specific endpoints."""
        assert extractor.ADS_CAMPAIGN_LIST_PATH
        assert extractor.ADS_REPORT_PATH
        assert extractor.ADS_SPONSORED_PRODUCTS_PATH


class TestLazadaAdsExtractCampaigns:
    """Tests for campaign extraction."""

    def test_extract_campaigns_success(self, extractor):
        """Test successful campaign extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "0",
            "data": {
                "campaigns": [
                    {"campaign_id": "123", "name": "Campaign 1", "status": "active"},
                    {"campaign_id": "124", "name": "Campaign 2", "status": "paused"},
                ],
                "total": 2,
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "campaigns": [
                    {"campaign_id": "123", "name": "Campaign 1"},
                    {"campaign_id": "124", "name": "Campaign 2"},
                ],
                "total": 2,
            }

            results = list(extractor.extract_campaigns())

            assert len(results) == 2
            assert results[0]["type"] == "campaign"
            assert results[0]["platform"] == "lazada_ads"
            assert results[0]["data"]["campaign_id"] == "123"

    def test_extract_campaigns_with_status_filter(self, extractor):
        """Test campaign extraction with status filter."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "campaigns": [{"campaign_id": "123"}],
                "total": 1,
            }

            list(extractor.extract_campaigns(status="active"))

            call_args = mock_request.call_args
            assert "status" in str(call_args)

    def test_extract_campaigns_with_pagination(self, extractor):
        """Test campaign extraction with pagination."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.side_effect = [
                {
                    "campaigns": [{"campaign_id": "123"}],
                    "total": 200,
                },
                {
                    "campaigns": [{"campaign_id": "124"}],
                    "total": 200,
                },
                {
                    "campaigns": [],
                    "total": 200,
                },
            ]

            results = list(extractor.extract_campaigns())

            assert len(results) == 2


class TestLazadaAdsExtractReports:
    """Tests for report extraction."""

    def test_extract_reports_success(self, extractor):
        """Test successful report extraction."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "reports": [
                    {
                        "date": "2024-01-01",
                        "impressions": 1000,
                        "clicks": 50,
                        "spend": 100.00,
                    },
                    {
                        "date": "2024-01-02",
                        "impressions": 1200,
                        "clicks": 60,
                        "spend": 120.00,
                    },
                ],
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract_reports(start_date, end_date))

            assert len(results) == 2
            assert results[0]["type"] == "report"
            assert results[0]["data"]["impressions"] == 1000

    def test_extract_reports_with_campaign_filter(self, extractor):
        """Test report extraction with campaign filter."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "reports": [{"date": "2024-01-01"}],
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            list(extractor.extract_reports(start_date, end_date, campaign_id="123"))

            call_args = mock_request.call_args
            assert "campaign_id" in str(call_args)

    def test_extract_reports_api_error(self, extractor):
        """Test report extraction with API error."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.side_effect = Exception("API Error")

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract_reports(start_date, end_date))

            # Should gracefully handle error and return empty
            assert len(results) == 0


class TestLazadaAdsExtractSponsoredProducts:
    """Tests for sponsored products extraction."""

    def test_extract_sponsored_products_success(self, extractor):
        """Test successful sponsored products extraction."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "products": [
                    {"product_id": "456", "status": "active"},
                    {"product_id": "457", "status": "active"},
                ],
                "total": 2,
            }

            results = list(extractor.extract_sponsored_products())

            assert len(results) == 2
            assert results[0]["type"] == "sponsored_product"

    def test_extract_sponsored_products_by_campaign(self, extractor):
        """Test sponsored products extraction filtered by campaign."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "products": [{"product_id": "456"}],
                "total": 1,
            }

            list(extractor.extract_sponsored_products(campaign_id="123"))

            call_args = mock_request.call_args
            assert "campaign_id" in str(call_args)


class TestLazadaAdsGetCampaignDetail:
    """Tests for getting campaign detail."""

    def test_get_campaign_detail_success(self, extractor):
        """Test successful campaign detail retrieval."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "campaign": {
                    "campaign_id": "123",
                    "name": "Test Campaign",
                    "status": "active",
                    "budget": 1000.00,
                },
            }

            result = extractor.get_campaign_detail(campaign_id="123")

            assert result is not None
            assert result["campaign_id"] == "123"

    def test_get_campaign_detail_not_found(self, extractor):
        """Test campaign detail not found."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.side_effect = Exception("Campaign not found")

            result = extractor.get_campaign_detail(campaign_id="999")

            assert result is None


class TestLazadaAdsGetCampaignMetrics:
    """Tests for getting campaign metrics."""

    def test_get_campaign_metrics_success(self, extractor):
        """Test successful campaign metrics retrieval."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "reports": [
                    {"impressions": 1000, "clicks": 50, "spend": 100.00, "conversions": 5},
                    {"impressions": 1200, "clicks": 60, "spend": 120.00, "conversions": 6},
                ],
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            result = extractor.get_campaign_metrics("123", start_date, end_date)

            assert result is not None
            assert result["campaign_id"] == "123"
            assert result["impressions"] == 2200
            assert result["clicks"] == 110
            assert result["spend"] == 220.00
            assert result["conversions"] == 11
            assert "ctr" in result
            assert "cpc" in result

    def test_get_campaign_metrics_empty(self, extractor):
        """Test campaign metrics with no data."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {"reports": []}

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            result = extractor.get_campaign_metrics("123", start_date, end_date)

            assert result is None


class TestLazadaAdsExtract:
    """Tests for main extract method."""

    def test_extract_all_data_types(self, extractor):
        """Test extract with default data_type (all)."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.side_effect = [
                # Campaigns response
                {"campaigns": [{"campaign_id": "123"}], "total": 1},
                # Reports response
                {"reports": [{"date": "2024-01-01"}]},
            ]

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract(start_date, end_date))

            # Should have campaigns + reports
            assert len(results) == 2

    def test_extract_campaigns_only(self, extractor):
        """Test extract with campaigns data_type."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "campaigns": [{"campaign_id": "123"}],
                "total": 1,
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract(start_date, end_date, data_type="campaigns"))

            assert len(results) == 1
            assert results[0]["type"] == "campaign"

    def test_extract_reports_only(self, extractor):
        """Test extract with reports data_type."""
        extractor._authenticated = True

        with patch.object(extractor, "_make_request") as mock_request:
            mock_request.return_value = {
                "reports": [{"date": "2024-01-01"}],
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract(start_date, end_date, data_type="reports"))

            assert len(results) == 1
            assert results[0]["type"] == "report"
