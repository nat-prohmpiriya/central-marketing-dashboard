"""Unit tests for base classes."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
    RateLimiter,
)
from src.loaders.base import BaseLoader, LoaderError
from src.transformers.base import BaseTransformer, TransformError
from src.utils.currency import (
    convert_currency,
    format_currency,
    parse_currency_string,
    round_currency,
    to_decimal,
)
from src.utils.datetime import (
    date_range,
    days_ago,
    from_timestamp,
    now_utc,
    parse_iso,
    start_of_day,
    to_local,
    to_timestamp,
    to_utc,
)


# =============================================================================
# RateLimiter Tests
# =============================================================================


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(requests_per_minute=60)
        assert limiter.requests_per_minute == 60
        assert limiter.interval == 1.0

    def test_interval_calculation(self):
        """Test interval calculation for different rates."""
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.interval == 2.0

        limiter = RateLimiter(requests_per_minute=120)
        assert limiter.interval == 0.5

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_no_delay_first_request(self, mock_time, mock_sleep):
        """Test no delay on first request."""
        mock_time.return_value = 1000.0
        limiter = RateLimiter(requests_per_minute=60)
        limiter.wait()
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    @patch("time.time")
    def test_wait_with_delay(self, mock_time, mock_sleep):
        """Test delay when requests are too fast."""
        limiter = RateLimiter(requests_per_minute=60)
        limiter.last_request_time = 999.5
        mock_time.return_value = 1000.0  # 0.5 seconds later

        limiter.wait()

        # Should sleep for 0.5 seconds (1.0 interval - 0.5 elapsed)
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 0.4 < sleep_time < 0.6


# =============================================================================
# BaseExtractor Tests
# =============================================================================


class ConcreteExtractor(BaseExtractor):
    """Concrete implementation for testing."""

    platform_name = "test"
    base_url = "https://api.test.com"

    def authenticate(self):
        self._authenticated = True
        return True

    def extract(self, start_date, end_date, **kwargs):
        yield {"id": 1, "data": "test"}


class TestBaseExtractor:
    """Tests for BaseExtractor class."""

    def test_init(self):
        """Test extractor initialization."""
        extractor = ConcreteExtractor()
        assert extractor.platform_name == "test"
        assert extractor._authenticated is False

    def test_authenticate(self):
        """Test authentication."""
        extractor = ConcreteExtractor()
        result = extractor.authenticate()
        assert result is True
        assert extractor._authenticated is True

    def test_extract(self):
        """Test data extraction."""
        extractor = ConcreteExtractor()
        records = list(extractor.extract(datetime.now(), datetime.now()))
        assert len(records) == 1
        assert records[0]["id"] == 1

    def test_context_manager(self):
        """Test context manager protocol."""
        with ConcreteExtractor() as extractor:
            assert extractor is not None
        assert extractor._client is None

    def test_ensure_authenticated(self):
        """Test _ensure_authenticated method."""
        extractor = ConcreteExtractor()
        extractor._ensure_authenticated()
        assert extractor._authenticated is True

    def test_is_token_expired_no_expiry(self):
        """Test token expiry check when no expiry set."""
        extractor = ConcreteExtractor()
        assert extractor._is_token_expired() is False

    def test_is_token_expired_not_expired(self):
        """Test token expiry check when not expired."""
        extractor = ConcreteExtractor()
        extractor._token_expires_at = datetime.now() + timedelta(hours=1)
        assert extractor._is_token_expired() is False

    def test_is_token_expired_expired(self):
        """Test token expiry check when expired."""
        extractor = ConcreteExtractor()
        extractor._token_expires_at = datetime.now() - timedelta(hours=1)
        assert extractor._is_token_expired() is True


# =============================================================================
# BaseTransformer Tests
# =============================================================================


class ConcreteTransformer(BaseTransformer):
    """Concrete implementation for testing."""

    source_platform = "test"

    def transform(self, records):
        for record in records:
            transformed = self._transform_record(record)
            if transformed:
                yield transformed

    def _map_fields(self, record):
        return {
            "id": record.get("source_id"),
            "value": record.get("source_value"),
        }


class TestBaseTransformer:
    """Tests for BaseTransformer class."""

    def test_init(self):
        """Test transformer initialization."""
        transformer = ConcreteTransformer()
        assert transformer.source_platform == "test"
        assert transformer._error_records == []

    def test_transform_success(self):
        """Test successful transformation."""
        transformer = ConcreteTransformer()
        records = [{"source_id": 1, "source_value": "test"}]
        result = list(transformer.transform(records))
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["value"] == "test"

    def test_normalize_currency(self):
        """Test currency normalization."""
        result = BaseTransformer.normalize_currency(100.0, "THB", "THB")
        assert result == 100.0

        result = BaseTransformer.normalize_currency(None)
        assert result is None

    def test_normalize_datetime(self):
        """Test datetime normalization."""
        # Test Unix timestamp
        result = BaseTransformer.normalize_datetime(1704067200)  # 2024-01-01 00:00:00 UTC
        assert result is not None
        assert result.tzinfo is not None

        # Test None
        result = BaseTransformer.normalize_datetime(None)
        assert result is None

    def test_normalize_status(self):
        """Test status normalization."""
        mapping = {"completed": "done", "pending": "waiting"}
        result = BaseTransformer.normalize_status("completed", mapping)
        assert result == "done"

        result = BaseTransformer.normalize_status("unknown", mapping, "other")
        assert result == "other"

    def test_dead_letter_queue(self):
        """Test error record handling."""
        transformer = ConcreteTransformer()
        assert len(transformer.get_error_records()) == 0

        transformer._add_to_dead_letter({"id": 1}, Exception("test error"))
        assert len(transformer.get_error_records()) == 1

        transformer.clear_error_records()
        assert len(transformer.get_error_records()) == 0


# =============================================================================
# BaseLoader Tests
# =============================================================================


class ConcreteLoader(BaseLoader):
    """Concrete implementation for testing."""

    destination_name = "test"

    def __init__(self):
        super().__init__()
        self._connected = False
        self._written = []

    def connect(self):
        self._connected = True
        return True

    def close(self):
        self._connected = False

    def load(self, records, table_name, **kwargs):
        total = 0
        for batch in self._batch_records(records):
            total += self._write_batch(batch, table_name, **kwargs)
        return total

    def _write_batch(self, records, table_name, **kwargs):
        self._written.extend(records)
        return len(records)


class TestBaseLoader:
    """Tests for BaseLoader class."""

    def test_init(self):
        """Test loader initialization."""
        loader = ConcreteLoader()
        assert loader.destination_name == "test"
        assert loader.batch_size == 1000

    def test_connect(self):
        """Test connection."""
        loader = ConcreteLoader()
        result = loader.connect()
        assert result is True
        assert loader._connected is True

    def test_load_single_batch(self):
        """Test loading a single batch."""
        loader = ConcreteLoader()
        records = [{"id": i} for i in range(10)]
        result = loader.load(records, "test_table")
        assert result == 10
        assert len(loader._written) == 10

    def test_load_multiple_batches(self):
        """Test loading multiple batches."""
        loader = ConcreteLoader()
        loader.batch_size = 5
        records = [{"id": i} for i in range(12)]
        result = loader.load(records, "test_table")
        assert result == 12

    def test_batch_records(self):
        """Test record batching."""
        loader = ConcreteLoader()
        loader.batch_size = 3
        records = [1, 2, 3, 4, 5, 6, 7]
        batches = list(loader._batch_records(records))
        assert len(batches) == 3
        assert batches[0] == [1, 2, 3]
        assert batches[1] == [4, 5, 6]
        assert batches[2] == [7]

    def test_add_metadata(self):
        """Test metadata addition."""
        loader = ConcreteLoader()
        record = {"id": 1}
        result = loader._add_metadata(record, "test_table")
        assert "_ingested_at" in result
        assert "_source_table" in result
        assert result["_source_table"] == "test_table"

    def test_context_manager(self):
        """Test context manager protocol."""
        with ConcreteLoader() as loader:
            assert loader._connected is True
        assert loader._connected is False

    def test_get_stats(self):
        """Test statistics."""
        loader = ConcreteLoader()
        stats = loader.get_stats()
        assert stats["records_loaded"] == 0
        assert stats["records_failed"] == 0


# =============================================================================
# Datetime Utility Tests
# =============================================================================


class TestDatetimeUtils:
    """Tests for datetime utilities."""

    def test_now_utc(self):
        """Test now_utc returns timezone-aware datetime."""
        result = now_utc()
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_to_utc(self):
        """Test conversion to UTC."""
        bangkok = ZoneInfo("Asia/Bangkok")
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=bangkok)
        result = to_utc(dt)
        assert result.tzinfo.key == "UTC"
        assert result.hour == 5  # 12:00 Bangkok = 05:00 UTC

    def test_to_local(self):
        """Test conversion to local timezone."""
        utc = ZoneInfo("UTC")
        dt = datetime(2024, 1, 1, 5, 0, tzinfo=utc)
        result = to_local(dt, ZoneInfo("Asia/Bangkok"))
        assert result.hour == 12  # 05:00 UTC = 12:00 Bangkok

    def test_from_timestamp(self):
        """Test timestamp conversion."""
        ts = 1704067200  # 2024-01-01 00:00:00 UTC
        result = from_timestamp(ts)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_to_timestamp(self):
        """Test datetime to timestamp."""
        dt = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        result = to_timestamp(dt)
        assert result == 1704067200

    def test_parse_iso(self):
        """Test ISO string parsing."""
        result = parse_iso("2024-01-15T10:30:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

        result = parse_iso("2024-01-15T10:30:00+07:00")
        assert result.tzinfo is not None

    def test_start_of_day(self):
        """Test start of day calculation."""
        dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
        result = start_of_day(dt)
        assert result.hour == 0
        assert result.minute == 0

    def test_date_range(self):
        """Test date range generation."""
        start = datetime(2024, 1, 1, tzinfo=ZoneInfo("UTC"))
        end = datetime(2024, 1, 5, tzinfo=ZoneInfo("UTC"))
        result = date_range(start, end)
        assert len(result) == 5

    def test_days_ago(self):
        """Test days ago calculation."""
        result = days_ago(7)
        today = datetime.now(ZoneInfo("Asia/Bangkok")).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        expected = today - timedelta(days=7)
        assert result.date() == expected.date()


# =============================================================================
# Currency Utility Tests
# =============================================================================


class TestCurrencyUtils:
    """Tests for currency utilities."""

    def test_to_decimal(self):
        """Test decimal conversion."""
        assert to_decimal(100) == Decimal("100")
        assert to_decimal("100.50") == Decimal("100.50")
        assert to_decimal("1,000.50") == Decimal("1000.50")
        assert to_decimal(None) == Decimal("0")

    def test_round_currency(self):
        """Test currency rounding."""
        result = round_currency(Decimal("100.555"))
        assert result == Decimal("100.56")

        result = round_currency(100.554, decimals=2)
        assert result == Decimal("100.55")

    def test_convert_currency_same(self):
        """Test same currency conversion."""
        result = convert_currency(100, "THB", "THB")
        assert result == Decimal("100.00")

    def test_convert_currency_different(self):
        """Test different currency conversion."""
        result = convert_currency(100, "USD", "THB")
        assert result == Decimal("3500.00")

    def test_format_currency(self):
        """Test currency formatting."""
        result = format_currency(1000, "THB")
        assert "1,000.00" in result
        assert "฿" in result

        result = format_currency(1000, "USD")
        assert "$" in result

    def test_parse_currency_string(self):
        """Test currency string parsing."""
        amount, currency = parse_currency_string("$100.00")
        assert amount == Decimal("100.00")
        assert currency == "USD"

        amount, currency = parse_currency_string("฿500")
        assert amount == Decimal("500")
        assert currency == "THB"

        amount, currency = parse_currency_string("100 THB")
        assert amount == Decimal("100")
        assert currency == "THB"


# =============================================================================
# Error Classes Tests
# =============================================================================


class TestErrors:
    """Tests for error classes."""

    def test_authentication_error(self):
        """Test AuthenticationError."""
        error = AuthenticationError(
            message="Auth failed",
            platform="test",
            details={"code": 401},
        )
        assert error.message == "Auth failed"
        assert error.platform == "test"
        assert error.details["code"] == 401

    def test_api_error(self):
        """Test APIError."""
        error = APIError(
            message="Request failed",
            platform="test",
        )
        assert str(error) == "Request failed"

    def test_transform_error(self):
        """Test TransformError."""
        error = TransformError(
            message="Transform failed",
            source_platform="test",
            record={"id": 1},
        )
        assert error.record == {"id": 1}

    def test_loader_error(self):
        """Test LoaderError."""
        error = LoaderError(
            message="Load failed",
            destination="bigquery",
        )
        assert error.destination == "bigquery"
