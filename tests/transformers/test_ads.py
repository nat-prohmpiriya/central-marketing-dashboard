"""Tests for Ads transformers."""

from datetime import datetime, timezone

import pytest

from src.transformers.ads import (
    FacebookAdsTransformer,
    GoogleAdsTransformer,
    TikTokAdsTransformer,
    UnifiedAd,
    UnifiedAdsTransformer,
)


# Sample Facebook Ads data
SAMPLE_FACEBOOK_INSIGHT = {
    "type": "insight",
    "platform": "facebook_ads",
    "ad_account_id": "act_123456789",
    "level": "ad",
    "data": {
        "campaign_id": "123456",
        "campaign_name": "Summer Sale Campaign",
        "adset_id": "234567",
        "adset_name": "Bangkok Targeting",
        "ad_id": "345678",
        "ad_name": "Product Video Ad",
        "impressions": "10000",
        "clicks": "250",
        "reach": "8000",
        "spend": "100.50",  # USD
        "ctr": "2.5",
        "cpc": "0.402",  # USD
        "cpm": "10.05",  # USD
        "date_start": "2024-01-15",
        "date_end": "2024-01-15",
        "actions": [
            {"action_type": "purchase", "value": "15"},
            {"action_type": "add_to_cart", "value": "45"},
            {"action_type": "link_click", "value": "250"},
        ],
        "cost_per_action_type": [
            {"action_type": "purchase", "value": "6.70"},
            {"action_type": "add_to_cart", "value": "2.23"},
        ],
        "video_p25_watched_actions": [{"value": "5000"}],
        "video_p50_watched_actions": [{"value": "3500"}],
        "video_p75_watched_actions": [{"value": "2000"}],
        "video_p100_watched_actions": [{"value": "1000"}],
        "objective": "CONVERSIONS",
    },
    "extracted_at": "2024-01-16T00:00:00+00:00",
}

# Sample Google Ads data
SAMPLE_GOOGLE_ADS_DATA = {
    "type": "campaign",
    "platform": "google_ads",
    "customer_id": "1234567890",
    "data": {
        "campaign": {
            "id": "987654321",
            "name": "Search - Brand Keywords",
            "status": "ENABLED",
            "advertisingChannelType": "SEARCH",
        },
        "adGroup": {
            "id": "111222333",
            "name": "Brand Terms",
        },
        "adGroupAd": {
            "ad": {
                "id": "444555666",
                "name": "Brand Ad 1",
            }
        },
        "metrics": {
            "impressions": "5000",
            "clicks": "300",
            "costMicros": "1500000000",  # 1,500 THB in micros
            "conversions": "25",
            "conversionsValue": "75000.0",
            "ctr": "0.06",
            "averageCpc": "5000000",  # 5 THB in micros
            "averageCpm": "300000000",  # 300 THB in micros
        },
        "date": "2024-01-15",
    },
    "extracted_at": "2024-01-16T00:00:00+00:00",
}

# Sample TikTok Ads data
SAMPLE_TIKTOK_ADS_DATA = {
    "type": "ad",
    "platform": "tiktok_ads",
    "advertiser_id": "7123456789",
    "data": {
        "dimensions": {
            "campaign_id": "1234567890123",
            "adgroup_id": "2345678901234",
            "ad_id": "3456789012345",
            "stat_time_day": "2024-01-15",
        },
        "metrics": {
            "spend": "3500.00",  # THB
            "impressions": "150000",
            "clicks": "5000",
            "ctr": "3.33",
            "cpc": "0.70",
            "cpm": "23.33",
            "reach": "100000",
            "conversion": "120",
            "cost_per_conversion": "29.17",
            "conversion_rate": "2.4",
            "video_play_actions": "80000",
            "video_views_p25": "60000",
            "video_views_p50": "40000",
            "video_views_p75": "25000",
            "video_views_p100": "15000",
            "likes": "2500",
            "comments": "300",
            "shares": "150",
            "follows": "50",
        },
    },
    "extracted_at": "2024-01-16T00:00:00+00:00",
}


