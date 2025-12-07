"""Base pipeline class with common functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.utils.logging import get_logger


class PipelineStage(Enum):
    """Pipeline execution stages."""

    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD_RAW = "load_raw"
    LOAD_STAGING = "load_staging"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineError(Exception):
    """Base exception for pipeline errors."""

    def __init__(
        self,
        message: str,
        pipeline: str,
        stage: PipelineStage,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.pipeline = pipeline
        self.stage = stage
        self.details = details or {}
        super().__init__(self.message)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""

    pipeline_name: str
    success: bool
    stage: PipelineStage
    start_time: datetime
    end_time: datetime | None = None
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded_raw: int = 0
    records_loaded_staging: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float | None:
        """Get duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pipeline_name": self.pipeline_name,
            "success": self.success,
            "stage": self.stage.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "records_extracted": self.records_extracted,
            "records_transformed": self.records_transformed,
            "records_loaded_raw": self.records_loaded_raw,
            "records_loaded_staging": self.records_loaded_staging,
            "error_count": len(self.errors),
            "metadata": self.metadata,
        }


class BasePipeline(ABC):
    """Abstract base class for ETL pipelines.

    Provides common functionality:
    - Stage-based execution
    - Error handling and recovery
    - Progress tracking
    - Logging
    """

    pipeline_name: str = "base"

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        batch_id: str | None = None,
    ):
        """Initialize pipeline.

        Args:
            start_date: Start date for data extraction.
            end_date: End date for data extraction.
            batch_id: Optional batch identifier for tracking.
        """
        self.start_date = start_date
        self.end_date = end_date
        self.batch_id = batch_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.logger = get_logger(f"pipeline.{self.pipeline_name}")

        # State tracking
        self._current_stage = PipelineStage.EXTRACT
        self._result: PipelineResult | None = None

        # Data storage between stages
        self._extracted_data: list[dict[str, Any]] = []
        self._transformed_data: list[dict[str, Any]] = []

    def run(self, skip_raw: bool = False, skip_staging: bool = False) -> PipelineResult:
        """Run the full ETL pipeline.

        Args:
            skip_raw: Skip loading to raw layer.
            skip_staging: Skip loading to staging layer.

        Returns:
            PipelineResult with execution details.
        """
        self._result = PipelineResult(
            pipeline_name=self.pipeline_name,
            success=False,
            stage=PipelineStage.EXTRACT,
            start_time=datetime.now(timezone.utc),
        )

        try:
            # Extract
            self._current_stage = PipelineStage.EXTRACT
            self.logger.info(
                "Starting extraction",
                pipeline=self.pipeline_name,
                start_date=self.start_date.isoformat(),
                end_date=self.end_date.isoformat(),
            )
            self._extracted_data = list(self.extract())
            self._result.records_extracted = len(self._extracted_data)
            self.logger.info(
                "Extraction complete",
                records=self._result.records_extracted,
            )

            # Transform
            self._current_stage = PipelineStage.TRANSFORM
            self.logger.info("Starting transformation")
            self._transformed_data = list(self.transform(self._extracted_data))
            self._result.records_transformed = len(self._transformed_data)
            self.logger.info(
                "Transformation complete",
                records=self._result.records_transformed,
            )

            # Load to raw layer
            if not skip_raw:
                self._current_stage = PipelineStage.LOAD_RAW
                self.logger.info("Loading to raw layer")
                self._result.records_loaded_raw = self.load_raw(self._extracted_data)
                self.logger.info(
                    "Raw load complete",
                    records=self._result.records_loaded_raw,
                )

            # Load to staging layer
            if not skip_staging:
                self._current_stage = PipelineStage.LOAD_STAGING
                self.logger.info("Loading to staging layer")
                self._result.records_loaded_staging = self.load_staging(
                    self._transformed_data
                )
                self.logger.info(
                    "Staging load complete",
                    records=self._result.records_loaded_staging,
                )

            # Complete
            self._current_stage = PipelineStage.COMPLETED
            self._result.success = True
            self._result.stage = PipelineStage.COMPLETED

        except PipelineError as e:
            self._result.success = False
            self._result.stage = e.stage
            self._result.errors.append({
                "stage": e.stage.value,
                "message": e.message,
                "details": e.details,
            })
            self.logger.error(
                "Pipeline failed",
                stage=e.stage.value,
                error=e.message,
            )

        except Exception as e:
            self._result.success = False
            self._result.stage = self._current_stage
            self._result.errors.append({
                "stage": self._current_stage.value,
                "message": str(e),
                "type": type(e).__name__,
            })
            self.logger.error(
                "Pipeline failed with unexpected error",
                stage=self._current_stage.value,
                error=str(e),
            )

        finally:
            self._result.end_time = datetime.now(timezone.utc)
            self._cleanup()

        return self._result

    @abstractmethod
    def extract(self) -> list[dict[str, Any]]:
        """Extract data from sources.

        Returns:
            List of extracted records.
        """
        pass

    @abstractmethod
    def transform(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform extracted data.

        Args:
            records: Extracted records.

        Returns:
            List of transformed records.
        """
        pass

    @abstractmethod
    def load_raw(self, records: list[dict[str, Any]]) -> int:
        """Load data to raw layer.

        Args:
            records: Raw records to load.

        Returns:
            Number of records loaded.
        """
        pass

    @abstractmethod
    def load_staging(self, records: list[dict[str, Any]]) -> int:
        """Load data to staging layer.

        Args:
            records: Transformed records to load.

        Returns:
            Number of records loaded.
        """
        pass

    def _cleanup(self) -> None:
        """Clean up resources after pipeline execution."""
        self._extracted_data = []
        self._transformed_data = []

    def get_result(self) -> PipelineResult | None:
        """Get the pipeline result.

        Returns:
            PipelineResult if pipeline has run, None otherwise.
        """
        return self._result
