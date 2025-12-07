"""Loaders package for loading data to destinations."""

from src.loaders.base import (
    BaseLoader,
    ConnectionError,
    LoaderError,
    SchemaError,
    WriteError,
)

# Lazy import BigQuery loaders to avoid import errors when google.cloud is not installed
try:
    from src.loaders.bigquery import (
        BigQueryLoader,
        RawDataLoader,
        StagingDataLoader,
    )
except ImportError:
    BigQueryLoader = None  # type: ignore[misc, assignment]
    RawDataLoader = None  # type: ignore[misc, assignment]
    StagingDataLoader = None  # type: ignore[misc, assignment]

__all__ = [
    "BaseLoader",
    "LoaderError",
    "ConnectionError",
    "WriteError",
    "SchemaError",
    "BigQueryLoader",
    "RawDataLoader",
    "StagingDataLoader",
]
