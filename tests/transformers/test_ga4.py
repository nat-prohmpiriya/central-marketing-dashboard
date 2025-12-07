"""Tests for GA4 transformers."""

from datetime import datetime, timezone

import pytest

from src.transformers.ga4 import (
    GA4Page,
    GA4PagesTransformer,
    GA4Session,
    GA4SessionsTransformer,
    GA4Traffic,
    GA4TrafficTransformer,
    UnifiedGA4Transformer,
    get_channel_grouping,
)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_traffic_record():
    """Sample GA4 traffic report record."""
    return {
        "type": "traffic",
        "platform": "ga4",
        "property_id": "properties/123456789",
        "data": {
            "dimensions": {
                "date": "20241201",
                "sessionSource": "google",
                "sessionMedium": "organic",
                "sessionCampaignName": "(not set)",
            },
            "metrics": {
                "sessions": "1500",
                "totalUsers": "1200",
                "newUsers": "800",
                "bounceRate": "0.45",
                "averageSessionDuration": "180.5",
                "engagementRate": "0.65",
            },
        },
        "extracted_at": "2024-12-01T10:00:00Z",
    }


@pytest.fixture
def sample_ecommerce_record():
    """Sample GA4 ecommerce report record."""
    return {
        "type": "ecommerce",
        "platform": "ga4",
        "property_id": "properties/123456789",
        "data": {
            "dimensions": {
                "date": "20241201",
                "sessionSource": "facebook",
                "sessionMedium": "cpc",
            },
            "metrics": {
                "sessions": "500",
                "totalUsers": "450",
                "newUsers": "300",
                "transactions": "25",
                "purchaseRevenue": "125000.50",
                "bounceRate": "0.35",
                "engagementRate": "0.75",
                "averageSessionDuration": "240.0",
            },
        },
        "extracted_at": "2024-12-01T10:00:00Z",
    }


@pytest.fixture
def sample_pages_record():
    """Sample GA4 pages report record."""
    return {
        "type": "pages",
        "platform": "ga4",
        "property_id": "properties/123456789",
        "data": {
            "dimensions": {
                "date": "20241201",
                "pagePath": "/products/item-123",
                "pageTitle": "Product Detail - Item 123",
            },
            "metrics": {
                "screenPageViews": "5000",
                "sessions": "3000",
                "bounceRate": "0.25",
                "engagementRate": "0.85",
                "averageSessionDuration": "120.0",
                "entrances": "2500",
                "exits": "1500",
            },
        },
        "extracted_at": "2024-12-01T10:00:00Z",
    }


@pytest.fixture
def sample_session_record():
    """Sample GA4 session record with engagement metrics."""
    return {
        "type": "traffic",
        "platform": "ga4",
        "property_id": "properties/123456789",
        "data": {
            "dimensions": {
                "date": "20241201",
                "sessionSource": "direct",
                "sessionMedium": "(none)",
            },
            "metrics": {
                "sessions": "2000",
                "engagedSessions": "1600",
                "totalUsers": "1800",
                "newUsers": "500",
                "activeUsers": "1700",
                "screenPageViews": "8000",
                "bounceRate": "0.20",
                "engagementRate": "0.80",
                "averageSessionDuration": "200.0",
                "eventsPerSession": "4.5",
            },
        },
        "extracted_at": "2024-12-01T10:00:00Z",
    }


# =============================================================================
# Channel Grouping Tests
# =============================================================================


