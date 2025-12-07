"""Tests for TikTok Ads extractor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.tiktok_ads import TikTokAdsExtractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.tiktok_ads.get_settings") as mock_tt, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.tiktok_ads_app_id = "test_app_id"
        settings.tiktok_ads_app_secret = "test_app_secret"
        settings.tiktok_ads_access_token = "test_access_token"
        settings.tiktok_ads_advertiser_id = "1234567890"
        mock_tt.return_value = settings
        mock_base.return_value = settings
        mock_rate.return_value = {
            "requests_per_minute": 100,
            "retry_after_seconds": 60,
            "max_retries": 3,
        }
        yield settings


@pytest.fixture
def extractor(mock_settings):
    """Create extractor instance."""
    return TikTokAdsExtractor()


class TestTikTokAdsExtractorInit:
    """Tests for extractor initialization."""

    def test_init_with_settings(self, extractor, mock_settings):
        """Test initialization with settings."""
        assert extractor.app_id == "test_app_id"
        assert extractor.app_secret == "test_app_secret"
        assert extractor._access_token == "test_access_token"
        assert extractor.advertiser_id == "1234567890"

    def test_init_with_custom_advertiser_id(self, mock_settings):
        """Test initialization with custom advertiser ID."""
        extractor = TikTokAdsExtractor(advertiser_id="9876543210")
        assert extractor.advertiser_id == "9876543210"


class TestTikTokAdsAuthentication:
    """Tests for authentication."""

    def test_authenticate_missing_app_id(self):
        """Test authentication fails without app_id."""
        with patch("src.extractors.tiktok_ads.get_settings") as mock_tt, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.tiktok_ads_app_id = ""
            settings.tiktok_ads_app_secret = "secret"
            settings.tiktok_ads_access_token = "token"
            settings.tiktok_ads_advertiser_id = "123"
            mock_tt.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = TikTokAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "Missing TikTok Ads credentials" in str(exc_info.value)

    def test_authenticate_missing_access_token(self):
        """Test authentication fails without access_token."""
        with patch("src.extractors.tiktok_ads.get_settings") as mock_tt, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.tiktok_ads_app_id = "app_id"
            settings.tiktok_ads_app_secret = "secret"
            settings.tiktok_ads_access_token = ""
            settings.tiktok_ads_advertiser_id = "123"
            mock_tt.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = TikTokAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "No access_token available" in str(exc_info.value)

    def test_authenticate_missing_advertiser_id(self):
        """Test authentication fails without advertiser_id."""
        with patch("src.extractors.tiktok_ads.get_settings") as mock_tt, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.tiktok_ads_app_id = "app_id"
            settings.tiktok_ads_app_secret = "secret"
            settings.tiktok_ads_access_token = "token"
            settings.tiktok_ads_advertiser_id = ""
            mock_tt.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = TikTokAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "No advertiser_id specified" in str(exc_info.value)

    def test_authenticate_success(self, extractor):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [{"name": "Test Advertiser", "advertiser_id": "1234567890"}]
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client

        result = extractor.authenticate()

        assert result is True
        assert extractor._authenticated is True

    def test_authenticate_api_error(self, extractor):
        """Test authentication with API error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 40001,
            "message": "Invalid token",
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client

        from src.extractors.base import AuthenticationError
        with pytest.raises(AuthenticationError):
            extractor.authenticate()


class TestTikTokAdsAuthorizationUrl:
    """Tests for authorization URL generation."""

    def test_get_authorization_url(self, extractor):
        """Test authorization URL generation."""
        url = extractor.get_authorization_url(
            redirect_uri="https://example.com/callback",
            state="test_state",
        )

        assert "business-api.tiktok.com/portal/auth" in url
        assert "app_id=test_app_id" in url
        assert "redirect_uri=" in url
        assert "state=test_state" in url