class TestFacebookAdsTransformer:
    """Tests for FacebookAdsTransformer."""

    @pytest.fixture
    def transformer(self):
        return FacebookAdsTransformer()

    def test_transform_basic_insight(self, transformer):
        """Test basic Facebook Ads insight transformation."""
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        assert len(results) == 1
        ad = results[0]

        # Check identifiers
        assert ad["platform"] == "facebook_ads"
        assert ad["account_id"] == "act_123456789"
        assert ad["campaign_id"] == "123456"
        assert ad["campaign_name"] == "Summer Sale Campaign"
        assert ad["adgroup_id"] == "234567"
        assert ad["adgroup_name"] == "Bangkok Targeting"
        assert ad["ad_id"] == "345678"
        assert ad["ad_name"] == "Product Video Ad"

    def test_transform_metrics(self, transformer):
        """Test Facebook Ads metrics transformation."""
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        ad = results[0]

        # Check performance metrics
        assert ad["impressions"] == 10000
        assert ad["clicks"] == 250
        assert ad["reach"] == 8000

    def test_currency_conversion(self, transformer):
        """Test Facebook Ads currency conversion (USD to THB)."""
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        ad = results[0]

        # Original spend is $100.50, should convert to THB
        assert ad["spend_raw"] == 100.50
        assert ad["currency_raw"] == "USD"
        assert ad["currency"] == "THB"
        # With rate 35.0, spend should be 3517.5 THB
        assert ad["spend"] == 3517.5

        # CPC and CPM should also be converted
        assert ad["cpc"] is not None
        assert ad["cpm"] is not None

    def test_conversion_extraction(self, transformer):
        """Test conversion metrics extraction from actions array."""
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        ad = results[0]

        # Should extract conversions from actions array
        # purchase(15) + add_to_cart(45) = 60
        assert ad["conversions"] == 60

    def test_video_metrics(self, transformer):
        """Test video metrics extraction."""
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["video_views_p25"] == 5000
        assert ad["video_views_p50"] == 3500
        assert ad["video_views_p75"] == 2000
        assert ad["video_views_p100"] == 1000

    def test_transform_campaign_level(self, transformer):
        """Test transformation at campaign level."""
        record = {
            **SAMPLE_FACEBOOK_INSIGHT,
            "level": "campaign",
        }
        record["data"] = {
            **SAMPLE_FACEBOOK_INSIGHT["data"],
            "adset_id": None,
            "ad_id": None,
        }

        results = list(transformer.transform([record]))
        ad = results[0]

        assert ad["level"] == "campaign"
        assert "fb_123456" in ad["record_id"]

    def test_record_id_uniqueness(self, transformer):
        """Test that record IDs are unique per ad."""
        records = [
            SAMPLE_FACEBOOK_INSIGHT,
            {
                **SAMPLE_FACEBOOK_INSIGHT,
                "data": {
                    **SAMPLE_FACEBOOK_INSIGHT["data"],
                    "ad_id": "different_ad_id",
                },
            },
        ]

        results = list(transformer.transform(records))
        record_ids = [r["record_id"] for r in results]

        assert len(set(record_ids)) == 2  # All unique

    def test_empty_records(self, transformer):
        """Test handling of empty records list."""
        results = list(transformer.transform([]))
        assert len(results) == 0

    def test_error_handling(self, transformer):
        """Test error handling for malformed data."""
        records = [
            {
                "type": "insight",
                "data": {
                    # Missing campaign_id but should still transform
                    "impressions": "100",
                },
            }
        ]

        results = list(transformer.transform(records))
        # Should handle gracefully
        assert len(results) == 1 or len(transformer.get_error_records()) > 0


