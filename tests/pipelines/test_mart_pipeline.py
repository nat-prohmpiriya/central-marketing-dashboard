"""Tests for mart pipeline."""

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Mock google.cloud.bigquery before importing mart_pipeline
mock_bigquery = MagicMock()
mock_bigquery.Client = MagicMock
mock_exceptions = MagicMock()


# Only mock if google module doesn't exist or is already a mock
if "google" not in sys.modules or isinstance(sys.modules.get("google"), MagicMock):
    sys.modules["google"] = MagicMock()
    sys.modules["google.cloud"] = MagicMock()
    sys.modules["google.cloud.bigquery"] = mock_bigquery
    sys.modules["google.cloud.exceptions"] = mock_exceptions


from src.pipelines.mart_pipeline import (
    MART_DEPENDENCIES,
    MART_SQL_FILES,
    MartPipeline,
    MartPipelineResult,
    MartRefreshResult,
    MartTable,
)


class TestMartTable:
    """Tests for MartTable enum."""

    def test_table_values(self):
        """Test mart table enum values."""
        assert MartTable.DAILY_PERFORMANCE.value == "daily_performance"
        assert MartTable.SHOP_PERFORMANCE.value == "shop_performance"
        assert MartTable.ADS_CHANNEL.value == "ads_channel"
        assert MartTable.CAMPAIGN.value == "campaign"
        assert MartTable.PRODUCT.value == "product"

    def test_all_tables_have_sql_files(self):
        """Test all tables have SQL file mappings."""
        for table in MartTable:
            assert table in MART_SQL_FILES

    def test_all_tables_have_dependencies(self):
        """Test all tables have dependency entries."""
        for table in MartTable:
            assert table in MART_DEPENDENCIES


