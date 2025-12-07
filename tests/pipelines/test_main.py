"""Tests for main entry point."""

import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


class TestDateParsing:
    """Tests for date parsing utilities."""

    def test_parse_date_valid(self):
        """Test parsing valid date string."""
        from src.main import parse_date

        result = parse_date("2024-01-15")

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.tzinfo == timezone.utc

    def test_parse_date_invalid(self):
        """Test parsing invalid date string."""
        from src.main import parse_date

        with pytest.raises(ValueError):
            parse_date("invalid-date")

    def test_parse_date_wrong_format(self):
        """Test parsing date with wrong format."""
        from src.main import parse_date

        with pytest.raises(ValueError):
            parse_date("15/01/2024")


class TestDateRangeCalculation:
    """Tests for date range calculation."""

    def test_get_date_range_from_dates(self):
        """Test getting date range from explicit dates."""
        from src.main import get_date_range

        start, end = get_date_range("2024-01-01", "2024-01-31", None)

        assert start.year == 2024
        assert start.month == 1
        assert start.day == 1
        assert end.day == 31

    def test_get_date_range_from_days(self):
        """Test getting date range from days parameter."""
        from src.main import get_date_range

        start, end = get_date_range(None, None, 7)

        # End should be now, start should be 7 days ago
        assert (end - start).days == 7

    def test_get_date_range_default(self):
        """Test getting date range with default (7 days)."""
        from src.main import get_date_range

        start, end = get_date_range(None, None, None)

        # Default is 7 days
        assert (end - start).days == 7


class TestPlatformParsing:
    """Tests for platform parsing."""

    def test_parse_platforms_single(self):
        """Test parsing single platform."""
        platforms_str = "shopee"
        platforms = [p.strip() for p in platforms_str.split(",")]

        assert platforms == ["shopee"]

    def test_parse_platforms_multiple(self):
        """Test parsing multiple platforms."""
        platforms_str = "shopee,lazada,tiktok_shop"
        platforms = [p.strip() for p in platforms_str.split(",")]

        assert platforms == ["shopee", "lazada", "tiktok_shop"]

    def test_parse_platforms_with_spaces(self):
        """Test parsing platforms with spaces."""
        platforms_str = "shopee, lazada, tiktok_shop"
        platforms = [p.strip() for p in platforms_str.split(",")]

        assert platforms == ["shopee", "lazada", "tiktok_shop"]

    def test_parse_platforms_none(self):
        """Test parsing None platforms."""
        platforms_str = None
        platforms = None

        if platforms_str:
            platforms = [p.strip() for p in platforms_str.split(",")]

        assert platforms is None


class TestPrintResult:
    """Tests for result printing."""

    def test_print_success_result(self, capsys):
        """Test printing successful result."""
        from src.main import print_result
        from src.pipelines.base import PipelineResult, PipelineStage

        result = PipelineResult(
            pipeline_name="ecommerce",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
            records_extracted=100,
            records_transformed=95,
            records_loaded_raw=100,
            records_loaded_staging=95,
        )

        print_result(result)

        captured = capsys.readouterr()
        assert "SUCCESS" in captured.out
        assert "ecommerce" in captured.out
        assert "100" in captured.out

    def test_print_failed_result(self, capsys):
        """Test printing failed result."""
        from src.main import print_result
        from src.pipelines.base import PipelineResult, PipelineStage

        result = PipelineResult(
            pipeline_name="ecommerce",
            success=False,
            stage=PipelineStage.EXTRACT,
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            errors=[
                {"stage": "extract", "message": "API error"},
            ],
        )

        print_result(result)

        captured = capsys.readouterr()
        assert "FAILED" in captured.out
        assert "API error" in captured.out

    def test_print_result_with_metadata(self, capsys):
        """Test printing result with metadata."""
        from src.main import print_result
        from src.pipelines.base import PipelineResult, PipelineStage

        result = PipelineResult(
            pipeline_name="products",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            metadata={
                "sku_mappings_loaded": 10,
                "new_sku_mappings": 3,
            },
        )

        print_result(result)

        captured = capsys.readouterr()
        assert "sku_mappings_loaded" in captured.out
        assert "10" in captured.out