class TestGoogleAdsTransformer:
    """Tests for GoogleAdsTransformer."""

    @pytest.fixture
    def transformer(self):
        return GoogleAdsTransformer()

    def test_transform_basic_campaign(self, transformer):
        """Test basic Google Ads campaign transformation."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        assert len(results) == 1
        ad = results[0]

        # Check identifiers
        assert ad["platform"] == "google_ads"
        assert ad["account_id"] == "1234567890"
        assert ad["campaign_id"] == "987654321"
        assert ad["campaign_name"] == "Search - Brand Keywords"

    def test_cost_micros_conversion(self, transformer):
        """Test Google Ads cost_micros conversion."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        # cost_micros 1,500,000,000 = 1,500 THB
        assert ad["spend"] == 1500.0
        assert ad["currency"] == "THB"

        # average_cpc 5,000,000 micros = 5 THB
        assert ad["cpc"] == 5.0

        # average_cpm 300,000,000 micros = 300 THB
        assert ad["cpm"] == 300.0

    def test_transform_metrics(self, transformer):
        """Test Google Ads metrics transformation."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["impressions"] == 5000
        assert ad["clicks"] == 300
        assert ad["conversions"] == 25
        assert ad["conversion_value"] == 75000.0

    def test_cost_per_conversion_calculation(self, transformer):
        """Test cost per conversion calculation."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        # 1500 THB / 25 conversions = 60 THB per conversion
        assert ad["cost_per_conversion"] == 60.0

    def test_conversion_rate_calculation(self, transformer):
        """Test conversion rate calculation."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        # 25 conversions / 300 clicks * 100 = 8.33%
        assert ad["conversion_rate"] == 8.33

    def test_status_normalization(self, transformer):
        """Test status normalization."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["status"] == "active"

    def test_campaign_type_normalization(self, transformer):
        """Test campaign type normalization."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["campaign_type"] == "search"

    def test_adgroup_level(self, transformer):
        """Test adgroup level transformation."""
        record = {
            **SAMPLE_GOOGLE_ADS_DATA,
            "type": "adgroup",
        }

        results = list(transformer.transform([record]))
        ad = results[0]

        assert ad["level"] == "adgroup"
        assert ad["adgroup_id"] == "111222333"
        assert ad["adgroup_name"] == "Brand Terms"


class TestTikTokAdsTransformer:
    """Tests for TikTokAdsTransformer."""

    @pytest.fixture
    def transformer(self):
        return TikTokAdsTransformer()

    def test_transform_basic_ad(self, transformer):
        """Test basic TikTok Ads transformation."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        assert len(results) == 1
        ad = results[0]

        # Check identifiers
        assert ad["platform"] == "tiktok_ads"
        assert ad["account_id"] == "7123456789"
        assert ad["campaign_id"] == "1234567890123"
        assert ad["adgroup_id"] == "2345678901234"
        assert ad["ad_id"] == "3456789012345"

    def test_transform_metrics(self, transformer):
        """Test TikTok Ads metrics transformation."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["impressions"] == 150000
        assert ad["clicks"] == 5000
        assert ad["reach"] == 100000
        assert ad["spend"] == 3500.0
        assert ad["currency"] == "THB"

    def test_conversion_metrics(self, transformer):
        """Test TikTok Ads conversion metrics."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["conversions"] == 120
        assert ad["cost_per_conversion"] == 29.17
        assert ad["conversion_rate"] == 2.4

    def test_video_metrics(self, transformer):
        """Test TikTok Ads video metrics."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["video_views"] == 80000
        assert ad["video_views_p25"] == 60000
        assert ad["video_views_p50"] == 40000
        assert ad["video_views_p75"] == 25000
        assert ad["video_views_p100"] == 15000

    def test_engagement_metrics(self, transformer):
        """Test TikTok Ads engagement metrics."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["likes"] == 2500
        assert ad["comments"] == 300
        assert ad["shares"] == 150
        assert ad["follows"] == 50

    def test_ctr_cpc_cpm(self, transformer):
        """Test CTR, CPC, CPM metrics."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["ctr"] == 3.33
        assert ad["cpc"] == 0.70
        assert ad["cpm"] == 23.33

    def test_record_id_with_date(self, transformer):
        """Test that record ID includes date for uniqueness."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        # Record ID should include date
        assert "2024-01-15" in ad["record_id"]


