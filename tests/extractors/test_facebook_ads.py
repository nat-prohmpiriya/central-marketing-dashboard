"""Tests for Facebook Ads extractor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.facebook_ads import FacebookAdsExtractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.facebook_ads.get_settings") as mock_fb, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.facebook_app_id = "test_app_id"
        settings.facebook_app_secret = "test_app_secret"
        settings.facebook_access_token = "test_access_token"
        settings.facebook_ad_account_id = "act_123456789"
        mock_fb.return_value = settings
        mock_base.return_value = settings
        mock_rate.return_value = {
            "requests_per_minute": 200,
            "retry_after_seconds": 60,
            "max_retries": 3,
        }
        yield settings


@pytest.fixture
def extractor(mock_settings):
    """Create extractor instance."""
    return FacebookAdsExtractor()


class TestFacebookAdsExtractorInit:
    """Tests for extractor initialization."""

    def test_init_with_settings(self, extractor, mock_settings):
        """Test initialization with settings."""
        assert extractor.app_id == "test_app_id"
        assert extractor.app_secret == "test_app_secret"
        assert extractor._access_token == "test_access_token"
        assert extractor.ad_account_id == "act_123456789"

    def test_init_with_custom_ad_account(self, mock_settings):
        """Test initialization with custom ad account ID."""
        extractor = FacebookAdsExtractor(ad_account_id="act_987654321")
        assert extractor.ad_account_id == "act_987654321"

    def test_init_adds_act_prefix(self, mock_settings):
        """Test initialization adds act_ prefix if missing."""
        extractor = FacebookAdsExtractor(ad_account_id="987654321")
        assert extractor.ad_account_id == "act_987654321"


class TestFacebookAdsAuthentication:
    """Tests for authentication."""

    def test_authenticate_missing_app_id(self):
        """Test authentication fails without app_id."""
        with patch("src.extractors.facebook_ads.get_settings") as mock_fb, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.facebook_app_id = ""
            settings.facebook_app_secret = "secret"
            settings.facebook_access_token = "token"
            settings.facebook_ad_account_id = "act_123"
            mock_fb.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 200}

            extractor = FacebookAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "Missing Facebook credentials" in str(exc_info.value)

    def test_authenticate_missing_access_token(self):
        """Test authentication fails without access_token."""
        with patch("src.extractors.facebook_ads.get_settings") as mock_fb, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.facebook_app_id = "app_id"
            settings.facebook_app_secret = "secret"
            settings.facebook_access_token = ""
            settings.facebook_ad_account_id = "act_123"
            mock_fb.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 200}

            extractor = FacebookAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "No access_token available" in str(exc_info.value)

    def test_authenticate_missing_ad_account(self):
        """Test authentication fails without ad_account_id."""
        with patch("src.extractors.facebook_ads.get_settings") as mock_fb, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.facebook_app_id = "app_id"
            settings.facebook_app_secret = "secret"
            settings.facebook_access_token = "token"
            settings.facebook_ad_account_id = ""
            mock_fb.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 200}

            extractor = FacebookAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "No ad_account_id specified" in str(exc_info.value)

    def test_authenticate_sdk_not_installed(self, extractor):
        """Test authentication fails when SDK not installed."""
        with patch.dict("sys.modules", {"facebook_business": None}):
            with patch(
                "src.extractors.facebook_ads.FacebookAdsExtractor._init_sdk"
            ) as mock_init:
                mock_init.side_effect = ImportError("No module named 'facebook_business'")

                from src.extractors.base import AuthenticationError
                with pytest.raises(AuthenticationError):
                    extractor.authenticate()

    def test_authenticate_success(self, extractor):
        """Test successful authentication."""
        mock_api = MagicMock()
        mock_ad_account = MagicMock()
        mock_ad_account.api_get.return_value = {
            "name": "Test Account",
            "account_status": 1,
            "currency": "USD",
        }

        with patch.object(extractor, "_init_sdk") as mock_init:
            mock_init.side_effect = lambda: setattr(extractor, "_ad_account", mock_ad_account)
            extractor._ad_account = mock_ad_account

            result = extractor.authenticate()

            assert result is True
            assert extractor._authenticated is True

    def test_authenticate_invalid_token(self, extractor):
        """Test authentication fails with invalid token."""
        mock_ad_account = MagicMock()
        mock_ad_account.api_get.side_effect = Exception("OAuthException: Invalid access token")

        with patch.object(extractor, "_init_sdk"):
            extractor._ad_account = mock_ad_account

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "Invalid or expired access token" in str(exc_info.value)


class TestFacebookAdsLongLivedToken:
    """Tests for long-lived token exchange."""

    def test_get_long_lived_token_success(self, extractor):
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "long_lived_token_123",
            "token_type": "bearer",
            "expires_in": 5184000,
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client

        result = extractor.get_long_lived_token("short_lived_token")

        assert result["access_token"] == "long_lived_token_123"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == 5184000

    def test_get_long_lived_token_error(self, extractor):
        """Test token exchange error."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {
                "message": "Invalid token",
                "type": "OAuthException",
            }
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        extractor._client = mock_client

        from src.extractors.base import APIError
        with pytest.raises(APIError) as exc_info:
            extractor.get_long_lived_token("invalid_token")
        assert "Token exchange failed" in str(exc_info.value)


