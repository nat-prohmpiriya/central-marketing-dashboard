"""Base loader class with common functionality."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Generator

from src.utils.logging import get_logger


class LoaderError(Exception):
    """Base exception for loader errors."""

    def __init__(
        self,
        message: str,
        destination: str,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.destination = destination
        self.details = details or {}
        super().__init__(self.message)


class ConnectionError(LoaderError):
    """Raised when connection to destination fails."""

    pass


class WriteError(LoaderError):
    """Raised when writing data fails."""

    pass


class SchemaError(LoaderError):
    """Raised when schema validation fails."""

    pass


class BaseLoader(ABC):
    """Abstract base class for all data loaders.

    Provides common functionality:
    - Batch loading with configurable size
    - Error handling and retry logic
    - Deduplication support
    - Load statistics tracking
    """

    # Override in subclasses
    destination_name: str = "base"
    default_batch_size: int = 1000

    def __init__(self, batch_size: int | None = None):
        self.logger = get_logger(f"loader.{self.destination_name}")
        self.batch_size = batch_size or self.default_batch_size

        # Statistics
        self._records_loaded = 0
        self._records_failed = 0
        self._batches_loaded = 0
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the destination.

        Returns:
            True if connection successful.

        Raises:
            ConnectionError: If connection fails.
        """
        pass

    @abstractmethod
    def load(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
        table_name: str,
        **kwargs: Any,
    ) -> int:
        """Load records to the destination.

        Args:
            records: Records to load.
            table_name: Target table name.
            **kwargs: Additional loader-specific options.

        Returns:
            Number of records successfully loaded.

        Raises:
            LoaderError: If loading fails.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the connection and clean up resources."""
        pass

    def load_batch(
        self,
        records: list[dict[str, Any]],
        table_name: str,
        **kwargs: Any,
    ) -> int:
        """Load a single batch of records.

        Args:
            records: Batch of records to load.
            table_name: Target table name.
            **kwargs: Additional options.

        Returns:
            Number of records loaded.
        """
        return self._write_batch(records, table_name, **kwargs)

    @abstractmethod
    def _write_batch(
        self,
        records: list[dict[str, Any]],
        table_name: str,
        **kwargs: Any,
    ) -> int:
        """Write a batch of records to the destination.

        Args:
            records: Records to write.
            table_name: Target table.
            **kwargs: Additional options.

        Returns:
            Number of records written.
        """
        pass

    def _batch_records(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[list[dict[str, Any]], None, None]:
        """Split records into batches.

        Args:
            records: Records to batch.

        Yields:
            Batches of records.
        """
        batch: list[dict[str, Any]] = []

        for record in records:
            batch.append(record)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def _add_metadata(
        self,
        record: dict[str, Any],
        table_name: str,
    ) -> dict[str, Any]:
        """Add ingestion metadata to a record.

        Args:
            record: Original record.
            table_name: Target table name.

        Returns:
            Record with metadata added.
        """
        return {
            **record,
            "_ingested_at": datetime.now(timezone.utc).isoformat(),
            "_source_table": table_name,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get loading statistics.

        Returns:
            Dictionary with loading statistics.
        """
        duration = None
        if self._start_time and self._end_time:
            duration = (self._end_time - self._start_time).total_seconds()

        return {
            "records_loaded": self._records_loaded,
            "records_failed": self._records_failed,
            "batches_loaded": self._batches_loaded,
            "duration_seconds": duration,
            "records_per_second": (
                self._records_loaded / duration if duration and duration > 0 else None
            ),
        }

    def reset_stats(self) -> None:
        """Reset loading statistics."""
        self._records_loaded = 0
        self._records_failed = 0
        self._batches_loaded = 0
        self._start_time = None
        self._end_time = None

    def __enter__(self) -> "BaseLoader":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()
