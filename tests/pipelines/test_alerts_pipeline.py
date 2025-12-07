"""Tests for alerts pipeline."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Mock google.cloud.bigquery before importing alerts_pipeline
mock_bigquery = MagicMock()
mock_bigquery.Client = MagicMock

# Only mock if google module doesn't exist or is already a mock
if "google" not in sys.modules or isinstance(sys.modules.get("google"), MagicMock):
    sys.modules["google"] = MagicMock()
    sys.modules["google.cloud"] = MagicMock()
    sys.modules["google.cloud.bigquery"] = mock_bigquery


from src.models.simple_alerts import (
    AlertRuleEngine,
    AlertSeverity,
    AlertType,
)
from src.pipelines.alerts_pipeline import (
    AlertsPipeline,
    AlertsPipelineResult,
    AlertsRefreshResult,
)


class TestAlertsRefreshResult:
    """Tests for AlertsRefreshResult dataclass."""

    def test_result_creation(self):
        """Test creating alerts refresh result."""
        result = AlertsRefreshResult(
            success=True,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            alerts_generated=10,
            critical_count=2,
            warning_count=5,
            info_count=3,
            query_cost_bytes=1000000,
        )

        assert result.success is True
        assert result.alerts_generated == 10
        assert result.critical_count == 2
        assert result.warning_count == 5
        assert result.duration_seconds == 60.0

    def test_result_without_end_time(self):
        """Test result without end time."""
        result = AlertsRefreshResult(
            success=False,
            start_time=datetime.now(timezone.utc),
            error="Query failed",
        )

        assert result.duration_seconds is None
        assert result.error == "Query failed"

    def test_to_dict(self):
        """Test converting result to dictionary."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)

        result = AlertsRefreshResult(
            success=True,
            start_time=start,
            end_time=end,
            alerts_generated=15,
            critical_count=3,
            warning_count=7,
            info_count=5,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["alerts_generated"] == 15
        assert result_dict["critical_count"] == 3
        assert result_dict["duration_seconds"] == 60.0


class TestAlertsPipelineResult:
    """Tests for AlertsPipelineResult dataclass."""

    def test_result_creation(self):
        """Test creating alerts pipeline result."""
        result = AlertsPipelineResult(
            success=True,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
            total_alerts=20,
        )

        assert result.success is True
        assert result.duration_seconds == 300.0
        assert result.total_alerts == 20

    def test_result_with_sql_result(self):
        """Test result with SQL refresh result."""
        sql_result = AlertsRefreshResult(
            success=True,
            start_time=datetime.now(timezone.utc),
            alerts_generated=10,
            critical_count=2,
        )

        result = AlertsPipelineResult(
            success=True,
            start_time=datetime.now(timezone.utc),
            sql_result=sql_result,
            total_alerts=10,
        )

        assert result.sql_result is not None
        assert result.sql_result.alerts_generated == 10

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = AlertsPipelineResult(
            success=True,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            total_alerts=5,
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["total_alerts"] == 5
        assert result_dict["python_alerts_count"] == 0


class TestAlertsPipeline:
    """Tests for AlertsPipeline class."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        settings = MagicMock()
        settings.gcp_project_id = "test-project"
        settings.bigquery_dataset_raw = "raw"
        settings.bigquery_dataset_staging = "staging"
        settings.bigquery_dataset_mart = "mart"
        return settings

    @pytest.fixture
    def sql_dir(self, tmp_path):
        """Create temp SQL directory with test files."""
        sql_dir = tmp_path / "sql" / "transformations" / "mart"
        sql_dir.mkdir(parents=True)

        # Create test SQL file
        (sql_dir / "simple_alerts.sql").write_text(
            "CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.mart_simple_alerts` AS SELECT 1;"
        )

        return sql_dir

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = AlertsPipeline()

        assert pipeline._client is None
        assert pipeline.rule_engine is not None

    def test_pipeline_with_custom_sql_dir(self, sql_dir):
        """Test pipeline with custom SQL directory."""
        pipeline = AlertsPipeline(sql_dir=sql_dir)

        assert pipeline.sql_dir == sql_dir

    def test_pipeline_with_custom_rule_engine(self):
        """Test pipeline with custom rule engine."""
        custom_engine = AlertRuleEngine(rules=[])
        pipeline = AlertsPipeline(rule_engine=custom_engine)

        assert len(pipeline.rule_engine.rules) == 0

    def test_substitute_variables(self, mock_settings):
        """Test variable substitution in SQL."""
        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline()

            sql = "SELECT * FROM `${project_id}.${dataset_mart}.test`"
            result = pipeline._substitute_variables(sql)

            assert result == "SELECT * FROM `test-project.mart.test`"

    def test_split_statements_simple(self, mock_settings):
        """Test splitting simple SQL statements."""
        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline()

            sql = "SELECT 1; SELECT 2; SELECT 3;"
            statements = pipeline._split_statements(sql)

            assert len(statements) == 3

    def test_split_statements_with_strings(self, mock_settings):
        """Test splitting statements with semicolons in strings."""
        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline()

            sql = "SELECT 'a;b;c'; SELECT \"x;y\";"
            statements = pipeline._split_statements(sql)

            assert len(statements) == 2
            assert "a;b;c" in statements[0]

    def test_split_statements_with_comments(self, mock_settings):
        """Test splitting statements with comments."""
        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline()

            sql = """
                -- This is a comment;
                SELECT 1;
                /* Another comment; */
                SELECT 2;
            """
            statements = pipeline._split_statements(sql)

            assert len(statements) == 2

    def test_load_sql_file_exists(self, mock_settings, sql_dir):
        """Test loading existing SQL file."""
        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline(sql_dir=sql_dir)

            sql = pipeline._load_sql()

            assert sql is not None
            assert "CREATE OR REPLACE TABLE" in sql

    def test_load_sql_file_not_found(self, mock_settings, tmp_path):
        """Test loading non-existent SQL file."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline(sql_dir=empty_dir)

            sql = pipeline._load_sql()

            assert sql is None

    def test_run_sql_success(self, mock_settings, sql_dir):
        """Test successful SQL alerts run."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = None
        mock_job.total_bytes_billed = 1000
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline(sql_dir=sql_dir)
            pipeline._client = mock_client

            # Mock _get_alert_counts
            pipeline._get_alert_counts = MagicMock(return_value={
                "critical": 2,
                "warning": 5,
                "info": 1,
                "total": 8,
            })

            result = pipeline.run(run_sql=True, run_python_rules=False)

            assert result.success is True
            assert result.sql_result is not None
            assert result.sql_result.alerts_generated == 8

    def test_run_with_failure(self, mock_settings, sql_dir):
        """Test pipeline run with SQL failure."""
        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("Query failed")

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline(sql_dir=sql_dir)
            pipeline._client = mock_client

            result = pipeline.run(run_sql=True)

            assert result.success is False
            assert "Query failed" in result.error

    def test_run_with_python_rules(self, mock_settings, sql_dir):
        """Test running with Python rules enabled."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = None
        mock_job.total_bytes_billed = 500
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline(sql_dir=sql_dir)
            pipeline._client = mock_client

            pipeline._get_alert_counts = MagicMock(return_value={
                "critical": 1,
                "warning": 2,
                "info": 0,
                "total": 3,
            })

            result = pipeline.run(run_sql=True, run_python_rules=True)

            assert result.success is True
            assert result.total_alerts >= 3

    def test_refresh_alerts(self, mock_settings, sql_dir):
        """Test refreshing alerts directly."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = None
        mock_job.total_bytes_billed = 2000
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline(sql_dir=sql_dir)
            pipeline._client = mock_client

            pipeline._get_alert_counts = MagicMock(return_value={
                "critical": 0,
                "warning": 3,
                "info": 2,
                "total": 5,
            })

            result = pipeline.refresh_alerts()

            assert result.success is True
            assert result.alerts_generated == 5

    def test_get_active_alerts(self, mock_settings):
        """Test getting active alerts."""
        mock_client = MagicMock()
        mock_job = MagicMock()

        # Mock row results
        mock_row1 = MagicMock()
        mock_row1.__iter__ = lambda self: iter([
            ("alert_id", "ALERT-001"),
            ("alert_type", "low_roas"),
            ("severity", "critical"),
        ])
        mock_row1.keys.return_value = ["alert_id", "alert_type", "severity"]

        mock_job.result.return_value = [mock_row1]
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline()
            pipeline._client = mock_client

            alerts = pipeline.get_active_alerts(limit=10)

            assert mock_client.query.called

    def test_get_active_alerts_with_filters(self, mock_settings):
        """Test getting active alerts with filters."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = []
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.alerts_pipeline.get_settings", return_value=mock_settings):
            pipeline = AlertsPipeline()
            pipeline._client = mock_client

            pipeline.get_active_alerts(
                severity=AlertSeverity.CRITICAL,
                alert_type=AlertType.LOW_ROAS,
                platform="shopee",
                limit=50,
            )

            # Check that query was called with filters
            call_args = mock_client.query.call_args[0][0]
            assert "severity = 'critical'" in call_args
            assert "alert_type = 'low_roas'" in call_args
            assert "platform = 'shopee'" in call_args


class TestAlertsPipelineIntegration:
    """Integration tests for alerts pipeline."""

    def test_sql_file_exists(self):
        """Test that alerts SQL file exists in the project."""
        project_root = Path(__file__).parent.parent.parent
        sql_path = project_root / "sql" / "transformations" / "mart" / "simple_alerts.sql"

        assert sql_path.exists(), f"SQL file not found: {sql_path}"

    def test_sql_file_has_content(self):
        """Test that alerts SQL file is not empty."""
        project_root = Path(__file__).parent.parent.parent
        sql_path = project_root / "sql" / "transformations" / "mart" / "simple_alerts.sql"

        content = sql_path.read_text()
        assert len(content) > 0
        assert "mart_simple_alerts" in content

    def test_sql_file_has_placeholders(self):
        """Test that SQL file uses correct placeholders."""
        project_root = Path(__file__).parent.parent.parent
        sql_path = project_root / "sql" / "transformations" / "mart" / "simple_alerts.sql"

        content = sql_path.read_text()

        assert "${project_id}" in content
        assert "${dataset_mart}" in content

    def test_sql_file_creates_alerts_table(self):
        """Test that SQL file creates the alerts table."""
        project_root = Path(__file__).parent.parent.parent
        sql_path = project_root / "sql" / "transformations" / "mart" / "simple_alerts.sql"

        content = sql_path.read_text()

        assert "CREATE OR REPLACE TABLE" in content
        assert "mart_simple_alerts" in content

    def test_sql_file_creates_views(self):
        """Test that SQL file creates the expected views."""
        project_root = Path(__file__).parent.parent.parent
        sql_path = project_root / "sql" / "transformations" / "mart" / "simple_alerts.sql"

        content = sql_path.read_text()

        assert "v_active_alerts" in content
        assert "v_alert_summary" in content