class TestFacebookAdsExtractInsights:
    """Tests for insights extraction."""

    def test_extract_insights_success(self, extractor):
        """Test successful insights extraction."""
        mock_insights = [
            {
                "campaign_id": "123",
                "campaign_name": "Test Campaign",
                "impressions": "1000",
                "clicks": "50",
                "spend": "100.00",
            },
            {
                "campaign_id": "124",
                "campaign_name": "Test Campaign 2",
                "impressions": "2000",
                "clicks": "100",
                "spend": "200.00",
            },
        ]

        mock_ad_account = MagicMock()
        mock_ad_account.get_insights.return_value = mock_insights
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_insights(start_date, end_date))

        assert len(results) == 2
        assert results[0]["type"] == "insight"
        assert results[0]["platform"] == "facebook_ads"
        assert results[0]["data"]["campaign_id"] == "123"
        assert results[1]["data"]["campaign_id"] == "124"

    def test_extract_insights_with_breakdowns(self, extractor):
        """Test insights extraction with breakdowns."""
        mock_insights = [
            {
                "campaign_id": "123",
                "age": "25-34",
                "gender": "male",
                "impressions": "500",
            },
        ]

        mock_ad_account = MagicMock()
        mock_ad_account.get_insights.return_value = mock_insights
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_insights(
            start_date,
            end_date,
            breakdowns=["age", "gender"],
        ))

        assert len(results) == 1
        mock_ad_account.get_insights.assert_called_once()
        call_params = mock_ad_account.get_insights.call_args[1]["params"]
        assert call_params["breakdowns"] == ["age", "gender"]

    def test_extract_insights_invalid_breakdown_warning(self, extractor):
        """Test warning for invalid breakdowns."""
        mock_ad_account = MagicMock()
        mock_ad_account.get_insights.return_value = []
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        # Invalid breakdown should be filtered out
        list(extractor.extract_insights(
            start_date,
            end_date,
            breakdowns=["invalid_breakdown", "age"],
        ))

        call_params = mock_ad_account.get_insights.call_args[1]["params"]
        assert call_params["breakdowns"] == ["age"]

    def test_extract_insights_api_error(self, extractor):
        """Test API error during insights extraction."""
        mock_ad_account = MagicMock()
        mock_ad_account.get_insights.side_effect = Exception("API Error")
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        from src.extractors.base import APIError
        with pytest.raises(APIError) as exc_info:
            list(extractor.extract_insights(start_date, end_date))
        assert "Failed to fetch insights" in str(exc_info.value)