class TestTikTokAdsTokenExchange:
    """Tests for token exchange."""

    def test_exchange_code_for_token_success(self, extractor):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "access_token": "new_access_token",
                "advertiser_ids": ["1234567890"],
            },
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        extractor._client = mock_client

        result = extractor.exchange_code_for_token("auth_code_123")

        assert result["access_token"] == "new_access_token"
        assert extractor._access_token == "new_access_token"

    def test_exchange_code_for_token_error(self, extractor):
        """Test token exchange error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 40001,
            "message": "Invalid auth code",
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        extractor._client = mock_client

        from src.extractors.base import AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            extractor.exchange_code_for_token("invalid_code")
        assert "Token exchange failed" in str(exc_info.value)


class TestTikTokAdsExtractReports:
    """Tests for report extraction."""

    def test_extract_reports_success(self, extractor):
        """Test successful report extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [
                    {
                        "dimensions": {"ad_id": "123"},
                        "metrics": {"spend": "100.00", "impressions": "1000"},
                    },
                    {
                        "dimensions": {"ad_id": "124"},
                        "metrics": {"spend": "200.00", "impressions": "2000"},
                    },
                ],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_reports(start_date, end_date, level="ad"))

        assert len(results) == 2
        assert results[0]["type"] == "ad"
        assert results[0]["platform"] == "tiktok_ads"
        assert results[0]["data"]["dimensions"]["ad_id"] == "123"

    def test_extract_reports_with_pagination(self, extractor):
        """Test report extraction with pagination."""
        mock_response_page1 = MagicMock()
        mock_response_page1.json.return_value = {
            "code": 0,
            "data": {
                "list": [{"dimensions": {"ad_id": "123"}}],
                "page_info": {"page": 1, "total_page": 2},
            },
        }

        mock_response_page2 = MagicMock()
        mock_response_page2.json.return_value = {
            "code": 0,
            "data": {
                "list": [{"dimensions": {"ad_id": "124"}}],
                "page_info": {"page": 2, "total_page": 2},
            },
        }

        mock_client = MagicMock()
        mock_client.post.side_effect = [mock_response_page1, mock_response_page2]
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_reports(start_date, end_date))

        assert len(results) == 2

    def test_extract_reports_invalid_level(self, extractor):
        """Test extraction with invalid level."""
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(ValueError) as exc_info:
            list(extractor.extract_reports(start_date, end_date, level="invalid"))
        assert "Invalid level" in str(exc_info.value)

    def test_extract_reports_api_error(self, extractor):
        """Test API error during report extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 40001,
            "message": "API Error",
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        from src.extractors.base import APIError
        with pytest.raises(APIError):
            list(extractor.extract_reports(start_date, end_date))


class TestTikTokAdsExtractCampaigns:
    """Tests for campaign extraction."""

    def test_extract_campaigns_success(self, extractor):
        """Test successful campaign extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [
                    {"campaign_id": "123", "campaign_name": "Campaign 1"},
                    {"campaign_id": "124", "campaign_name": "Campaign 2"},
                ],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 2
        assert results[0]["type"] == "campaign"
        assert results[0]["data"]["campaign_id"] == "123"


class TestTikTokAdsExtractAdGroups:
    """Tests for ad group extraction."""

    def test_extract_adgroups_success(self, extractor):
        """Test successful ad group extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [
                    {"adgroup_id": "456", "adgroup_name": "AdGroup 1"},
                ],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_adgroups())

        assert len(results) == 1
        assert results[0]["type"] == "adgroup"
        assert results[0]["data"]["adgroup_id"] == "456"

    def test_extract_adgroups_by_campaign(self, extractor):
        """Test ad group extraction filtered by campaigns."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [{"adgroup_id": "456"}],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_adgroups(campaign_ids=["123"]))

        assert len(results) == 1
        call_args = mock_client.get.call_args
        assert "campaign_ids" in str(call_args)


class TestTikTokAdsExtractAds:
    """Tests for ad extraction."""

    def test_extract_ads_success(self, extractor):
        """Test successful ad extraction."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [
                    {"ad_id": "789", "ad_name": "Ad 1"},
                ],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_ads())

        assert len(results) == 1
        assert results[0]["type"] == "ad"
        assert results[0]["data"]["ad_id"] == "789"


class TestTikTokAdsExtract:
    """Tests for main extract method."""

    def test_extract_default_level(self, extractor):
        """Test extract with default level (ad)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date))

        call_args = mock_client.post.call_args
        assert "AUCTION_AD" in str(call_args)

    def test_extract_with_level(self, extractor):
        """Test extract with specified level."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [],
                "page_info": {"page": 1, "total_page": 1},
            },
        }

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date, level="campaign"))

        call_args = mock_client.post.call_args
        assert "AUCTION_CAMPAIGN" in str(call_args)


class TestTikTokAdsGetAdvertiserIds:
    """Tests for getting advertiser IDs."""

    def test_get_advertiser_ids(self, extractor):
        """Test getting list of advertiser IDs."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": 0,
            "data": {
                "list": [
                    {"advertiser_id": "1234567890"},
                    {"advertiser_id": "9876543210"},
                ],
            },
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client
        extractor._authenticated = True

        results = extractor.get_advertiser_ids()

        assert len(results) == 2
        assert "1234567890" in results
        assert "9876543210" in results
