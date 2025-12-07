"""ETL Pipelines package for orchestrating data flows."""

from src.pipelines.base import (
    BasePipeline,
    PipelineError,
    PipelineResult,
    PipelineStage,
)

# Lazy imports to avoid circular dependencies
try:
    from src.pipelines.ecommerce_pipeline import EcommercePipeline
except ImportError:
    EcommercePipeline = None  # type: ignore[misc, assignment]

try:
    from src.pipelines.ads_pipeline import AdsPipeline
except ImportError:
    AdsPipeline = None  # type: ignore[misc, assignment]

try:
    from src.pipelines.product_pipeline import ProductPipeline
except ImportError:
    ProductPipeline = None  # type: ignore[misc, assignment]

__all__ = [
    "BasePipeline",
    "PipelineError",
    "PipelineResult",
    "PipelineStage",
    "EcommercePipeline",
    "AdsPipeline",
    "ProductPipeline",
]