class TestFacebookAdsExtractCampaigns:
    """Tests for campaign extraction."""

    def test_extract_campaigns_success(self, extractor):
        """Test successful campaign extraction."""
        mock_campaigns = [
            {
                "id": "123",
                "name": "Campaign 1",
                "status": "ACTIVE",
                "objective": "CONVERSIONS",
            },
            {
                "id": "124",
                "name": "Campaign 2",
                "status": "PAUSED",
                "objective": "TRAFFIC",
            },
        ]

        mock_ad_account = MagicMock()
        mock_ad_account.get_campaigns.return_value = mock_campaigns
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        results = list(extractor.extract_campaigns())

        assert len(results) == 2
        assert results[0]["type"] == "campaign"
        assert results[0]["data"]["id"] == "123"
        assert results[1]["data"]["id"] == "124"

    def test_extract_campaigns_include_deleted(self, extractor):
        """Test campaign extraction including deleted."""
        mock_ad_account = MagicMock()
        mock_ad_account.get_campaigns.return_value = []
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        list(extractor.extract_campaigns(include_deleted=True))

        call_params = mock_ad_account.get_campaigns.call_args[1]["params"]
        assert "DELETED" in call_params["effective_status"]


class TestFacebookAdsExtractAdSets:
    """Tests for ad set extraction."""

    def test_extract_adsets_success(self, extractor):
        """Test successful ad set extraction."""
        mock_adsets = [
            {
                "id": "456",
                "name": "AdSet 1",
                "campaign_id": "123",
                "status": "ACTIVE",
            },
        ]

        mock_ad_account = MagicMock()
        mock_ad_account.get_ad_sets.return_value = mock_adsets
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        results = list(extractor.extract_adsets())

        assert len(results) == 1
        assert results[0]["type"] == "adset"
        assert results[0]["data"]["id"] == "456"

    def test_extract_adsets_by_campaign(self, extractor):
        """Test ad set extraction filtered by campaign."""
        mock_adsets = [
            {"id": "456", "name": "AdSet 1"},
        ]

        mock_campaign = MagicMock()
        mock_campaign.get_ad_sets.return_value = mock_adsets
        extractor._authenticated = True

        with patch(
            "facebook_business.adobjects.campaign.Campaign"
        ) as MockCampaign:
            MockCampaign.return_value = mock_campaign

            results = list(extractor.extract_adsets(campaign_id="123"))

            assert len(results) == 1
            MockCampaign.assert_called_once_with("123")


class TestFacebookAdsExtractAds:
    """Tests for ad extraction."""

    def test_extract_ads_success(self, extractor):
        """Test successful ad extraction."""
        mock_ads = [
            {
                "id": "789",
                "name": "Ad 1",
                "adset_id": "456",
                "status": "ACTIVE",
            },
        ]

        mock_ad_account = MagicMock()
        mock_ad_account.get_ads.return_value = mock_ads
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        results = list(extractor.extract_ads())

        assert len(results) == 1
        assert results[0]["type"] == "ad"
        assert results[0]["data"]["id"] == "789"

    def test_extract_ads_by_adset(self, extractor):
        """Test ad extraction filtered by ad set."""
        mock_ads = [
            {"id": "789", "name": "Ad 1"},
        ]

        mock_adset = MagicMock()
        mock_adset.get_ads.return_value = mock_ads
        extractor._authenticated = True

        with patch("facebook_business.adobjects.adset.AdSet") as MockAdSet:
            MockAdSet.return_value = mock_adset

            results = list(extractor.extract_ads(adset_id="456"))

            assert len(results) == 1
            MockAdSet.assert_called_once_with("456")


class TestFacebookAdsExtract:
    """Tests for main extract method."""

    def test_extract_default_level(self, extractor):
        """Test extract with default level (ad)."""
        mock_ad_account = MagicMock()
        mock_ad_account.get_insights.return_value = []
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date))

        call_params = mock_ad_account.get_insights.call_args[1]["params"]
        assert call_params["level"] == "ad"

    def test_extract_campaign_level(self, extractor):
        """Test extract with campaign level."""
        mock_ad_account = MagicMock()
        mock_ad_account.get_insights.return_value = []
        extractor._ad_account = mock_ad_account
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date, level="campaign"))

        call_params = mock_ad_account.get_insights.call_args[1]["params"]
        assert call_params["level"] == "campaign"
