"""Logging configuration module using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from src.utils.config import get_settings


def setup_logging(
    level: str | None = None,
    log_format: str | None = None,
) -> None:
    """Configure structured logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses settings from environment.
        log_format: Output format ('json' or 'console').
                   If None, uses settings from environment.
    """
    settings = get_settings()
    level = level or settings.log_level
    log_format = log_format or settings.log_format

    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Shared processors for all formats
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        # JSON format for production/cloud logging
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format for development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Set level for third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name. If None, uses the caller's module name.

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind context variables to all subsequent log messages.

    Args:
        **kwargs: Key-value pairs to add to log context.

    Example:
        >>> bind_context(request_id="abc123", user_id="user456")
        >>> logger.info("Processing request")  # Will include request_id and user_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()


def unbind_context(*keys: str) -> None:
    """Remove specific context variables.

    Args:
        *keys: Keys to remove from context.
    """
    structlog.contextvars.unbind_contextvars(*keys)


# Convenience function to log ETL pipeline events
def log_pipeline_event(
    logger: structlog.stdlib.BoundLogger,
    event: str,
    pipeline: str,
    status: str,
    **extra: Any,
) -> None:
    """Log a pipeline event with standard fields.

    Args:
        logger: Logger instance.
        event: Event description.
        pipeline: Pipeline name.
        status: Status (started, completed, failed).
        **extra: Additional fields to log.
    """
    logger.info(
        event,
        pipeline=pipeline,
        status=status,
        **extra,
    )


def log_extraction_event(
    logger: structlog.stdlib.BoundLogger,
    platform: str,
    entity: str,
    records_count: int,
    status: str,
    **extra: Any,
) -> None:
    """Log a data extraction event.

    Args:
        logger: Logger instance.
        platform: Platform name (shopee, lazada, etc.).
        entity: Entity being extracted (orders, products, etc.).
        records_count: Number of records extracted.
        status: Status (started, completed, failed).
        **extra: Additional fields to log.
    """
    logger.info(
        f"extraction_{status}",
        platform=platform,
        entity=entity,
        records_count=records_count,
        **extra,
    )