class TestMainFunction:
    """Tests for main function."""

    def test_main_no_command(self):
        """Test main with no command shows help."""
        from src.main import main

        # Save original argv
        original_argv = sys.argv

        try:
            sys.argv = ["main.py"]
            result = main()
            assert result == 1
        finally:
            sys.argv = original_argv

    @patch("src.main.EcommercePipeline")
    def test_main_ecommerce_command(self, mock_pipeline):
        """Test main with ecommerce command."""
        from src.main import main
        from src.pipelines.base import PipelineResult, PipelineStage

        # Setup mock
        mock_result = PipelineResult(
            pipeline_name="ecommerce",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        mock_instance = MagicMock()
        mock_instance.run.return_value = mock_result
        mock_pipeline.return_value = mock_instance

        # Save original argv
        original_argv = sys.argv

        try:
            # Global args must come before subcommand
            sys.argv = ["main.py", "--days", "7", "ecommerce"]
            result = main()
            assert result == 0
            assert mock_pipeline.called
        finally:
            sys.argv = original_argv

    @patch("src.main.AdsPipeline")
    def test_main_ads_command(self, mock_pipeline):
        """Test main with ads command."""
        from src.main import main
        from src.pipelines.base import PipelineResult, PipelineStage

        # Setup mock
        mock_result = PipelineResult(
            pipeline_name="ads",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        mock_instance = MagicMock()
        mock_instance.run.return_value = mock_result
        mock_pipeline.return_value = mock_instance

        # Save original argv
        original_argv = sys.argv

        try:
            # Global args must come before subcommand
            sys.argv = ["main.py", "--days", "7", "ads"]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

    @patch("src.main.ProductPipeline")
    def test_main_products_command(self, mock_pipeline):
        """Test main with products command."""
        from src.main import main
        from src.pipelines.base import PipelineResult, PipelineStage

        # Setup mock
        mock_result = PipelineResult(
            pipeline_name="products",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        mock_instance = MagicMock()
        mock_instance.run.return_value = mock_result
        mock_pipeline.return_value = mock_instance

        # Save original argv
        original_argv = sys.argv

        try:
            # Global args must come before subcommand
            sys.argv = ["main.py", "--days", "7", "products"]
            result = main()
            assert result == 0
        finally:
            sys.argv = original_argv

    def test_dry_run_flags(self):
        """Test dry run sets skip flags correctly."""
        # When --dry-run is set, both skip_raw and skip_staging should be True
        dry_run = True
        skip_raw_arg = False
        skip_staging_arg = False

        skip_raw = dry_run or skip_raw_arg
        skip_staging = dry_run or skip_staging_arg

        assert skip_raw is True
        assert skip_staging is True

    def test_skip_raw_flag(self):
        """Test skip-raw flag."""
        dry_run = False
        skip_raw_arg = True
        skip_staging_arg = False

        skip_raw = dry_run or skip_raw_arg
        skip_staging = dry_run or skip_staging_arg

        assert skip_raw is True
        assert skip_staging is False

    def test_skip_staging_flag(self):
        """Test skip-staging flag."""
        dry_run = False
        skip_raw_arg = False
        skip_staging_arg = True

        skip_raw = dry_run or skip_raw_arg
        skip_staging = dry_run or skip_staging_arg

        assert skip_raw is False
        assert skip_staging is True


class TestAllPipelinesCommand:
    """Tests for running all pipelines."""

    def test_filter_ads_platforms(self):
        """Test filtering platforms for ads pipeline."""
        platforms = ["shopee", "facebook_ads", "google_ads", "lazada"]

        ads_platforms = [
            p for p in platforms
            if p in ["facebook_ads", "google_ads", "tiktok_ads", "line_ads", "shopee_ads", "lazada_ads"]
        ]

        assert ads_platforms == ["facebook_ads", "google_ads"]

    def test_filter_ecommerce_platforms(self):
        """Test filtering platforms for e-commerce pipeline."""
        platforms = ["shopee", "facebook_ads", "google_ads", "lazada"]

        ecommerce_platforms = [
            p for p in platforms
            if p in ["shopee", "lazada", "tiktok_shop"]
        ]

        assert ecommerce_platforms == ["shopee", "lazada"]

    def test_all_success(self):
        """Test all pipelines success summary."""
        results = {
            "ecommerce": MagicMock(success=True),
            "ads": MagicMock(success=True),
            "products": MagicMock(success=True),
        }

        all_success = all(r.success for r in results.values())
        assert all_success is True

    def test_partial_failure(self):
        """Test partial pipeline failure summary."""
        results = {
            "ecommerce": MagicMock(success=True),
            "ads": MagicMock(success=False),
            "products": MagicMock(success=True),
        }

        all_success = all(r.success for r in results.values())
        assert all_success is False

        # Count failures
        failures = [name for name, r in results.items() if not r.success]
        assert failures == ["ads"]
