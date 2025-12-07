"""Loaders package for loading data to destinations."""

from src.loaders.base import (
    BaseLoader,
    ConnectionError,
    LoaderError,
    SchemaError,
    WriteError,
)

# Lazy import BigQueryLoader to avoid import errors when google.cloud is not installed
try:
    from src.loaders.bigquery import BigQueryLoader
except ImportError:
    BigQueryLoader = None  # type: ignore[misc, assignment]

__all__ = [
    "BaseLoader",
    "LoaderError",
    "ConnectionError",
    "WriteError",
    "SchemaError",
    "BigQueryLoader",
]
