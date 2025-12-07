"""Base transformer class with common functionality."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Generator

from pydantic import BaseModel, ValidationError

from src.utils.logging import get_logger


class TransformError(Exception):
    """Base exception for transformer errors."""

    def __init__(
        self,
        message: str,
        source_platform: str,
        record: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.source_platform = source_platform
        self.record = record
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(TransformError):
    """Raised when data validation fails."""

    pass


class MappingError(TransformError):
    """Raised when field mapping fails."""

    pass


class BaseTransformer(ABC):
    """Abstract base class for all data transformers.

    Provides common functionality:
    - Data validation using Pydantic
    - Error handling with dead letter queue
    - Currency normalization
    - Timezone conversion
    - Status mapping
    """

    # Override in subclasses
    source_platform: str = "base"
    target_schema: type[BaseModel] | None = None

    def __init__(self):
        self.logger = get_logger(f"transformer.{self.source_platform}")
        self._error_records: list[dict[str, Any]] = []

    @abstractmethod
    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform raw records to staging format.

        Args:
            records: Raw records from extractor.

        Yields:
            Transformed records in staging format.

        Raises:
            TransformError: If transformation fails critically.
        """
        pass

    def validate(self, record: dict[str, Any]) -> dict[str, Any]:
        """Validate a record against the target schema.

        Args:
            record: Record to validate.

        Returns:
            Validated record as dictionary.

        Raises:
            ValidationError: If validation fails.
        """
        if self.target_schema is None:
            return record

        try:
            validated = self.target_schema.model_validate(record)
            return validated.model_dump()
        except ValidationError as e:
            raise ValidationError(
                message=f"Validation failed: {e}",
                source_platform=self.source_platform,
                record=record,
                details={"validation_errors": e.errors()},
            )

    def _transform_record(self, record: dict[str, Any]) -> dict[str, Any] | None:
        """Transform a single record with error handling.

        Args:
            record: Raw record to transform.

        Returns:
            Transformed record or None if transformation failed.
        """
        try:
            transformed = self._map_fields(record)
            transformed = self._normalize_values(transformed)
            validated = self.validate(transformed)
            return validated
        except TransformError as e:
            self.logger.warning(
                "Transform error, adding to dead letter queue",
                error=str(e),
                record_id=record.get("id") or record.get("order_id"),
            )
            self._add_to_dead_letter(record, e)
            return None
        except Exception as e:
            self.logger.error(
                "Unexpected transform error",
                error=str(e),
                record_id=record.get("id") or record.get("order_id"),
            )
            self._add_to_dead_letter(record, e)
            return None

    @abstractmethod
    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map source fields to target fields.

        Args:
            record: Raw record with source field names.

        Returns:
            Record with target field names.
        """
        pass

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize values (currency, dates, status, etc.).

        Override in subclasses for platform-specific normalization.

        Args:
            record: Record with mapped fields.

        Returns:
            Record with normalized values.
        """
        return record

    def _add_to_dead_letter(
        self,
        record: dict[str, Any],
        error: Exception,
    ) -> None:
        """Add a failed record to the dead letter queue.

        Args:
            record: The record that failed transformation.
            error: The error that occurred.
        """
        self._error_records.append({
            "record": record,
            "error": str(error),
            "error_type": type(error).__name__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_platform": self.source_platform,
        })

    def get_error_records(self) -> list[dict[str, Any]]:
        """Get all records that failed transformation.

        Returns:
            List of error records with metadata.
        """
        return self._error_records

    def clear_error_records(self) -> None:
        """Clear the dead letter queue."""
        self._error_records = []

    # Utility methods for common transformations

    @staticmethod
    def normalize_currency(
        amount: float | int | str | Decimal | None,
        source_currency: str = "THB",
        target_currency: str = "THB",
    ) -> float | None:
        """Normalize amount to target currency.

        Args:
            amount: Original amount.
            source_currency: Source currency code.
            target_currency: Target currency code.

        Returns:
            Normalized amount or None if input is None.
        """
        if amount is None:
            return None

        # Convert to float
        if isinstance(amount, str):
            amount = float(amount.replace(",", ""))
        elif isinstance(amount, Decimal):
            amount = float(amount)
        else:
            amount = float(amount)

        # TODO: Implement actual currency conversion
        # For now, assume all amounts are in THB
        if source_currency == target_currency:
            return round(amount, 2)

        # Placeholder for currency conversion
        # In production, use forex-python or similar
        exchange_rates = {
            ("USD", "THB"): 35.0,
            ("THB", "USD"): 1 / 35.0,
        }

        rate = exchange_rates.get((source_currency, target_currency), 1.0)
        return round(amount * rate, 2)

    @staticmethod
    def normalize_datetime(
        dt: datetime | str | int | None,
        source_timezone: str = "UTC",
        target_timezone: str = "Asia/Bangkok",
    ) -> datetime | None:
        """Normalize datetime to target timezone.

        Args:
            dt: Original datetime (datetime, ISO string, or Unix timestamp).
            source_timezone: Source timezone name.
            target_timezone: Target timezone name.

        Returns:
            Normalized datetime or None if input is None.
        """
        if dt is None:
            return None

        from zoneinfo import ZoneInfo

        # Convert to datetime if needed
        if isinstance(dt, int):
            # Unix timestamp
            dt = datetime.fromtimestamp(dt, tz=ZoneInfo("UTC"))
        elif isinstance(dt, str):
            # ISO format string
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

        # Ensure timezone aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo(source_timezone))

        # Convert to target timezone
        return dt.astimezone(ZoneInfo(target_timezone))

    @staticmethod
    def normalize_status(
        status: str,
        status_mapping: dict[str, str],
        default: str = "unknown",
    ) -> str:
        """Normalize status to standard values.

        Args:
            status: Original status string.
            status_mapping: Mapping from source to target status.
            default: Default status if not found in mapping.

        Returns:
            Normalized status string.
        """
        if not status:
            return default
        return status_mapping.get(status.lower(), default)

    def get_stats(self) -> dict[str, int]:
        """Get transformation statistics.

        Returns:
            Dictionary with success/error counts.
        """
        return {
            "error_count": len(self._error_records),
        }
