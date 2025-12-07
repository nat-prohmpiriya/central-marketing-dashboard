"""Pytest configuration for loader tests.

This module sets up mocking for google.cloud.bigquery to avoid
conflicts with other tests that mock google.analytics.
"""

import sys
from unittest.mock import MagicMock

import pytest


# Store original google module if it exists
_original_google = sys.modules.get("google")


@pytest.fixture(autouse=True)
def isolate_google_modules():
    """Isolate google modules for each test."""
    # Save current state
    google_modules = {
        key: mod for key, mod in sys.modules.items()
        if key == "google" or key.startswith("google.")
    }

    yield

    # Restore original state after test
    # Remove any google modules added during test
    for key in list(sys.modules.keys()):
        if key == "google" or key.startswith("google."):
            if key in google_modules:
                sys.modules[key] = google_modules[key]
            else:
                del sys.modules[key]


@pytest.fixture
def mock_bigquery():
    """Create mock bigquery module."""
    mock_bq = MagicMock()
    mock_bq.SchemaField = MagicMock
    mock_bq.Client = MagicMock
    mock_bq.Table = MagicMock
    mock_bq.TimePartitioning = MagicMock
    mock_bq.LoadJobConfig = MagicMock
    mock_bq.SourceFormat = MagicMock()
    mock_bq.SourceFormat.NEWLINE_DELIMITED_JSON = "NEWLINE_DELIMITED_JSON"
    mock_bq.WriteDisposition = MagicMock()
    mock_bq.WriteDisposition.WRITE_APPEND = "WRITE_APPEND"
    return mock_bq