class TestChannelGrouping:
    """Tests for channel grouping logic."""

    def test_direct_traffic(self):
        """Test direct traffic channel grouping."""
        assert get_channel_grouping("(direct)", "(none)") == "Direct"
        assert get_channel_grouping("(direct)", "(not set)") == "Direct"

    def test_organic_search(self):
        """Test organic search channel grouping."""
        assert get_channel_grouping("google", "organic") == "Organic Search"
        assert get_channel_grouping("bing", "organic") == "Organic Search"

    def test_paid_search(self):
        """Test paid search channel grouping."""
        assert get_channel_grouping("google", "cpc") == "Paid Search"
        assert get_channel_grouping("google", "ppc") == "Paid Search"
        assert get_channel_grouping("bing", "paidsearch") == "Paid Search"

    def test_display(self):
        """Test display channel grouping."""
        assert get_channel_grouping("google", "display") == "Display"
        assert get_channel_grouping("google", "cpm") == "Display"
        assert get_channel_grouping("gdn", "banner") == "Display"

    def test_social(self):
        """Test social channel grouping."""
        assert get_channel_grouping("facebook", "referral") == "Social"
        assert get_channel_grouping("instagram", "post") == "Social"
        assert get_channel_grouping("twitter", "tweet") == "Social"
        assert get_channel_grouping("tiktok", "video") == "Social"
        assert get_channel_grouping("any", "social") == "Social"

    def test_paid_social(self):
        """Test paid social channel grouping."""
        assert get_channel_grouping("facebook", "paid_social") == "Paid Social"
        assert get_channel_grouping("instagram", "paidsocial") == "Paid Social"

    def test_email(self):
        """Test email channel grouping."""
        assert get_channel_grouping("newsletter", "email") == "Email"
        assert get_channel_grouping("mailchimp", "email") == "Email"

    def test_referral(self):
        """Test referral channel grouping."""
        assert get_channel_grouping("blog.example.com", "referral") == "Referral"

    def test_affiliates(self):
        """Test affiliates channel grouping."""
        assert get_channel_grouping("partner", "affiliate") == "Affiliates"

    def test_other(self):
        """Test other/unknown channel grouping."""
        assert get_channel_grouping("unknown", "unknown") == "Other"
        assert get_channel_grouping("", "") == "Other"
        assert get_channel_grouping(None, None) == "Other"


# =============================================================================
# GA4 Sessions Transformer Tests
# =============================================================================


class TestGA4SessionsTransformer:
    """Tests for GA4SessionsTransformer."""

    def test_transform_session_record(self, sample_session_record):
        """Test transforming a session record."""
        transformer = GA4SessionsTransformer()
        results = list(transformer.transform([sample_session_record]))

        assert len(results) == 1
        result = results[0]

        assert result["property_id"] == "properties/123456789"
        assert result["sessions"] == 2000
        assert result["engaged_sessions"] == 1600
        assert result["total_users"] == 1800
        assert result["new_users"] == 500
        assert result["active_users"] == 1700
        assert result["screen_page_views"] == 8000
        assert result["bounce_rate"] == 0.20
        assert result["engagement_rate"] == 0.80
        assert result["avg_session_duration"] == 200.0
        assert result["events_per_session"] == 4.5
        assert result["channel_grouping"] == "Direct"
        assert result["returning_users"] == 1300  # 1800 - 500

    def test_session_duration_total_calculation(self, sample_session_record):
        """Test total session duration calculation."""
        transformer = GA4SessionsTransformer()
        results = list(transformer.transform([sample_session_record]))

        result = results[0]
        # 200.0 * 2000 = 400000.0
        assert result["session_duration_total"] == 400000.0

    def test_date_parsing_yyyymmdd_format(self, sample_session_record):
        """Test date parsing from YYYYMMDD format."""
        transformer = GA4SessionsTransformer()
        results = list(transformer.transform([sample_session_record]))

        result = results[0]
        assert result["date"].year == 2024
        assert result["date"].month == 12
        assert result["date"].day == 1

    def test_record_id_generation(self, sample_session_record):
        """Test record ID generation."""
        transformer = GA4SessionsTransformer()
        results = list(transformer.transform([sample_session_record]))

        result = results[0]
        assert "ga4_session_" in result["record_id"]
        assert "properties/123456789" in result["record_id"]
        assert "20241201" in result["record_id"]

    def test_not_set_values_converted_to_none(self):
        """Test that (not set) values are converted to None."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "sessionSource": "(not set)",
                    "sessionMedium": "(not set)",
                    "sessionCampaignName": "(not set)",
                },
                "metrics": {
                    "sessions": "100",
                },
            },
        }
        transformer = GA4SessionsTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["source"] is None
        assert result["medium"] is None
        assert result["campaign"] is None

    def test_empty_records(self):
        """Test with empty records list."""
        transformer = GA4SessionsTransformer()
        results = list(transformer.transform([]))
        assert len(results) == 0


# =============================================================================
# GA4 Traffic Transformer Tests
# =============================================================================


class TestGA4TrafficTransformer:
    """Tests for GA4TrafficTransformer."""

    def test_transform_traffic_record(self, sample_traffic_record):
        """Test transforming a traffic record."""
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([sample_traffic_record]))

        assert len(results) == 1
        result = results[0]

        assert result["property_id"] == "properties/123456789"
        assert result["source"] == "google"
        assert result["medium"] == "organic"
        assert result["sessions"] == 1500
        assert result["total_users"] == 1200
        assert result["new_users"] == 800
        assert result["bounce_rate"] == 0.45
        assert result["engagement_rate"] == 0.65
        assert result["channel_grouping"] == "Organic Search"

    def test_transform_ecommerce_record(self, sample_ecommerce_record):
        """Test transforming an ecommerce record with revenue."""
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([sample_ecommerce_record]))

        result = results[0]
        assert result["transactions"] == 25
        assert result["revenue"] == 125000.50
        # AOV = 125000.50 / 25 = 5000.02
        assert result["avg_order_value"] == pytest.approx(5000.02, rel=0.01)
        # Conversion rate = 25/500 * 100 = 5%
        assert result["conversion_rate"] == pytest.approx(5.0, rel=0.01)
        assert result["channel_grouping"] == "Paid Search"

    def test_conversion_rate_zero_sessions(self):
        """Test conversion rate when sessions is zero."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "sessionSource": "google",
                    "sessionMedium": "organic",
                },
                "metrics": {
                    "sessions": "0",
                    "transactions": "0",
                    "purchaseRevenue": "0",
                },
            },
        }
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["conversion_rate"] is None
        assert result["avg_order_value"] is None

    def test_multiple_records(self, sample_traffic_record, sample_ecommerce_record):
        """Test transforming multiple records."""
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([sample_traffic_record, sample_ecommerce_record]))

        assert len(results) == 2
        assert results[0]["channel_grouping"] == "Organic Search"
        assert results[1]["channel_grouping"] == "Paid Search"


