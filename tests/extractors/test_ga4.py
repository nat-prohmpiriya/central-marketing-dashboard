"""Tests for GA4 extractor."""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# Mock google.analytics module before importing GA4Extractor
mock_ga4_types = MagicMock()
mock_ga4_types.DateRange = MagicMock
mock_ga4_types.Dimension = MagicMock
mock_ga4_types.Metric = MagicMock
mock_ga4_types.RunReportRequest = MagicMock
mock_ga4_types.RunRealtimeReportRequest = MagicMock
mock_ga4_types.GetMetadataRequest = MagicMock

sys.modules["google"] = MagicMock()
sys.modules["google.analytics"] = MagicMock()
sys.modules["google.analytics.data_v1beta"] = MagicMock()
sys.modules["google.analytics.data_v1beta.types"] = mock_ga4_types

from src.extractors.ga4 import GA4Extractor


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    with patch("src.extractors.ga4.get_settings") as mock_ga4, \
         patch("src.extractors.base.get_settings") as mock_base, \
         patch("src.extractors.base.get_rate_limits") as mock_rate:
        settings = MagicMock()
        settings.ga4_property_id = "123456789"
        settings.ga4_credentials_path = ""
        mock_ga4.return_value = settings
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
    return GA4Extractor()


class TestGA4ExtractorInit:
    """Tests for extractor initialization."""

    def test_init_with_settings(self, extractor, mock_settings):
        """Test initialization with settings."""
        assert extractor.property_id == "properties/123456789"

    def test_init_with_custom_property_id(self, mock_settings):
        """Test initialization with custom property ID."""
        extractor = GA4Extractor(property_id="987654321")
        assert extractor.property_id == "properties/987654321"

    def test_init_with_properties_prefix(self, mock_settings):
        """Test initialization preserves properties/ prefix."""
        extractor = GA4Extractor(property_id="properties/111222333")
        assert extractor.property_id == "properties/111222333"

    def test_init_with_credentials_path(self, mock_settings):
        """Test initialization with credentials path."""
        extractor = GA4Extractor(credentials_path="/path/to/creds.json")
        assert extractor.credentials_path == "/path/to/creds.json"


class TestGA4Authentication:
    """Tests for authentication."""

    def test_authenticate_missing_property_id(self):
        """Test authentication fails without property_id."""
        with patch("src.extractors.ga4.get_settings") as mock_ga4, \
             patch("src.extractors.base.get_settings") as mock_base, \
             patch("src.extractors.base.get_rate_limits") as mock_rate:
            settings = MagicMock()
            settings.ga4_property_id = ""
            settings.ga4_credentials_path = ""
            mock_ga4.return_value = settings
            mock_base.return_value = settings
            mock_rate.return_value = {"requests_per_minute": 60}

            extractor = GA4Extractor()

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "No property_id specified" in str(exc_info.value)

    def test_authenticate_sdk_not_installed(self, extractor):
        """Test authentication fails when SDK not installed."""
        with patch.object(extractor, "_init_client") as mock_init:
            mock_init.side_effect = ImportError("No module named 'google.analytics'")

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError):
                extractor.authenticate()

    def test_authenticate_credentials_file_not_found(self, mock_settings):
        """Test authentication fails when credentials file not found."""
        extractor = GA4Extractor(credentials_path="/nonexistent/path.json")

        with patch("src.extractors.ga4.os.path.exists", return_value=False):
            with patch.object(extractor, "_init_client") as mock_init:
                from src.extractors.base import AuthenticationError
                mock_init.side_effect = AuthenticationError(
                    message="Credentials file not found",
                    platform="ga4",
                )

                with pytest.raises(AuthenticationError) as exc_info:
                    extractor.authenticate()
                assert "Credentials file not found" in str(exc_info.value)

    def test_authenticate_success(self, extractor):
        """Test successful authentication."""
        mock_response = MagicMock()
        mock_response.rows = []

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response

        with patch.object(extractor, "_init_client"):
            extractor._analytics_client = mock_client

            result = extractor.authenticate()

            assert result is True
            assert extractor._authenticated is True

    def test_authenticate_permission_denied(self, extractor):
        """Test authentication with permission denied."""
        with patch.object(extractor, "_init_client"):
            extractor._analytics_client = MagicMock()
            extractor._analytics_client.run_report.side_effect = Exception(
                "403 Permission denied"
            )

            from src.extractors.base import AuthenticationError
            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()
            assert "Access denied" in str(exc_info.value)