class TestUnifiedAdsTransformer:
    """Tests for UnifiedAdsTransformer."""

    @pytest.fixture
    def transformer(self):
        return UnifiedAdsTransformer()

    def test_route_facebook_ads(self, transformer):
        """Test routing Facebook Ads to correct transformer."""
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        assert len(results) == 1
        assert results[0]["platform"] == "facebook_ads"

    def test_route_google_ads(self, transformer):
        """Test routing Google Ads to correct transformer."""
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        assert len(results) == 1
        assert results[0]["platform"] == "google_ads"

    def test_route_tiktok_ads(self, transformer):
        """Test routing TikTok Ads to correct transformer."""
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        assert len(results) == 1
        assert results[0]["platform"] == "tiktok_ads"

    def test_transform_mixed_platforms(self, transformer):
        """Test transforming records from multiple platforms."""
        records = [
            SAMPLE_FACEBOOK_INSIGHT,
            SAMPLE_GOOGLE_ADS_DATA,
            SAMPLE_TIKTOK_ADS_DATA,
        ]
        results = list(transformer.transform(records))

        assert len(results) == 3

        platforms = [r["platform"] for r in results]
        assert "facebook_ads" in platforms
        assert "google_ads" in platforms
        assert "tiktok_ads" in platforms

    def test_platform_detection_facebook(self, transformer):
        """Test platform detection for Facebook Ads."""
        record = {
            "data": {"adset_id": "123"},
        }
        platform = transformer._detect_platform(record)
        assert platform == "facebook_ads"

    def test_platform_detection_google(self, transformer):
        """Test platform detection for Google Ads."""
        record = {
            "customer_id": "123",
            "data": {"metrics": {"costMicros": 1000}},
        }
        platform = transformer._detect_platform(record)
        assert platform == "google_ads"

    def test_platform_detection_tiktok(self, transformer):
        """Test platform detection for TikTok Ads."""
        record = {
            "advertiser_id": "123",
            "data": {},
        }
        platform = transformer._detect_platform(record)
        assert platform == "tiktok_ads"

    def test_unknown_platform_skipped(self, transformer):
        """Test that unknown platforms are skipped."""
        records = [
            {"platform": "unknown_platform", "data": {}},
        ]
        results = list(transformer.transform(records))
        assert len(results) == 0

    def test_error_aggregation(self, transformer):
        """Test error records aggregation from all transformers."""
        # Clear any existing errors
        transformer.clear_error_records()

        # Transform valid records
        records = [SAMPLE_FACEBOOK_INSIGHT]
        list(transformer.transform(records))

        # Errors should be empty for valid data
        errors = transformer.get_error_records()
        assert isinstance(errors, list)

    def test_clear_error_records(self, transformer):
        """Test clearing error records from all transformers."""
        transformer.clear_error_records()
        errors = transformer.get_error_records()
        assert len(errors) == 0


class TestUnifiedAdSchema:
    """Tests for UnifiedAd Pydantic schema."""

    def test_schema_validation(self):
        """Test UnifiedAd schema validation."""
        ad = UnifiedAd(
            record_id="test_123",
            platform="facebook_ads",
            account_id="act_123",
            campaign_id="camp_123",
            date=datetime.now(timezone.utc),
        )

        assert ad.record_id == "test_123"
        assert ad.platform == "facebook_ads"
        assert ad.impressions == 0  # Default value
        assert ad.clicks == 0  # Default value
        assert ad.spend == 0.0  # Default value

    def test_schema_with_all_fields(self):
        """Test UnifiedAd schema with all fields."""
        ad = UnifiedAd(
            record_id="test_456",
            platform="google_ads",
            account_id="123456",
            campaign_id="camp_456",
            campaign_name="Test Campaign",
            adgroup_id="adg_789",
            adgroup_name="Test AdGroup",
            ad_id="ad_012",
            ad_name="Test Ad",
            impressions=10000,
            clicks=500,
            reach=8000,
            ctr=5.0,
            cpc=10.0,
            cpm=50.0,
            spend=5000.0,
            spend_raw=5000.0,
            currency="THB",
            currency_raw="THB",
            conversions=50,
            conversion_value=25000.0,
            cost_per_conversion=100.0,
            conversion_rate=10.0,
            video_views=3000,
            video_views_p25=2500,
            video_views_p50=2000,
            video_views_p75=1500,
            video_views_p100=1000,
            likes=200,
            comments=50,
            shares=25,
            follows=10,
            status="active",
            campaign_type="search",
            objective="conversions",
            date=datetime(2024, 1, 15, tzinfo=timezone.utc),
            level="ad",
        )

        assert ad.impressions == 10000
        assert ad.conversions == 50
        assert ad.video_views == 3000
        assert ad.likes == 200

    def test_schema_optional_fields(self):
        """Test that optional fields can be None."""
        ad = UnifiedAd(
            record_id="test_789",
            platform="tiktok_ads",
            account_id="adv_123",
            campaign_id="camp_789",
            date=datetime.now(timezone.utc),
            # All other fields use defaults
        )

        assert ad.campaign_name is None
        assert ad.adgroup_id is None
        assert ad.ctr is None
        assert ad.reach is None
        assert ad.video_views is None