# =============================================================================
# GA4 Pages Transformer Tests
# =============================================================================


class TestGA4PagesTransformer:
    """Tests for GA4PagesTransformer."""

    def test_transform_pages_record(self, sample_pages_record):
        """Test transforming a pages record."""
        transformer = GA4PagesTransformer()
        results = list(transformer.transform([sample_pages_record]))

        assert len(results) == 1
        result = results[0]

        assert result["property_id"] == "properties/123456789"
        assert result["page_path"] == "/products/item-123"
        assert result["page_title"] == "Product Detail - Item 123"
        assert result["page_views"] == 5000
        assert result["sessions"] == 3000
        assert result["unique_page_views"] == 3000  # Uses sessions as proxy
        assert result["bounce_rate"] == 0.25
        assert result["engagement_rate"] == 0.85
        assert result["entrances"] == 2500
        assert result["exits"] == 1500

    def test_exit_rate_calculation(self, sample_pages_record):
        """Test exit rate calculation."""
        transformer = GA4PagesTransformer()
        results = list(transformer.transform([sample_pages_record]))

        result = results[0]
        # Exit rate = 1500/5000 * 100 = 30%
        assert result["exit_rate"] == pytest.approx(30.0, rel=0.01)

    def test_exit_rate_zero_pageviews(self):
        """Test exit rate when page views is zero."""
        record = {
            "type": "pages",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "pagePath": "/empty-page",
                },
                "metrics": {
                    "screenPageViews": "0",
                    "sessions": "0",
                    "exits": "0",
                },
            },
        }
        transformer = GA4PagesTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["exit_rate"] is None

    def test_page_path_in_record_id(self, sample_pages_record):
        """Test that page path is included in record ID."""
        transformer = GA4PagesTransformer()
        results = list(transformer.transform([sample_pages_record]))

        result = results[0]
        assert "ga4_page_" in result["record_id"]
        # Path should be cleaned (/ replaced with _)
        assert "_products_item-123" in result["record_id"]

    def test_not_set_page_title(self):
        """Test that (not set) page title is converted to None."""
        record = {
            "type": "pages",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "pagePath": "/page",
                    "pageTitle": "(not set)",
                },
                "metrics": {
                    "screenPageViews": "100",
                },
            },
        }
        transformer = GA4PagesTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["page_title"] is None