class TestMartRefreshResult:
    """Tests for MartRefreshResult dataclass."""

    def test_result_creation(self):
        """Test creating mart refresh result."""
        result = MartRefreshResult(
            table=MartTable.DAILY_PERFORMANCE,
            success=True,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            rows_affected=100,
            query_cost_bytes=1000000,
        )

        assert result.table == MartTable.DAILY_PERFORMANCE
        assert result.success is True
        assert result.rows_affected == 100
        assert result.duration_seconds == 60.0

    def test_result_without_end_time(self):
        """Test result without end time."""
        result = MartRefreshResult(
            table=MartTable.CAMPAIGN,
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

        result = MartRefreshResult(
            table=MartTable.PRODUCT,
            success=True,
            start_time=start,
            end_time=end,
            rows_affected=50,
        )

        result_dict = result.to_dict()

        assert result_dict["table"] == "product"
        assert result_dict["success"] is True
        assert result_dict["duration_seconds"] == 60.0
        assert result_dict["rows_affected"] == 50


class TestMartPipelineResult:
    """Tests for MartPipelineResult dataclass."""

    def test_result_creation(self):
        """Test creating mart pipeline result."""
        result = MartPipelineResult(
            success=True,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
        )

        assert result.success is True
        assert result.duration_seconds == 300.0
        assert result.total_tables == 0

    def test_total_rows_affected(self):
        """Test calculating total rows affected."""
        result = MartPipelineResult(
            success=True,
            start_time=datetime.now(timezone.utc),
            tables_refreshed=[
                MartRefreshResult(
                    table=MartTable.DAILY_PERFORMANCE,
                    success=True,
                    start_time=datetime.now(timezone.utc),
                    rows_affected=100,
                ),
                MartRefreshResult(
                    table=MartTable.CAMPAIGN,
                    success=True,
                    start_time=datetime.now(timezone.utc),
                    rows_affected=50,
                ),
            ],
        )

        assert result.total_rows_affected == 150
        assert result.total_tables == 2

    def test_to_dict(self):
        """Test converting result to dictionary."""
        result = MartPipelineResult(
            success=True,
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
            tables_skipped=["product"],
        )

        result_dict = result.to_dict()

        assert result_dict["success"] is True
        assert result_dict["tables_skipped"] == 1
        assert result_dict["skipped"] == ["product"]


class TestMartPipeline:
    """Tests for MartPipeline class."""

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

        # Create test SQL files
        (sql_dir / "daily_performance.sql").write_text(
            "CREATE OR REPLACE TABLE `${project_id}.${dataset_mart}.test` AS SELECT 1;"
        )
        (sql_dir / "shop_performance.sql").write_text(
            "SELECT 1;"
        )
        (sql_dir / "ads_channel.sql").write_text(
            "SELECT 1;"
        )
        (sql_dir / "campaign.sql").write_text(
            "SELECT 1;"
        )
        (sql_dir / "product.sql").write_text(
            "SELECT 1;"
        )

        return sql_dir

    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = MartPipeline()

        assert len(pipeline.tables) == len(MartTable)
        assert pipeline._client is None

    def test_pipeline_with_specific_tables(self):
        """Test pipeline with specific tables."""
        tables = [MartTable.DAILY_PERFORMANCE, MartTable.CAMPAIGN]
        pipeline = MartPipeline(tables=tables)

        assert pipeline.tables == tables

    def test_pipeline_with_custom_sql_dir(self, sql_dir):
        """Test pipeline with custom SQL directory."""
        pipeline = MartPipeline(sql_dir=sql_dir)

        assert pipeline.sql_dir == sql_dir

    def test_substitute_variables(self, mock_settings):
        """Test variable substitution in SQL."""
        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline()

            sql = "SELECT * FROM `${project_id}.${dataset_mart}.test`"
            result = pipeline._substitute_variables(sql)

            assert result == "SELECT * FROM `test-project.mart.test`"

    def test_split_statements_simple(self, mock_settings):
        """Test splitting simple SQL statements."""
        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline()

            sql = "SELECT 1; SELECT 2; SELECT 3;"
            statements = pipeline._split_statements(sql)

            assert len(statements) == 3

    def test_split_statements_with_strings(self, mock_settings):
        """Test splitting statements with semicolons in strings."""
        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline()

            sql = "SELECT 'a;b;c'; SELECT \"x;y\";"
            statements = pipeline._split_statements(sql)

            assert len(statements) == 2
            assert "a;b;c" in statements[0]

    def test_split_statements_with_comments(self, mock_settings):
        """Test splitting statements with comments."""
        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline()

            sql = """
                -- This is a comment;
                SELECT 1;
                /* Another comment; */
                SELECT 2;
            """
            statements = pipeline._split_statements(sql)

            assert len(statements) == 2

    def test_topological_sort_no_deps(self, mock_settings):
        """Test topological sort with no dependencies."""
        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline()

            tables = [MartTable.DAILY_PERFORMANCE, MartTable.CAMPAIGN]
            sorted_tables = pipeline._topological_sort(tables)

            assert set(sorted_tables) == set(tables)

    def test_load_sql_file_exists(self, mock_settings, sql_dir):
        """Test loading existing SQL file."""
        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(sql_dir=sql_dir)

            sql = pipeline._load_sql(MartTable.DAILY_PERFORMANCE)

            assert sql is not None
            assert "CREATE OR REPLACE TABLE" in sql

    def test_load_sql_file_not_found(self, mock_settings, tmp_path):
        """Test loading non-existent SQL file."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(sql_dir=empty_dir)

            sql = pipeline._load_sql(MartTable.DAILY_PERFORMANCE)

            assert sql is None

    def test_run_success(self, mock_settings, sql_dir):
        """Test successful pipeline run."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = None
        mock_job.num_dml_affected_rows = 10
        mock_job.total_bytes_billed = 1000
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(
                tables=[MartTable.DAILY_PERFORMANCE],
                sql_dir=sql_dir,
            )
            pipeline._client = mock_client  # Inject mock client directly
            result = pipeline.run()

            assert result.success is True
            assert len(result.tables_refreshed) == 1
            assert result.tables_refreshed[0].table == MartTable.DAILY_PERFORMANCE

    def test_run_with_failure(self, mock_settings, sql_dir):
        """Test pipeline run with table failure."""
        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("Query failed")

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(
                tables=[MartTable.DAILY_PERFORMANCE],
                sql_dir=sql_dir,
            )
            pipeline._client = mock_client
            result = pipeline.run()

            assert result.success is False
            assert len(result.tables_failed) == 1

    def test_run_continue_on_error(self, mock_settings, sql_dir):
        """Test pipeline continues on error when configured."""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First table failed")
            mock_job = MagicMock()
            mock_job.result.return_value = None
            mock_job.num_dml_affected_rows = 10
            mock_job.total_bytes_billed = 1000
            return mock_job

        mock_client = MagicMock()
        mock_client.query.side_effect = side_effect

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(
                tables=[MartTable.DAILY_PERFORMANCE, MartTable.CAMPAIGN],
                sql_dir=sql_dir,
            )
            pipeline._client = mock_client
            result = pipeline.run(continue_on_error=True)

            # First should fail, second should succeed
            assert len(result.tables_failed) == 1
            assert len(result.tables_refreshed) == 1

    def test_run_stop_on_error(self, mock_settings, sql_dir):
        """Test pipeline stops on error when configured."""
        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("Query failed")

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(
                tables=[MartTable.DAILY_PERFORMANCE, MartTable.CAMPAIGN],
                sql_dir=sql_dir,
            )
            pipeline._client = mock_client
            result = pipeline.run(continue_on_error=False)

            # Should stop after first failure
            assert len(result.tables_failed) == 1
            assert len(result.tables_refreshed) == 0
            # Second table should not be attempted
            assert result.total_tables == 1

    def test_refresh_single_table(self, mock_settings, sql_dir):
        """Test refreshing a single table directly."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = None
        mock_job.num_dml_affected_rows = 50
        mock_job.total_bytes_billed = 500
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(sql_dir=sql_dir)
            pipeline._client = mock_client
            result = pipeline.refresh_table(MartTable.CAMPAIGN)

            assert result.success is True
            assert result.table == MartTable.CAMPAIGN

    def test_refresh_table_by_string(self, mock_settings, sql_dir):
        """Test refreshing a table by string name."""
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.result.return_value = None
        mock_job.num_dml_affected_rows = 25
        mock_job.total_bytes_billed = 250
        mock_client.query.return_value = mock_job

        with patch("src.pipelines.mart_pipeline.get_settings", return_value=mock_settings):
            pipeline = MartPipeline(sql_dir=sql_dir)
            pipeline._client = mock_client
            result = pipeline.refresh_table("product")

            assert result.success is True
            assert result.table == MartTable.PRODUCT


class TestMartPipelineIntegration:
    """Integration tests for mart pipeline."""

    def test_sql_files_exist(self):
        """Test that all SQL files exist in the project."""
        project_root = Path(__file__).parent.parent.parent
        sql_dir = project_root / "sql" / "transformations" / "mart"

        for table, filename in MART_SQL_FILES.items():
            sql_path = sql_dir / filename
            assert sql_path.exists(), f"SQL file not found for {table.value}: {sql_path}"

    def test_sql_files_have_content(self):
        """Test that SQL files are not empty."""
        project_root = Path(__file__).parent.parent.parent
        sql_dir = project_root / "sql" / "transformations" / "mart"

        for table, filename in MART_SQL_FILES.items():
            sql_path = sql_dir / filename
            content = sql_path.read_text()
            assert len(content) > 0, f"SQL file is empty: {sql_path}"
            assert "SELECT" in content.upper() or "CREATE" in content.upper(), \
                f"SQL file doesn't contain valid SQL: {sql_path}"

    def test_sql_files_have_placeholders(self):
        """Test that SQL files use correct placeholders."""
        project_root = Path(__file__).parent.parent.parent
        sql_dir = project_root / "sql" / "transformations" / "mart"

        for table, filename in MART_SQL_FILES.items():
            sql_path = sql_dir / filename
            content = sql_path.read_text()

            # Check for required placeholders
            assert "${project_id}" in content, f"Missing project_id placeholder: {sql_path}"
            assert "${dataset_mart}" in content, f"Missing dataset_mart placeholder: {sql_path}"
