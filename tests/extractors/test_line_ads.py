"""Tests for LINE Ads extractor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.line_ads import LINEAdsExtractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.line_ads.get_settings") as mock_line, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.line_ads_access_key = "test_access_key"
        settings.line_ads_secret_key = "test_secret_key"
        settings.line_ads_ad_account_id = "A123456"
        mock_line.return_value = settings
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
    return LINEAdsExtractor()


class TestLINEAdsExtractorInit:
    """Tests for extractor initialization."""

    def test_init_with_settings(self, extractor, mock_settings):
        """Test initialization with settings."""
        assert extractor.access_key == "test_access_key"
        assert extractor.secret_key == "test_secret_key"
        assert extractor.ad_account_id == "A123456"

    def test_init_with_custom_ad_account(self, mock_settings):
        """Test initialization with custom ad account ID."""
        extractor = LINEAdsExtractor(ad_account_id="B987654")
        assert extractor.ad_account_id == "B987654"


class TestLINEAdsSignature:
    """Tests for JWS signature generation."""

    def test_generate_signature(self, extractor):
        """Test signature generation."""
        signature = extractor._generate_signature(
            method="GET",
            path="/api/v3/adaccounts/A123456",
            date="Wed, 22 Dec 2021 00:00:00 GMT",
        )

        # Signature should be base64 encoded
        assert signature
        assert isinstance(signature, str)

    def test_generate_signature_with_body(self, extractor):
        """Test signature generation with request body."""
        signature = extractor._generate_signature(
            method="POST",
            path="/api/v3/campaigns",
            date="Wed, 22 Dec 2021 00:00:00 GMT",
            body='{"name":"Test Campaign"}',
        )

        assert signature
        assert isinstance(signature, str)

    def test_get_date_header(self, extractor):
        """Test date header generation."""
        date_header = extractor._get_date_header()

        # Should be RFC 2822 format
        assert "GMT" in date_header


class TestLINEAdsAuthentication:
    """Tests for authentication."""

    def test_authenticate_missing_access_key(self):
        """Test authentication fails without access_key."""
        with patch("src.extractors.line_ads.get_settings") as mock_line, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.line_ads_access_key = ""
            settings.line_ads_secret_key = "secret"
            settings.line_ads_ad_account_id = "A123"
            mock_line.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 60}

            extractor = LINEAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "Missing LINE Ads credentials" in str(exc_info.value)

    def test_authenticate_missing_ad_account(self):
        """Test authentication fails without ad_account_id."""
        with patch("src.extractors.line_ads.get_settings") as mock_line, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.line_ads_access_key = "key"
            settings.line_ads_secret_key = "secret"
            settings.line_ads_ad_account_id = ""
            mock_line.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 60}

            extractor = LINEAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "No ad_account_id specified" in str(exc_info.value)

    def test_authenticate_success(self, extractor):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "A123456",
            "name": "Test Account",
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client

        result = extractor.authenticate()

        assert result is True
        assert extractor._authenticated is True

    def test_authenticate_unauthorized(self, extractor):
        """Test authentication with unauthorized response."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json.return_value = {"error": "Unauthorized"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client

        from src.extractors.base import AuthenticationError
        with pytest.raises(AuthenticationError):
            extractor.authenticate()


class TestLINEAdsExtractReports:
    """Tests for report extraction."""

    def test_extract_reports_success(self, extractor):
        """Test successful report extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"campaign_id": "123", "impressions": 1000, "clicks": 50},
                {"campaign_id": "124", "impressions": 2000, "clicks": 100},
            ],
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_reports(start_date, end_date, level="CAMPAIGN"))

        assert len(results) == 2
        assert results[0]["type"] == "campaign"
        assert results[0]["platform"] == "line_ads"

    def test_extract_reports_invalid_level(self, extractor):
        """Test extraction with invalid level."""
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(ValueError) as exc_info:
            list(extractor.extract_reports(start_date, end_date, level="INVALID"))
        assert "Invalid level" in str(exc_info.value)

    def test_extract_reports_api_error(self, extractor):
        """Test API error during report extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"error": "Internal Server Error"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        from src.extractors.base import APIError
        with pytest.raises(APIError):
            list(extractor.extract_reports(start_date, end_date))


class TestLINEAdsExtractCampaigns:
    """Tests for campaign extraction."""

    def test_extract_campaigns_success(self, extractor):
        """Test successful campaign extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {"id": "123", "name": "Campaign 1"},
                {"id": "124", "name": "Campaign 2"},
            ],
            "totalPages": 1,
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 2
        assert results[0]["type"] == "campaign"
        assert results[0]["data"]["id"] == "123"

    def test_extract_campaigns_with_pagination(self, extractor):
        """Test campaign extraction with pagination."""
        mock_response_page1 = MagicMock()
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = {
            "content": [{"id": "123"}],
            "totalPages": 2,
        }

        mock_response_page2 = MagicMock()
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = {
            "content": [{"id": "124"}],
            "totalPages": 2,
        }

        mock_client = MagicMock()
        mock_client.get.side_effect = [mock_response_page1, mock_response_page2]
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 2


class TestLINEAdsExtractAdGroups:
    """Tests for ad group extraction."""

    def test_extract_adgroups_success(self, extractor):
        """Test successful ad group extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {"id": "456", "name": "AdGroup 1"},
            ],
            "totalPages": 1,
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_adgroups())

        assert len(results) == 1
        assert results[0]["type"] == "adgroup"

    def test_extract_adgroups_by_campaign(self, extractor):
        """Test ad group extraction filtered by campaign."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"id": "456"}],
            "totalPages": 1,
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_adgroups(campaign_id="123"))

        assert len(results) == 1
        # Verify endpoint includes campaign_id
        call_args = mock_client.get.call_args
        assert "campaigns/123/adgroups" in str(call_args)


class TestLINEAdsExtractAds:
    """Tests for ad extraction."""

    def test_extract_ads_success(self, extractor):
        """Test successful ad extraction."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [
                {"id": "789", "name": "Ad 1"},
            ],
            "totalPages": 1,
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_ads())

        assert len(results) == 1
        assert results[0]["type"] == "ad"
        assert results[0]["data"]["id"] == "789"


class TestLINEAdsExtract:
    """Tests for main extract method."""

    def test_extract_default_level(self, extractor):
        """Test extract with default level (CAMPAIGN)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date))

        # Verify the endpoint was for CAMPAIGN level
        call_args = mock_client.get.call_args
        assert "CAMPAIGN" in str(call_args)

    def test_extract_with_level(self, extractor):
        """Test extract with specified level."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date, level="AD_GROUP"))

        call_args = mock_client.get.call_args
        assert "AD_GROUP" in str(call_args)


class TestLINEAdsDownloadReportCSV:
    """Tests for CSV report download."""

    def test_download_report_csv_success(self, extractor):
        """Test successful CSV report download."""
        csv_content = b"campaign_id,impressions,clicks\n123,1000,50\n"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = csv_content

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        result = extractor.download_report_csv(start_date, end_date)

        assert result == csv_content

    def test_download_report_csv_error(self, extractor):
        """Test CSV download error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        from src.extractors.base import APIError
        with pytest.raises(APIError) as exc_info:
            extractor.download_report_csv(start_date, end_date)
        assert "Failed to download report" in str(exc_info.value)