# =============================================================================
# Unified GA4 Transformer Tests
# =============================================================================


class TestUnifiedGA4Transformer:
    """Tests for UnifiedGA4Transformer."""

    def test_auto_detect_traffic_type(self, sample_traffic_record):
        """Test auto-detection of traffic report type."""
        transformer = UnifiedGA4Transformer()
        results = list(transformer.transform([sample_traffic_record]))

        assert len(results) == 1
        result = results[0]
        assert "channel_grouping" in result
        assert result["source"] == "google"

    def test_auto_detect_pages_type(self, sample_pages_record):
        """Test auto-detection of pages report type."""
        transformer = UnifiedGA4Transformer()
        results = list(transformer.transform([sample_pages_record]))

        assert len(results) == 1
        result = results[0]
        assert "page_path" in result
        assert result["page_path"] == "/products/item-123"

    def test_auto_detect_ecommerce_type(self, sample_ecommerce_record):
        """Test auto-detection of ecommerce report type (routes to traffic)."""
        transformer = UnifiedGA4Transformer()
        results = list(transformer.transform([sample_ecommerce_record]))

        assert len(results) == 1
        result = results[0]
        assert result["transactions"] == 25
        assert result["revenue"] == 125000.50

    def test_detect_from_dimensions(self):
        """Test report type detection from dimensions when type is missing."""
        pages_record = {
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "pagePath": "/home",
                    "pageTitle": "Home",
                },
                "metrics": {
                    "screenPageViews": "100",
                },
            },
        }
        transformer = UnifiedGA4Transformer()
        results = list(transformer.transform([pages_record]))

        result = results[0]
        assert "page_path" in result

    def test_mixed_record_types(
        self, sample_traffic_record, sample_pages_record, sample_ecommerce_record
    ):
        """Test processing mixed record types."""
        transformer = UnifiedGA4Transformer()
        results = list(
            transformer.transform(
                [sample_traffic_record, sample_pages_record, sample_ecommerce_record]
            )
        )

        assert len(results) == 3
        # Traffic record
        assert results[0]["source"] == "google"
        # Pages record
        assert results[1]["page_path"] == "/products/item-123"
        # Ecommerce record
        assert results[2]["transactions"] == 25

    def test_generator_input(self, sample_traffic_record):
        """Test with generator input."""

        def record_generator():
            yield sample_traffic_record

        transformer = UnifiedGA4Transformer()
        results = list(transformer.transform(record_generator()))

        assert len(results) == 1


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestGA4SessionSchema:
    """Tests for GA4Session Pydantic model."""

    def test_valid_session(self):
        """Test creating a valid session."""
        session = GA4Session(
            record_id="ga4_session_123",
            property_id="properties/123",
            date=datetime.now(timezone.utc),
            sessions=100,
        )
        assert session.sessions == 100
        assert session.transformed_at is not None

    def test_default_values(self):
        """Test default values are applied."""
        session = GA4Session(
            record_id="ga4_session_123",
            property_id="properties/123",
            date=datetime.now(timezone.utc),
        )
        assert session.sessions == 0
        assert session.engaged_sessions == 0
        assert session.total_users == 0
        assert session.new_users == 0
        assert session.returning_users == 0


class TestGA4TrafficSchema:
    """Tests for GA4Traffic Pydantic model."""

    def test_valid_traffic(self):
        """Test creating a valid traffic record."""
        traffic = GA4Traffic(
            record_id="ga4_traffic_123",
            property_id="properties/123",
            date=datetime.now(timezone.utc),
            channel_grouping="Organic Search",
            sessions=500,
        )
        assert traffic.sessions == 500
        assert traffic.channel_grouping == "Organic Search"

    def test_ecommerce_fields(self):
        """Test ecommerce fields."""
        traffic = GA4Traffic(
            record_id="ga4_traffic_123",
            property_id="properties/123",
            date=datetime.now(timezone.utc),
            channel_grouping="Paid Search",
            transactions=10,
            revenue=50000.0,
            avg_order_value=5000.0,
            conversion_rate=2.0,
        )
        assert traffic.transactions == 10
        assert traffic.revenue == 50000.0