class TestGA4ExtractTrafficReport:
    """Tests for traffic report extraction."""

    def test_extract_traffic_report_success(self, extractor):
        """Test successful traffic report extraction."""
        mock_row = MagicMock()
        mock_row.dimension_values = [
            MagicMock(value="2024-01-01"),
            MagicMock(value="google"),
            MagicMock(value="organic"),
            MagicMock(value="(not set)"),
        ]
        mock_row.metric_values = [
            MagicMock(value="100"),
            MagicMock(value="80"),
            MagicMock(value="60"),
            MagicMock(value="0.4"),
            MagicMock(value="120.5"),
            MagicMock(value="0.65"),
        ]

        mock_response = MagicMock()
        mock_response.rows = [mock_row]

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_traffic_report(start_date, end_date))

        assert len(results) == 1
        assert results[0]["type"] == "traffic"
        assert results[0]["platform"] == "ga4"
        assert results[0]["data"]["dimensions"]["date"] == "2024-01-01"
        assert results[0]["data"]["dimensions"]["sessionSource"] == "google"


class TestGA4ExtractEcommerceReport:
    """Tests for ecommerce report extraction."""

    def test_extract_ecommerce_report_success(self, extractor):
        """Test successful ecommerce report extraction."""
        mock_row = MagicMock()
        mock_row.dimension_values = [
            MagicMock(value="2024-01-01"),
            MagicMock(value="google"),
            MagicMock(value="cpc"),
        ]
        mock_row.metric_values = [
            MagicMock(value="100"),
            MagicMock(value="10"),
            MagicMock(value="1000.00"),
            MagicMock(value="100.00"),
            MagicMock(value="500"),
            MagicMock(value="50"),
        ]

        mock_response = MagicMock()
        mock_response.rows = [mock_row]

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_ecommerce_report(start_date, end_date))

        assert len(results) == 1
        assert results[0]["type"] == "ecommerce"


class TestGA4ExtractPageReport:
    """Tests for page report extraction."""

    def test_extract_page_report_success(self, extractor):
        """Test successful page report extraction."""
        mock_row = MagicMock()
        mock_row.dimension_values = [
            MagicMock(value="2024-01-01"),
            MagicMock(value="/products"),
            MagicMock(value="Products Page"),
        ]
        mock_row.metric_values = [
            MagicMock(value="500"),
            MagicMock(value="400"),
            MagicMock(value="0.3"),
            MagicMock(value="180.0"),
            MagicMock(value="0.7"),
        ]

        mock_response = MagicMock()
        mock_response.rows = [mock_row]

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_page_report(start_date, end_date))

        assert len(results) == 1
        assert results[0]["type"] == "pages"
        assert results[0]["data"]["dimensions"]["pagePath"] == "/products"


class TestGA4ExtractCustomReport:
    """Tests for custom report extraction."""

    def test_extract_custom_report_success(self, extractor):
        """Test successful custom report extraction."""
        mock_row = MagicMock()
        mock_row.dimension_values = [MagicMock(value="2024-01-01")]
        mock_row.metric_values = [MagicMock(value="1000")]

        mock_response = MagicMock()
        mock_response.rows = [mock_row, mock_row]

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        results = list(extractor.extract_custom_report(
            start_date, end_date,
            dimensions=["date"],
            metrics=["sessions"],
        ))

        assert len(results) == 2
        assert results[0]["type"] == "custom"

    def test_extract_custom_report_api_error(self, extractor):
        """Test API error during custom report extraction."""
        mock_client = MagicMock()
        mock_client.run_report.side_effect = Exception("API Error")
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        from src.extractors.base import APIError
        with pytest.raises(APIError) as exc_info:
            list(extractor.extract_custom_report(
                start_date, end_date,
                dimensions=["date"],
                metrics=["sessions"],
            ))
        assert "Failed to run report" in str(exc_info.value)


