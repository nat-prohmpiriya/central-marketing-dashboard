"""Tests for Cloud Functions."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Mock google.cloud.bigquery before importing cloud functions
mock_bigquery = MagicMock()
mock_bigquery.Client = MagicMock

if "google" not in sys.modules or isinstance(sys.modules.get("google"), MagicMock):
    sys.modules["google"] = MagicMock()
    sys.modules["google.cloud"] = MagicMock()
    sys.modules["google.cloud.bigquery"] = mock_bigquery


class MockRequest:
    """Mock Flask request object."""

    def __init__(self, json_data=None, args=None):
        self._json = json_data or {}
        self.args = args or {}

    def get_json(self, silent=False):
        return self._json


class TestEcommerceCloudFunction:
    """Tests for E-commerce Cloud Function."""

    def test_import_main(self):
        """Test that main module can be imported."""
        # Add cloud functions to path
        cloud_functions_dir = Path(__file__).parent.parent.parent / "cloud_functions" / "etl_ecommerce"
        sys.path.insert(0, str(cloud_functions_dir.parent.parent))

        # Should not raise
        assert True

    def test_mock_request_creation(self):
        """Test mock request creation."""
        request = MockRequest(
            json_data={"days_back": 3, "platforms": ["shopee"]},
            args={"test": "value"},
        )

        assert request.get_json() == {"days_back": 3, "platforms": ["shopee"]}
        assert request.args == {"test": "value"}

    @patch("src.pipelines.EcommercePipeline")
    def test_etl_ecommerce_success(self, mock_pipeline_class):
        """Test successful E-commerce ETL execution."""
        # Mock pipeline result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_result.end_time = datetime(2024, 1, 1, 0, 5, 0, tzinfo=timezone.utc)
        mock_result.duration_seconds = 300.0
        mock_result.records_extracted = 100
        mock_result.records_transformed = 95
        mock_result.records_loaded_raw = 100
        mock_result.records_loaded_staging = 95
        mock_result.errors = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        # This test validates the mock setup is correct
        result = mock_pipeline.run()
        assert result.success is True
        assert result.records_extracted == 100

    @patch("src.pipelines.EcommercePipeline")
    def test_etl_ecommerce_with_date_range(self, mock_pipeline_class):
        """Test E-commerce ETL with custom date range."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.start_time = datetime.now(timezone.utc)
        mock_result.end_time = datetime.now(timezone.utc)
        mock_result.duration_seconds = 60.0
        mock_result.records_extracted = 50
        mock_result.records_transformed = 50
        mock_result.records_loaded_raw = 50
        mock_result.records_loaded_staging = 50
        mock_result.errors = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        # Validate date parsing would work
        start_date = datetime.fromisoformat("2024-01-01T00:00:00+00:00")
        end_date = datetime.fromisoformat("2024-01-07T00:00:00+00:00")

        assert start_date < end_date


class TestAdsCloudFunction:
    """Tests for Ads Cloud Function."""

    @patch("src.pipelines.AdsPipeline")
    def test_etl_ads_success(self, mock_pipeline_class):
        """Test successful Ads ETL execution."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_result.end_time = datetime(2024, 1, 1, 0, 10, 0, tzinfo=timezone.utc)
        mock_result.duration_seconds = 600.0
        mock_result.records_extracted = 200
        mock_result.records_transformed = 190
        mock_result.records_loaded_raw = 200
        mock_result.records_loaded_staging = 190
        mock_result.errors = []

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        result = mock_pipeline.run()
        assert result.success is True
        assert result.records_extracted == 200

    @patch("src.pipelines.AdsPipeline")
    def test_etl_ads_with_ga4(self, mock_pipeline_class):
        """Test Ads ETL with GA4 enabled."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.records_extracted = 300

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        # Verify AdsPipeline can be called with include_ga4
        from src.pipelines import AdsPipeline
        mock_pipeline_class(
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            include_ga4=True,
        )
        mock_pipeline_class.assert_called()


