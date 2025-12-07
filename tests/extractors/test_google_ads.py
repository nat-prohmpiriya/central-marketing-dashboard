"""Tests for Google Ads extractor."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.google_ads import GoogleAdsExtractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.google_ads.get_settings") as mock_ga, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.google_ads_developer_token = "test_dev_token"
        settings.google_ads_client_id = "test_client_id"
        settings.google_ads_client_secret = "test_client_secret"
        settings.google_ads_refresh_token = "test_refresh_token"
        settings.google_ads_customer_id = "123-456-7890"
        settings.google_ads_login_customer_id = ""
        mock_ga.return_value = settings
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
    return GoogleAdsExtractor()


class TestGoogleAdsExtractorInit:
    """Tests for extractor initialization."""

    def test_init_with_settings(self, extractor, mock_settings):
        """Test initialization with settings."""
        assert extractor.developer_token == "test_dev_token"
        assert extractor.client_id == "test_client_id"
        assert extractor.client_secret == "test_client_secret"
        assert extractor.refresh_token == "test_refresh_token"
        # Dashes should be removed
        assert extractor.customer_id == "1234567890"

    def test_init_with_custom_customer_id(self, mock_settings):
        """Test initialization with custom customer ID."""
        extractor = GoogleAdsExtractor(customer_id="987-654-3210")
        assert extractor.customer_id == "9876543210"

    def test_init_removes_dashes(self, mock_settings):
        """Test initialization removes dashes from customer ID."""
        extractor = GoogleAdsExtractor(customer_id="111-222-3333")
        assert extractor.customer_id == "1112223333"

    def test_init_with_login_customer_id(self):
        """Test initialization with login customer ID (manager account)."""
        with patch("src.extractors.google_ads.get_settings") as mock_ga, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.google_ads_developer_token = "token"
            settings.google_ads_client_id = "client_id"
            settings.google_ads_client_secret = "secret"
            settings.google_ads_refresh_token = "refresh"
            settings.google_ads_customer_id = "123-456-7890"
            settings.google_ads_login_customer_id = "111-222-3333"
            mock_ga.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = GoogleAdsExtractor()
            assert extractor.login_customer_id == "1112223333"


class TestGoogleAdsAuthentication:
    """Tests for authentication."""

    def test_authenticate_missing_developer_token(self):
        """Test authentication fails without developer token."""
        with patch("src.extractors.google_ads.get_settings") as mock_ga, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.google_ads_developer_token = ""
            settings.google_ads_client_id = "client_id"
            settings.google_ads_client_secret = "secret"
            settings.google_ads_refresh_token = "refresh"
            settings.google_ads_customer_id = "123"
            settings.google_ads_login_customer_id = ""
            mock_ga.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = GoogleAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "developer_token" in str(exc_info.value)

    def test_authenticate_missing_client_credentials(self):
        """Test authentication fails without OAuth credentials."""
        with patch("src.extractors.google_ads.get_settings") as mock_ga, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.google_ads_developer_token = "token"
            settings.google_ads_client_id = ""
            settings.google_ads_client_secret = "secret"
            settings.google_ads_refresh_token = "refresh"
            settings.google_ads_customer_id = "123"
            settings.google_ads_login_customer_id = ""
            mock_ga.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = GoogleAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "OAuth credentials" in str(exc_info.value)

    def test_authenticate_missing_refresh_token(self):
        """Test authentication fails without refresh token."""
        with patch("src.extractors.google_ads.get_settings") as mock_ga, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.google_ads_developer_token = "token"
            settings.google_ads_client_id = "client_id"
            settings.google_ads_client_secret = "secret"
            settings.google_ads_refresh_token = ""
            settings.google_ads_customer_id = "123"
            settings.google_ads_login_customer_id = ""
            mock_ga.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = GoogleAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "refresh_token" in str(exc_info.value)

    def test_authenticate_missing_customer_id(self):
        """Test authentication fails without customer ID."""
        with patch("src.extractors.google_ads.get_settings") as mock_ga, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.google_ads_developer_token = "token"
            settings.google_ads_client_id = "client_id"
            settings.google_ads_client_secret = "secret"
            settings.google_ads_refresh_token = "refresh"
            settings.google_ads_customer_id = ""
            settings.google_ads_login_customer_id = ""
            mock_ga.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 100}

            extractor = GoogleAdsExtractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "customer_id" in str(exc_info.value)

    def test_authenticate_sdk_not_installed(self, extractor):
        """Test authentication fails when SDK not installed."""
        with patch.object(extractor, "_init_client") as mock_init:
            mock_init.side_effect = ImportError("No module named 'google.ads'")

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError):
                extractor.authenticate()

    def test_authenticate_success(self, extractor):
        """Test successful authentication."""
        mock_service = MagicMock()
        mock_row = MagicMock()
        mock_row.customer.descriptive_name = "Test Account"
        mock_service.search.return_value = [mock_row]

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service

        with patch.object(extractor, "_init_client"):
            extractor._google_ads_client = mock_client

            result = extractor.authenticate()

            assert result is True
            assert extractor._authenticated is True


class TestGoogleAdsExtractPerformance:
    """Tests for performance data extraction."""

    def test_extract_campaigns_success(self, extractor):
        """Test successful campaign extraction."""
        mock_row = MagicMock()
        mock_row._pb = MagicMock()

        mock_service = MagicMock()
        mock_service.search.return_value = [mock_row]

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        with patch.object(extractor, "_row_to_dict") as mock_convert:
            mock_convert.return_value = {
                "campaign": {"id": "123", "name": "Test Campaign"},
                "metrics": {"impressions": "1000", "clicks": "50"},
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract_campaigns(start_date, end_date))

            assert len(results) == 1
            assert results[0]["type"] == "campaign"
            assert results[0]["platform"] == "google_ads"
            assert results[0]["data"]["campaign"]["id"] == "123"

    def test_extract_adgroups_success(self, extractor):
        """Test successful ad group extraction."""
        mock_row = MagicMock()
        mock_row._pb = MagicMock()

        mock_service = MagicMock()
        mock_service.search.return_value = [mock_row]

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        with patch.object(extractor, "_row_to_dict") as mock_convert:
            mock_convert.return_value = {
                "adGroup": {"id": "456", "name": "Test AdGroup"},
                "metrics": {"impressions": "500"},
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract_adgroups(start_date, end_date))

            assert len(results) == 1
            assert results[0]["type"] == "adgroup"

    def test_extract_ads_success(self, extractor):
        """Test successful ad extraction."""
        mock_row = MagicMock()
        mock_row._pb = MagicMock()

        mock_service = MagicMock()
        mock_service.search.return_value = [mock_row]

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        with patch.object(extractor, "_row_to_dict") as mock_convert:
            mock_convert.return_value = {
                "adGroupAd": {"ad": {"id": "789"}},
                "metrics": {"impressions": "200"},
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract_ads(start_date, end_date))

            assert len(results) == 1
            assert results[0]["type"] == "ad"

    def test_extract_keywords_success(self, extractor):
        """Test successful keyword extraction."""
        mock_row = MagicMock()
        mock_row._pb = MagicMock()

        mock_service = MagicMock()
        mock_service.search.return_value = [mock_row]

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        with patch.object(extractor, "_row_to_dict") as mock_convert:
            mock_convert.return_value = {
                "adGroupCriterion": {"keyword": {"text": "test keyword"}},
                "metrics": {"impressions": "100"},
            }

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(extractor.extract_keywords(start_date, end_date))

            assert len(results) == 1
            assert results[0]["type"] == "keyword"

    def test_extract_performance_invalid_level(self, extractor):
        """Test extraction with invalid level raises error."""
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(ValueError) as exc_info:
            list(extractor.extract_performance(start_date, end_date, level="invalid"))
        assert "Invalid level" in str(exc_info.value)

    def test_extract_api_error(self, extractor):
        """Test API error during extraction."""
        mock_service = MagicMock()
        mock_service.search.side_effect = Exception("API Error")

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        from src.extractors.base import APIError
        with pytest.raises(APIError) as exc_info:
            list(extractor.extract_campaigns(start_date, end_date))
        assert "GAQL query failed" in str(exc_info.value)


class TestGoogleAdsExtractCustom:
    """Tests for custom GAQL queries."""

    def test_extract_custom_success(self, extractor):
        """Test successful custom query execution."""
        mock_row = MagicMock()
        mock_row._pb = MagicMock()

        mock_service = MagicMock()
        mock_service.search.return_value = [mock_row, mock_row]

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        with patch.object(extractor, "_row_to_dict") as mock_convert:
            mock_convert.return_value = {"custom": "data"}

            custom_query = "SELECT campaign.id FROM campaign LIMIT 10"
            results = list(extractor.extract_custom(custom_query))

            assert len(results) == 2
            assert results[0]["type"] == "custom"
            assert results[0]["data"]["custom"] == "data"


class TestGoogleAdsExtract:
    """Tests for main extract method."""

    def test_extract_default_level(self, extractor):
        """Test extract with default level (campaign)."""
        mock_service = MagicMock()
        mock_service.search.return_value = []

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date))

        # Verify the query was for campaigns
        call_args = mock_service.search.call_args
        assert "FROM campaign" in call_args[1]["query"]

    def test_extract_with_level(self, extractor):
        """Test extract with specified level."""
        mock_service = MagicMock()
        mock_service.search.return_value = []

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date, level="adgroup"))

        call_args = mock_service.search.call_args
        assert "FROM ad_group" in call_args[1]["query"]

    def test_extract_with_custom_query(self, extractor):
        """Test extract with custom query."""
        mock_service = MagicMock()
        mock_service.search.return_value = []

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        custom_query = "SELECT campaign.id FROM campaign LIMIT 5"

        list(extractor.extract(start_date, end_date, custom_query=custom_query))

        call_args = mock_service.search.call_args
        assert "LIMIT 5" in call_args[1]["query"]


class TestGoogleAdsAccessibleCustomers:
    """Tests for listing accessible customers."""

    def test_get_accessible_customers(self, extractor):
        """Test getting list of accessible customers."""
        mock_response = MagicMock()
        mock_response.resource_names = [
            "customers/1234567890",
            "customers/9876543210",
        ]

        mock_service = MagicMock()
        mock_service.list_accessible_customers.return_value = mock_response

        mock_client = MagicMock()
        mock_client.get_service.return_value = mock_service
        extractor._google_ads_client = mock_client
        extractor._authenticated = True

        results = extractor.get_accessible_customers()

        assert len(results) == 2
        assert results[0]["customer_id"] == "1234567890"
        assert results[1]["customer_id"] == "9876543210"