class TestGA4ExtractRealtime:
    """Tests for realtime data extraction."""

    def test_extract_realtime_success(self, extractor):
        """Test successful realtime extraction."""
        mock_row = MagicMock()
        mock_row.dimension_values = [
            MagicMock(value="Thailand"),
            MagicMock(value="Bangkok"),
        ]
        mock_row.metric_values = [MagicMock(value="50")]

        mock_response = MagicMock()
        mock_response.rows = [mock_row]

        mock_client = MagicMock()
        mock_client.run_realtime_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_realtime())

        assert len(results) == 1
        assert results[0]["type"] == "realtime"
        assert results[0]["data"]["dimensions"]["country"] == "Thailand"

    def test_extract_realtime_with_custom_dimensions(self, extractor):
        """Test realtime extraction with custom dimensions."""
        mock_row = MagicMock()
        mock_row.dimension_values = [MagicMock(value="mobile")]
        mock_row.metric_values = [MagicMock(value="100")]

        mock_response = MagicMock()
        mock_response.rows = [mock_row]

        mock_client = MagicMock()
        mock_client.run_realtime_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        results = list(extractor.extract_realtime(
            dimensions=["deviceCategory"],
            metrics=["activeUsers"],
        ))

        assert len(results) == 1
        assert results[0]["data"]["dimensions"]["deviceCategory"] == "mobile"


class TestGA4Extract:
    """Tests for main extract method."""

    def test_extract_default_traffic(self, extractor):
        """Test extract with default report type (traffic)."""
        mock_response = MagicMock()
        mock_response.rows = []

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date))

        # Verify run_report was called
        mock_client.run_report.assert_called_once()

    def test_extract_ecommerce_type(self, extractor):
        """Test extract with ecommerce report type."""
        mock_response = MagicMock()
        mock_response.rows = []

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(start_date, end_date, report_type="ecommerce"))

        mock_client.run_report.assert_called_once()

    def test_extract_custom_type(self, extractor):
        """Test extract with custom report type."""
        mock_response = MagicMock()
        mock_response.rows = []

        mock_client = MagicMock()
        mock_client.run_report.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        list(extractor.extract(
            start_date, end_date,
            report_type="custom",
            dimensions=["country"],
            metrics=["activeUsers"],
        ))

        mock_client.run_report.assert_called_once()

    def test_extract_invalid_report_type(self, extractor):
        """Test extract with invalid report type."""
        extractor._authenticated = True

        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

        with pytest.raises(ValueError) as exc_info:
            list(extractor.extract(start_date, end_date, report_type="invalid"))
        assert "Invalid report_type" in str(exc_info.value)


class TestGA4GetMetadata:
    """Tests for metadata retrieval."""

    def test_get_metadata_success(self, extractor):
        """Test successful metadata retrieval."""
        mock_dimension = MagicMock()
        mock_dimension.api_name = "date"
        mock_dimension.ui_name = "Date"

        mock_metric = MagicMock()
        mock_metric.api_name = "sessions"
        mock_metric.ui_name = "Sessions"

        mock_response = MagicMock()
        mock_response.dimensions = [mock_dimension]
        mock_response.metrics = [mock_metric]

        mock_client = MagicMock()
        mock_client.get_metadata.return_value = mock_response
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        result = extractor.get_metadata()

        assert "dimensions" in result
        assert "metrics" in result
        assert result["dimensions"][0]["api_name"] == "date"
        assert result["metrics"][0]["api_name"] == "sessions"

    def test_get_metadata_api_error(self, extractor):
        """Test API error during metadata retrieval."""
        mock_client = MagicMock()
        mock_client.get_metadata.side_effect = Exception("API Error")
        extractor._analytics_client = mock_client
        extractor._authenticated = True

        from src.extractors.base import APIError
        with pytest.raises(APIError) as exc_info:
            extractor.get_metadata()
        assert "Failed to get metadata" in str(exc_info.value)