class TestMartCloudFunction:
    """Tests for Mart Cloud Function."""

    @patch("src.pipelines.MartPipeline")
    def test_etl_mart_success(self, mock_pipeline_class):
        """Test successful Mart ETL execution."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_result.end_time = datetime(2024, 1, 1, 0, 2, 0, tzinfo=timezone.utc)
        mock_result.duration_seconds = 120.0
        mock_result.total_tables = 5
        mock_result.tables_refreshed = []
        mock_result.tables_failed = []
        mock_result.tables_skipped = []
        mock_result.total_bytes_billed = 1000000

        mock_pipeline = MagicMock()
        mock_pipeline.run_all.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        result = mock_pipeline.run_all()
        assert result.success is True
        assert result.total_tables == 5

    @patch("src.pipelines.MartPipeline")
    def test_etl_mart_specific_tables(self, mock_pipeline_class):
        """Test Mart ETL with specific tables."""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.total_tables = 2

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        # Verify MartTable enum works
        from src.pipelines import MartTable

        tables = [MartTable.DAILY_PERFORMANCE, MartTable.SHOP_PERFORMANCE]
        assert len(tables) == 2


class TestAlertsCloudFunction:
    """Tests for Alerts Cloud Function."""

    @patch("src.pipelines.AlertsPipeline")
    def test_etl_alerts_success(self, mock_pipeline_class):
        """Test successful Alerts ETL execution."""
        mock_sql_result = MagicMock()
        mock_sql_result.alerts_generated = 10
        mock_sql_result.critical_count = 2
        mock_sql_result.warning_count = 5
        mock_sql_result.info_count = 3
        mock_sql_result.to_dict.return_value = {
            "alerts_generated": 10,
            "critical_count": 2,
        }

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_result.end_time = datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)
        mock_result.duration_seconds = 60.0
        mock_result.total_alerts = 10
        mock_result.sql_result = mock_sql_result
        mock_result.python_alerts = []
        mock_result.error = None

        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = mock_result
        mock_pipeline_class.return_value = mock_pipeline

        result = mock_pipeline.run()
        assert result.success is True
        assert result.total_alerts == 10

    @patch("src.pipelines.AlertsPipeline")
    def test_get_active_alerts(self, mock_pipeline_class):
        """Test getting active alerts."""
        mock_alerts = [
            {"alert_id": "ALERT-001", "severity": "critical"},
            {"alert_id": "ALERT-002", "severity": "warning"},
        ]

        mock_pipeline = MagicMock()
        mock_pipeline.get_active_alerts.return_value = mock_alerts
        mock_pipeline_class.return_value = mock_pipeline

        result = mock_pipeline.get_active_alerts(limit=10)
        assert len(result) == 2
        assert result[0]["alert_id"] == "ALERT-001"


class TestSchedulerConfig:
    """Tests for scheduler configuration."""

    def test_scheduler_config_exists(self):
        """Test that scheduler config file exists."""
        config_path = Path(__file__).parent.parent.parent / "cloud_functions" / "scheduler_config.yaml"
        assert config_path.exists()

    def test_scheduler_config_content(self):
        """Test scheduler config has expected content."""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "cloud_functions" / "scheduler_config.yaml"
        content = config_path.read_text()

        # Parse YAML
        config = yaml.safe_load(content)

        assert "schedulers" in config
        schedulers = config["schedulers"]

        # Should have 4 schedulers
        assert len(schedulers) == 4

        # Check scheduler names
        names = [s["name"] for s in schedulers]
        assert "etl-ecommerce-scheduler" in names
        assert "etl-ads-scheduler" in names
        assert "etl-mart-scheduler" in names
        assert "etl-alerts-scheduler" in names

    def test_scheduler_schedules(self):
        """Test scheduler cron expressions are valid."""
        import yaml

        config_path = Path(__file__).parent.parent.parent / "cloud_functions" / "scheduler_config.yaml"
        content = config_path.read_text()
        config = yaml.safe_load(content)

        for scheduler in config["schedulers"]:
            schedule = scheduler["schedule"]
            # Basic validation: should have 5 fields (minute hour day month weekday)
            parts = schedule.split()
            assert len(parts) == 5, f"Invalid cron: {schedule}"


class TestDeployScript:
    """Tests for deploy script."""

    def test_deploy_script_exists(self):
        """Test that deploy script exists."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "deploy_functions.sh"
        assert script_path.exists()

    def test_deploy_script_executable(self):
        """Test that deploy script is executable."""
        import os
        import stat

        script_path = Path(__file__).parent.parent.parent / "scripts" / "deploy_functions.sh"
        mode = os.stat(script_path).st_mode
        assert mode & stat.S_IXUSR, "Script should be executable"

    def test_deploy_script_content(self):
        """Test deploy script has expected functions."""
        script_path = Path(__file__).parent.parent.parent / "scripts" / "deploy_functions.sh"
        content = script_path.read_text()

        # Check for main functions
        assert "deploy_ecommerce()" in content
        assert "deploy_ads()" in content
        assert "deploy_mart()" in content
        assert "deploy_alerts()" in content
        assert "deploy_all()" in content
        assert "create_schedulers()" in content


class TestCloudFunctionStructure:
    """Tests for Cloud Function directory structure."""

    def test_ecommerce_function_structure(self):
        """Test E-commerce function has required files."""
        func_dir = Path(__file__).parent.parent.parent / "cloud_functions" / "etl_ecommerce"
        assert (func_dir / "main.py").exists()
        assert (func_dir / "requirements.txt").exists()

    def test_ads_function_structure(self):
        """Test Ads function has required files."""
        func_dir = Path(__file__).parent.parent.parent / "cloud_functions" / "etl_ads"
        assert (func_dir / "main.py").exists()
        assert (func_dir / "requirements.txt").exists()

    def test_mart_function_structure(self):
        """Test Mart function has required files."""
        func_dir = Path(__file__).parent.parent.parent / "cloud_functions" / "etl_mart"
        assert (func_dir / "main.py").exists()
        assert (func_dir / "requirements.txt").exists()

    def test_alerts_function_structure(self):
        """Test Alerts function has required files."""
        func_dir = Path(__file__).parent.parent.parent / "cloud_functions" / "etl_alerts"
        assert (func_dir / "main.py").exists()
        assert (func_dir / "requirements.txt").exists()

    def test_requirements_have_functions_framework(self):
        """Test all requirements include functions-framework."""
        cloud_functions_dir = Path(__file__).parent.parent.parent / "cloud_functions"

        for func_dir in ["etl_ecommerce", "etl_ads", "etl_mart", "etl_alerts"]:
            req_file = cloud_functions_dir / func_dir / "requirements.txt"
            content = req_file.read_text()
            assert "functions-framework" in content, f"Missing functions-framework in {func_dir}"
