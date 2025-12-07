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

try:
    from src.pipelines.mart_pipeline import (
        MartPipeline,
        MartPipelineResult,
        MartRefreshResult,
        MartTable,
    )
except ImportError:
    MartPipeline = None  # type: ignore[misc, assignment]
    MartPipelineResult = None  # type: ignore[misc, assignment]
    MartRefreshResult = None  # type: ignore[misc, assignment]
    MartTable = None  # type: ignore[misc, assignment]

try:
    from src.pipelines.alerts_pipeline import (
        AlertsPipeline,
        AlertsPipelineResult,
        AlertsRefreshResult,
    )
except ImportError:
    AlertsPipeline = None  # type: ignore[misc, assignment]
    AlertsPipelineResult = None  # type: ignore[misc, assignment]
    AlertsRefreshResult = None  # type: ignore[misc, assignment]

__all__ = [
    "BasePipeline",
    "PipelineError",
    "PipelineResult",
    "PipelineStage",
    "EcommercePipeline",
    "AdsPipeline",
    "ProductPipeline",
    "MartPipeline",
    "MartPipelineResult",
    "MartRefreshResult",
    "MartTable",
    "AlertsPipeline",
    "AlertsPipelineResult",
    "AlertsRefreshResult",
]
