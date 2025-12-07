"""Tests for base pipeline functionality."""

from datetime import datetime, timezone
from typing import Any

import pytest

from src.pipelines.base import (
    BasePipeline,
    PipelineError,
    PipelineResult,
    PipelineStage,
)


class ConcretePipeline(BasePipeline):
    """Concrete implementation for testing."""

    pipeline_name = "test"

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        extract_data: list[dict] | None = None,
        transform_data: list[dict] | None = None,
        fail_at_stage: PipelineStage | None = None,
    ):
        super().__init__(start_date, end_date)
        self._test_extract_data = extract_data or []
        self._test_transform_data = transform_data or []
        self._fail_at_stage = fail_at_stage

    def extract(self) -> list[dict[str, Any]]:
        if self._fail_at_stage == PipelineStage.EXTRACT:
            raise PipelineError(
                message="Extract failed",
                pipeline=self.pipeline_name,
                stage=PipelineStage.EXTRACT,
            )
        return self._test_extract_data

    def transform(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self._fail_at_stage == PipelineStage.TRANSFORM:
            raise PipelineError(
                message="Transform failed",
                pipeline=self.pipeline_name,
                stage=PipelineStage.TRANSFORM,
            )
        return self._test_transform_data or records

    def load_raw(self, records: list[dict[str, Any]]) -> int:
        if self._fail_at_stage == PipelineStage.LOAD_RAW:
            raise PipelineError(
                message="Load raw failed",
                pipeline=self.pipeline_name,
                stage=PipelineStage.LOAD_RAW,
            )
        return len(records)

    def load_staging(self, records: list[dict[str, Any]]) -> int:
        if self._fail_at_stage == PipelineStage.LOAD_STAGING:
            raise PipelineError(
                message="Load staging failed",
                pipeline=self.pipeline_name,
                stage=PipelineStage.LOAD_STAGING,
            )
        return len(records)


class TestPipelineStage:
    """Tests for PipelineStage enum."""

    def test_stage_values(self):
        """Test stage enum values."""
        assert PipelineStage.EXTRACT.value == "extract"
        assert PipelineStage.TRANSFORM.value == "transform"
        assert PipelineStage.LOAD_RAW.value == "load_raw"
        assert PipelineStage.LOAD_STAGING.value == "load_staging"
        assert PipelineStage.COMPLETED.value == "completed"
        assert PipelineStage.FAILED.value == "failed"


class TestPipelineError:
    """Tests for PipelineError exception."""

    def test_error_creation(self):
        """Test creating pipeline error."""
        error = PipelineError(
            message="Test error",
            pipeline="test",
            stage=PipelineStage.EXTRACT,
            details={"key": "value"},
        )

        assert error.message == "Test error"
        assert error.pipeline == "test"
        assert error.stage == PipelineStage.EXTRACT
        assert error.details == {"key": "value"}

    def test_error_without_details(self):
        """Test error with no details."""
        error = PipelineError(
            message="Test error",
            pipeline="test",
            stage=PipelineStage.TRANSFORM,
        )

        assert error.details == {}


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_result_creation(self):
        """Test creating pipeline result."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 5, 0, tzinfo=timezone.utc)

        result = PipelineResult(
            pipeline_name="test",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=start,
            end_time=end,
            records_extracted=100,
            records_transformed=95,
            records_loaded_raw=100,
            records_loaded_staging=95,
        )

        assert result.pipeline_name == "test"
        assert result.success is True
        assert result.stage == PipelineStage.COMPLETED
        assert result.records_extracted == 100

    def test_duration_calculation(self):
        """Test duration calculation."""
        start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 1, 30, tzinfo=timezone.utc)

        result = PipelineResult(
            pipeline_name="test",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=start,
            end_time=end,
        )

        assert result.duration_seconds == 90.0

    def test_duration_without_end_time(self):
        """Test duration when end time is not set."""
        result = PipelineResult(
            pipeline_name="test",
            success=False,
            stage=PipelineStage.EXTRACT,
            start_time=datetime.now(timezone.utc),
        )

        assert result.duration_seconds is None

    def test_to_dict(self):
        """Test converting result to dictionary."""
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, 0, 1, 0, tzinfo=timezone.utc)

        result = PipelineResult(
            pipeline_name="test",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=start,
            end_time=end,
            records_extracted=100,
            metadata={"key": "value"},
        )

        result_dict = result.to_dict()

        assert result_dict["pipeline_name"] == "test"
        assert result_dict["success"] is True
        assert result_dict["stage"] == "completed"
        assert result_dict["duration_seconds"] == 60.0
        assert result_dict["records_extracted"] == 100
        assert result_dict["metadata"] == {"key": "value"}


class TestBasePipeline:
    """Tests for BasePipeline class."""

    @pytest.fixture
    def date_range(self):
        """Create date range for tests."""
        return (
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 31, tzinfo=timezone.utc),
        )

    def test_pipeline_initialization(self, date_range):
        """Test pipeline initialization."""
        start, end = date_range
        pipeline = ConcretePipeline(start, end)

        assert pipeline.start_date == start
        assert pipeline.end_date == end
        assert pipeline.batch_id is not None
        assert pipeline.pipeline_name == "test"

    def test_custom_batch_id(self, date_range):
        """Test pipeline with custom batch ID."""
        start, end = date_range
        # BasePipeline accepts batch_id in __init__
        # Test via direct assignment as ConcretePipeline doesn't pass it through
        from src.pipelines.base import BasePipeline

        class PipelineWithBatchId(ConcretePipeline):
            def __init__(self, start_date, end_date, batch_id=None):
                # Call BasePipeline's __init__ properly
                BasePipeline.__init__(self, start_date, end_date, batch_id)

        pipeline = PipelineWithBatchId(start, end, batch_id="custom-123")
        assert pipeline.batch_id == "custom-123"

    def test_successful_run(self, date_range):
        """Test successful pipeline run."""
        start, end = date_range
        test_data = [{"id": 1}, {"id": 2}, {"id": 3}]

        pipeline = ConcretePipeline(
            start, end,
            extract_data=test_data,
        )

        result = pipeline.run()

        assert result.success is True
        assert result.stage == PipelineStage.COMPLETED
        assert result.records_extracted == 3
        assert result.records_transformed == 3
        assert result.records_loaded_raw == 3
        assert result.records_loaded_staging == 3

    def test_run_with_skip_raw(self, date_range):
        """Test pipeline run with skip_raw flag."""
        start, end = date_range
        test_data = [{"id": 1}, {"id": 2}]

        pipeline = ConcretePipeline(start, end, extract_data=test_data)
        result = pipeline.run(skip_raw=True)

        assert result.success is True
        assert result.records_loaded_raw == 0
        assert result.records_loaded_staging == 2

    def test_run_with_skip_staging(self, date_range):
        """Test pipeline run with skip_staging flag."""
        start, end = date_range
        test_data = [{"id": 1}, {"id": 2}]

        pipeline = ConcretePipeline(start, end, extract_data=test_data)
        result = pipeline.run(skip_staging=True)

        assert result.success is True
        assert result.records_loaded_raw == 2
        assert result.records_loaded_staging == 0

    def test_run_with_skip_both(self, date_range):
        """Test pipeline run with both skip flags (dry run)."""
        start, end = date_range
        test_data = [{"id": 1}]

        pipeline = ConcretePipeline(start, end, extract_data=test_data)
        result = pipeline.run(skip_raw=True, skip_staging=True)

        assert result.success is True
        assert result.records_extracted == 1
        assert result.records_transformed == 1
        assert result.records_loaded_raw == 0
        assert result.records_loaded_staging == 0

    def test_extract_failure(self, date_range):
        """Test pipeline failure at extract stage."""
        start, end = date_range
        pipeline = ConcretePipeline(
            start, end,
            fail_at_stage=PipelineStage.EXTRACT,
        )

        result = pipeline.run()

        assert result.success is False
        assert result.stage == PipelineStage.EXTRACT
        assert len(result.errors) > 0
        assert result.errors[0]["message"] == "Extract failed"

    def test_transform_failure(self, date_range):
        """Test pipeline failure at transform stage."""
        start, end = date_range
        pipeline = ConcretePipeline(
            start, end,
            extract_data=[{"id": 1}],
            fail_at_stage=PipelineStage.TRANSFORM,
        )

        result = pipeline.run()

        assert result.success is False
        assert result.stage == PipelineStage.TRANSFORM
        assert len(result.errors) > 0

    def test_load_raw_failure(self, date_range):
        """Test pipeline failure at load_raw stage."""
        start, end = date_range
        pipeline = ConcretePipeline(
            start, end,
            extract_data=[{"id": 1}],
            fail_at_stage=PipelineStage.LOAD_RAW,
        )

        result = pipeline.run()

        assert result.success is False
        assert result.stage == PipelineStage.LOAD_RAW

    def test_load_staging_failure(self, date_range):
        """Test pipeline failure at load_staging stage."""
        start, end = date_range
        pipeline = ConcretePipeline(
            start, end,
            extract_data=[{"id": 1}],
            fail_at_stage=PipelineStage.LOAD_STAGING,
        )

        result = pipeline.run()

        assert result.success is False
        assert result.stage == PipelineStage.LOAD_STAGING

    def test_empty_extract(self, date_range):
        """Test pipeline with no data extracted."""
        start, end = date_range
        pipeline = ConcretePipeline(start, end, extract_data=[])

        result = pipeline.run()

        assert result.success is True
        assert result.records_extracted == 0
        assert result.records_loaded_raw == 0

    def test_get_result_before_run(self, date_range):
        """Test getting result before pipeline runs."""
        start, end = date_range
        pipeline = ConcretePipeline(start, end)

        assert pipeline.get_result() is None

    def test_get_result_after_run(self, date_range):
        """Test getting result after pipeline runs."""
        start, end = date_range
        pipeline = ConcretePipeline(start, end, extract_data=[{"id": 1}])

        pipeline.run()
        result = pipeline.get_result()

        assert result is not None
        assert result.success is True

    def test_cleanup_called(self, date_range):
        """Test that cleanup is called after run."""
        start, end = date_range
        test_data = [{"id": 1}, {"id": 2}]

        pipeline = ConcretePipeline(start, end, extract_data=test_data)
        pipeline.run()

        # After cleanup, internal data should be cleared
        assert pipeline._extracted_data == []
        assert pipeline._transformed_data == []

    def test_result_has_timestamps(self, date_range):
        """Test that result has proper timestamps."""
        start, end = date_range
        pipeline = ConcretePipeline(start, end, extract_data=[{"id": 1}])

        result = pipeline.run()

        assert result.start_time is not None
        assert result.end_time is not None
        assert result.end_time >= result.start_time
