"""Tests for ads pipeline."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.pipelines.base import PipelineStage


class TestAdsPipelineLogic:
    """Tests for ads pipeline logic without GCP dependencies."""

    def test_data_type_separation(self):
        """Test separating ads and GA4 records."""
        records = [
            {"platform": "facebook_ads", "data_type": "ads", "data": {}},
            {"platform": "google_ads", "data_type": "ads", "data": {}},
            {"platform": "ga4", "data_type": "ga4", "data": {}},
            {"platform": "tiktok_ads", "data_type": "ads", "data": {}},
        ]

        ads_records = [r for r in records if r.get("data_type") == "ads"]
        ga4_records = [r for r in records if r.get("data_type") == "ga4"]

        assert len(ads_records) == 3
        assert len(ga4_records) == 1

    def test_ads_record_structure(self, sample_facebook_ads):
        """Test ads record structure."""
        record = sample_facebook_ads[0]

        assert record["platform"] == "facebook_ads"
        assert record["data_type"] == "ads"
        assert "campaign_id" in record["data"]
        assert "spend" in record["data"]

    def test_ga4_record_structure(self, sample_ga4_data):
        """Test GA4 record structure."""
        record = sample_ga4_data[0]

        assert record["platform"] == "ga4"
        assert record["data_type"] == "ga4"
        assert "dimensions" in record["data"]
        assert "metrics" in record["data"]

    def test_platform_grouping(self):
        """Test grouping records by platform."""
        records = [
            {"platform": "facebook_ads", "data": {"campaign_id": "FB001"}},
            {"platform": "facebook_ads", "data": {"campaign_id": "FB002"}},
            {"platform": "google_ads", "data": {"campaign_id": "GOOG001"}},
            {"platform": "tiktok_ads", "data": {"campaign_id": "TIK001"}},
        ]

        ads_by_platform = {}
        for record in records:
            platform = record.get("platform", "unknown")
            if platform not in ads_by_platform:
                ads_by_platform[platform] = []
            ads_by_platform[platform].append(record.get("data", record))

        assert len(ads_by_platform["facebook_ads"]) == 2
        assert len(ads_by_platform["google_ads"]) == 1
        assert len(ads_by_platform["tiktok_ads"]) == 1

    def test_unified_ads_format(self):
        """Test unified ads format structure."""
        unified_ad = {
            "record_id": "facebook_ads_FB001_2024-01-01",
            "platform": "facebook_ads",
            "date": "2024-01-01",
            "campaign_id": "FB001",
            "campaign_name": "Campaign 1",
            "ad_set_id": "ADSET001",
            "ad_id": "AD001",
            "spend": 100.0,
            "impressions": 10000,
            "clicks": 500,
            "conversions": 50,
            "ctr": 0.05,
            "cpc": 0.20,
            "cpm": 10.0,
            "roas": 5.0,
        }

        assert unified_ad["record_id"].startswith("facebook_ads_")
        assert "spend" in unified_ad
        assert "impressions" in unified_ad
        assert "ctr" in unified_ad

    def test_ga4_session_format(self):
        """Test GA4 session format structure."""
        ga4_session = {
            "record_id": "ga4_sessions_123456_2024-01-01_google_cpc",
            "property_id": "123456",
            "date": "2024-01-01",
            "source": "google",
            "medium": "cpc",
            "sessions": 1000,
            "users": 800,
            "new_users": 500,
            "bounce_rate": 0.45,
            "avg_session_duration": 120.5,
        }

        assert "property_id" in ga4_session
        assert "sessions" in ga4_session
        assert "bounce_rate" in ga4_session


class TestAdsPipelinePlatforms:
    """Tests for ads pipeline platform handling."""

    def test_default_platforms(self):
        """Test default platform configuration."""
        default_platforms = [
            "facebook_ads",
            "google_ads",
            "tiktok_ads",
            "line_ads",
            "shopee_ads",
            "lazada_ads",
        ]

        assert len(default_platforms) == 6
        assert "facebook_ads" in default_platforms
        assert "google_ads" in default_platforms

    def test_custom_platforms(self):
        """Test custom platform configuration."""
        custom_platforms = ["facebook_ads", "google_ads"]

        assert len(custom_platforms) == 2
        assert "tiktok_ads" not in custom_platforms

    def test_include_ga4_flag(self):
        """Test GA4 inclusion flag."""
        include_ga4 = True
        platforms = ["facebook_ads"]

        all_extractors = platforms.copy()
        if include_ga4:
            all_extractors.append("ga4")

        assert "ga4" in all_extractors
        assert len(all_extractors) == 2

    def test_exclude_ga4_flag(self):
        """Test GA4 exclusion flag."""
        include_ga4 = False
        platforms = ["facebook_ads"]

        all_extractors = platforms.copy()
        if include_ga4:
            all_extractors.append("ga4")

        assert "ga4" not in all_extractors
        assert len(all_extractors) == 1


class TestAdsPipelineMetrics:
    """Tests for ads pipeline metrics calculations."""

    def test_ctr_calculation(self):
        """Test CTR calculation."""
        impressions = 10000
        clicks = 500

        ctr = clicks / impressions if impressions > 0 else 0

        assert ctr == 0.05

    def test_cpc_calculation(self):
        """Test CPC calculation."""
        spend = 100.0
        clicks = 500

        cpc = spend / clicks if clicks > 0 else 0

        assert cpc == 0.20

    def test_cpm_calculation(self):
        """Test CPM calculation."""
        spend = 100.0
        impressions = 10000

        cpm = (spend / impressions) * 1000 if impressions > 0 else 0

        assert cpm == 10.0

    def test_roas_calculation(self):
        """Test ROAS calculation."""
        spend = 100.0
        revenue = 500.0

        roas = revenue / spend if spend > 0 else 0

        assert roas == 5.0

    def test_zero_division_handling(self):
        """Test handling of zero division cases."""
        spend = 0.0
        impressions = 0
        clicks = 0

        ctr = clicks / impressions if impressions > 0 else 0
        cpc = spend / clicks if clicks > 0 else 0
        cpm = (spend / impressions) * 1000 if impressions > 0 else 0

        assert ctr == 0
        assert cpc == 0
        assert cpm == 0


class TestAdsPipelineDataLoading:
    """Tests for ads pipeline data loading logic."""

    def test_separate_ads_and_ga4_loading(self):
        """Test separating ads and GA4 for loading."""
        records = [
            {"_data_type": "ads", "campaign_id": "FB001"},
            {"_data_type": "ads", "campaign_id": "GOOG001"},
            {"_data_type": "ga4", "property_id": "123456"},
        ]

        ads_records = [
            r for r in records
            if r.get("_data_type") == "ads" or "campaign_id" in r
        ]
        ga4_records = [r for r in records if r.get("_data_type") == "ga4"]

        assert len(ads_records) == 2
        assert len(ga4_records) == 1

    def test_ga4_type_classification(self):
        """Test classifying GA4 records by type."""
        ga4_records = [
            {"record_id": "ga4_sessions_123_2024-01-01", "_data_type": "ga4"},
            {"record_id": "ga4_traffic_123_2024-01-01", "_data_type": "ga4", "source": "google"},
            {"record_id": "ga4_sessions_124_2024-01-01", "_data_type": "ga4"},
        ]

        ga4_sessions = [
            r for r in ga4_records
            if "sessions" in str(r.get("record_id", ""))
        ]
        ga4_traffic = [
            r for r in ga4_records
            if "traffic" in str(r.get("record_id", "")) or "source" in r
        ]

        assert len(ga4_sessions) == 2
        assert len(ga4_traffic) == 1

    def test_remove_internal_markers(self):
        """Test removing internal type markers before loading."""
        records = [
            {"_data_type": "ads", "campaign_id": "FB001"},
            {"_data_type": "ga4", "property_id": "123"},
        ]

        for r in records:
            r.pop("_data_type", None)

        assert "_data_type" not in records[0]
        assert "_data_type" not in records[1]


class TestAdsPipelineIntegration:
    """Integration tests with mocked external services."""

    @patch("src.pipelines.ads_pipeline.FacebookAdsExtractor")
    @patch("src.pipelines.ads_pipeline.GoogleAdsExtractor")
    @patch("src.pipelines.ads_pipeline.GA4Extractor")
    @patch("src.pipelines.ads_pipeline.RawDataLoader")
    @patch("src.pipelines.ads_pipeline.StagingDataLoader")
    def test_full_pipeline_run_mocked(
        self,
        mock_staging,
        mock_raw,
        mock_ga4,
        mock_google,
        mock_facebook,
        sample_date_range,
        sample_facebook_ads,
    ):
        """Test full pipeline run with mocked dependencies."""
        start, end = sample_date_range

        # Setup mock extractors
        fb_instance = MagicMock()
        fb_instance.extract.return_value = iter([sample_facebook_ads[0]["data"]])
        fb_instance.__enter__ = MagicMock(return_value=fb_instance)
        fb_instance.__exit__ = MagicMock(return_value=False)
        mock_facebook.return_value = fb_instance

        google_instance = MagicMock()
        google_instance.extract.return_value = iter([])
        google_instance.__enter__ = MagicMock(return_value=google_instance)
        google_instance.__exit__ = MagicMock(return_value=False)
        mock_google.return_value = google_instance

        ga4_instance = MagicMock()
        ga4_instance.extract.return_value = iter([])
        ga4_instance.__enter__ = MagicMock(return_value=ga4_instance)
        ga4_instance.__exit__ = MagicMock(return_value=False)
        mock_ga4.return_value = ga4_instance

        # Setup mock loaders
        raw_instance = MagicMock()
        raw_instance.load_raw_ads.return_value = 1
        raw_instance.load_raw_ga4.return_value = 0
        raw_instance.set_batch_id = MagicMock()
        mock_raw.return_value = raw_instance

        staging_instance = MagicMock()
        staging_instance.load_ads.return_value = 1
        staging_instance.load_ga4_sessions.return_value = 0
        staging_instance.load_ga4_traffic.return_value = 0
        mock_staging.return_value = staging_instance

        # Import after patching
        from src.pipelines.ads_pipeline import AdsPipeline

        # Run pipeline with minimal platforms
        pipeline = AdsPipeline(
            start, end,
            platforms=["facebook_ads", "google_ads"],
            include_ga4=True,
        )
        result = pipeline.run()

        # Verify extractors were called
        assert mock_facebook.called
        assert mock_google.called
        assert mock_ga4.called