class TestGA4PageSchema:
    """Tests for GA4Page Pydantic model."""

    def test_valid_page(self):
        """Test creating a valid page record."""
        page = GA4Page(
            record_id="ga4_page_123",
            property_id="properties/123",
            date=datetime.now(timezone.utc),
            page_path="/home",
            page_views=1000,
        )
        assert page.page_path == "/home"
        assert page.page_views == 1000

    def test_default_values(self):
        """Test default values are applied."""
        page = GA4Page(
            record_id="ga4_page_123",
            property_id="properties/123",
            date=datetime.now(timezone.utc),
            page_path="/",
        )
        assert page.page_views == 0
        assert page.sessions == 0
        assert page.entrances == 0
        assert page.exits == 0


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_missing_data_field(self):
        """Test handling record with missing data field."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
        }
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([record]))

        # Should handle gracefully with defaults
        assert len(results) == 1

    def test_missing_metrics(self):
        """Test handling record with missing metrics."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "sessionSource": "google",
                    "sessionMedium": "organic",
                },
                "metrics": {},
            },
        }
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["sessions"] == 0
        assert result["total_users"] == 0

    def test_invalid_metric_values(self):
        """Test handling invalid metric values."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "sessionSource": "google",
                    "sessionMedium": "organic",
                },
                "metrics": {
                    "sessions": "invalid",
                    "bounceRate": "not_a_number",
                },
            },
        }
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["sessions"] == 0
        assert result["bounce_rate"] is None

    def test_iso_date_format(self):
        """Test handling ISO date format instead of YYYYMMDD."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "2024-12-01T00:00:00Z",
                    "sessionSource": "google",
                    "sessionMedium": "organic",
                },
                "metrics": {
                    "sessions": "100",
                },
            },
        }
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["date"].year == 2024
        assert result["date"].month == 12
        assert result["date"].day == 1

    def test_extracted_at_parsing(self, sample_traffic_record):
        """Test extracted_at timestamp parsing."""
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([sample_traffic_record]))

        result = results[0]
        assert result["extracted_at"] is not None
        assert result["extracted_at"].year == 2024

    def test_missing_extracted_at(self):
        """Test handling missing extracted_at."""
        record = {
            "type": "traffic",
            "property_id": "properties/123",
            "data": {
                "dimensions": {"date": "20241201"},
                "metrics": {"sessions": "100"},
            },
        }
        transformer = GA4TrafficTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["extracted_at"] is None

    def test_special_characters_in_page_path(self):
        """Test handling special characters in page path."""
        record = {
            "type": "pages",
            "property_id": "properties/123",
            "data": {
                "dimensions": {
                    "date": "20241201",
                    "pagePath": "/search?q=test&page=1",
                },
                "metrics": {
                    "screenPageViews": "100",
                },
            },
        }
        transformer = GA4PagesTransformer()
        results = list(transformer.transform([record]))

        result = results[0]
        assert result["page_path"] == "/search?q=test&page=1"
        # Record ID should have special chars replaced
        assert "?" not in result["record_id"]
        assert "&" not in result["record_id"]


# =============================================================================
# Integration with Base Transformer Tests
# =============================================================================


class TestBaseTransformerIntegration:
    """Tests for integration with BaseTransformer functionality."""

    def test_error_records_collection(self):
        """Test that error records are collected."""
        transformer = GA4TrafficTransformer()
        # Should not have any error records initially
        assert len(transformer.get_error_records()) == 0

    def test_clear_error_records(self):
        """Test clearing error records."""
        transformer = GA4TrafficTransformer()
        transformer.clear_error_records()
        assert len(transformer.get_error_records()) == 0

    def test_get_stats(self):
        """Test getting transformer statistics."""
        transformer = GA4TrafficTransformer()
        stats = transformer.get_stats()
        assert "error_count" in stats
        assert stats["error_count"] == 0