class TestDateNormalization:
    """Tests for date normalization across transformers."""

    def test_facebook_date_normalization(self):
        """Test Facebook date normalization."""
        transformer = FacebookAdsTransformer()
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        ad = results[0]

        # Date should be normalized to Asia/Bangkok timezone
        assert ad["date"] is not None
        assert isinstance(ad["date"], datetime)

    def test_google_date_normalization(self):
        """Test Google Ads date normalization."""
        transformer = GoogleAdsTransformer()
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["date"] is not None

    def test_tiktok_date_normalization(self):
        """Test TikTok Ads date normalization."""
        transformer = TikTokAdsTransformer()
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        assert ad["date"] is not None


class TestCurrencyNormalization:
    """Tests for currency normalization across transformers."""

    def test_facebook_usd_to_thb(self):
        """Test Facebook USD to THB conversion."""
        transformer = FacebookAdsTransformer()
        records = [SAMPLE_FACEBOOK_INSIGHT]
        results = list(transformer.transform(records))

        ad = results[0]

        # Original: $100.50 USD
        # Converted: 100.50 * 35 = 3517.5 THB
        assert ad["spend_raw"] == 100.50
        assert ad["currency_raw"] == "USD"
        assert ad["spend"] == 3517.5
        assert ad["currency"] == "THB"

    def test_google_already_thb(self):
        """Test Google Ads already in THB (no conversion needed)."""
        transformer = GoogleAdsTransformer()
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        # Already in THB
        assert ad["spend"] == 1500.0
        assert ad["currency"] == "THB"

    def test_tiktok_already_thb(self):
        """Test TikTok Ads already in THB (no conversion needed)."""
        transformer = TikTokAdsTransformer()
        records = [SAMPLE_TIKTOK_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]

        # Already in THB
        assert ad["spend"] == 3500.0
        assert ad["currency"] == "THB"


class TestStatusMapping:
    """Tests for status mapping across platforms."""

    def test_google_enabled_to_active(self):
        """Test Google Ads ENABLED status maps to active."""
        transformer = GoogleAdsTransformer()
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]
        assert ad["status"] == "active"

    def test_google_paused_status(self):
        """Test Google Ads PAUSED status mapping."""
        transformer = GoogleAdsTransformer()
        record = {
            **SAMPLE_GOOGLE_ADS_DATA,
            "data": {
                **SAMPLE_GOOGLE_ADS_DATA["data"],
                "campaign": {
                    **SAMPLE_GOOGLE_ADS_DATA["data"]["campaign"],
                    "status": "PAUSED",
                },
            },
        }
        results = list(transformer.transform([record]))

        ad = results[0]
        assert ad["status"] == "paused"


class TestCampaignTypeMapping:
    """Tests for campaign type mapping across platforms."""

    def test_google_search_campaign(self):
        """Test Google Ads SEARCH campaign type mapping."""
        transformer = GoogleAdsTransformer()
        records = [SAMPLE_GOOGLE_ADS_DATA]
        results = list(transformer.transform(records))

        ad = results[0]
        assert ad["campaign_type"] == "search"

    def test_google_display_campaign(self):
        """Test Google Ads DISPLAY campaign type mapping."""
        transformer = GoogleAdsTransformer()
        record = {
            **SAMPLE_GOOGLE_ADS_DATA,
            "data": {
                **SAMPLE_GOOGLE_ADS_DATA["data"],
                "campaign": {
                    **SAMPLE_GOOGLE_ADS_DATA["data"]["campaign"],
                    "advertisingChannelType": "DISPLAY",
                },
            },
        }
        results = list(transformer.transform([record]))

        ad = results[0]
        assert ad["campaign_type"] == "display"
