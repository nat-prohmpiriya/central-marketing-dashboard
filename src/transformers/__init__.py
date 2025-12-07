"""Transformers package for data transformation."""

from src.transformers.ads import (
    FacebookAdsTransformer,
    GoogleAdsTransformer,
    TikTokAdsTransformer,
    UnifiedAd,
    UnifiedAdsTransformer,
)
from src.transformers.base import (
    BaseTransformer,
    MappingError,
    TransformError,
)
from src.transformers.ga4 import (
    GA4Page,
    GA4PagesTransformer,
    GA4Session,
    GA4SessionsTransformer,
    GA4Traffic,
    GA4TrafficTransformer,
    UnifiedGA4Transformer,
)
from src.transformers.orders import (
    LazadaOrderTransformer,
    OrderItem,
    OrderItemTransformer,
    ShopeeOrderTransformer,
    TikTokOrderTransformer,
    UnifiedOrder,
    UnifiedOrderTransformer,
)
from src.transformers.products import (
    LazadaProductTransformer,
    ShopeeProductTransformer,
    TikTokProductTransformer,
    UnifiedProduct,
    UnifiedProductTransformer,
)
from src.transformers.sku_mapper import (
    SKUMapper,
    SKUMapping,
    SKUMappingNotFoundError,
)

__all__ = [
    # Base
    "BaseTransformer",
    "TransformError",
    "MappingError",
    # Orders
    "ShopeeOrderTransformer",
    "LazadaOrderTransformer",
    "TikTokOrderTransformer",
    "UnifiedOrderTransformer",
    "OrderItemTransformer",
    "UnifiedOrder",
    "OrderItem",
    # Ads
    "FacebookAdsTransformer",
    "GoogleAdsTransformer",
    "TikTokAdsTransformer",
    "UnifiedAdsTransformer",
    "UnifiedAd",
    # GA4
    "GA4SessionsTransformer",
    "GA4TrafficTransformer",
    "GA4PagesTransformer",
    "UnifiedGA4Transformer",
    "GA4Session",
    "GA4Traffic",
    "GA4Page",
    # Products
    "ShopeeProductTransformer",
    "LazadaProductTransformer",
    "TikTokProductTransformer",
    "UnifiedProductTransformer",
    "UnifiedProduct",
    # SKU Mapper
    "SKUMapper",
    "SKUMapping",
    "SKUMappingNotFoundError",
]
