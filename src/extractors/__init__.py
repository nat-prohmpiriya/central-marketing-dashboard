"""Extractors package for data extraction from various platforms."""

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
    ExtractorError,
    RateLimitError,
    RateLimiter,
)
from src.extractors.lazada import LazadaExtractor
from src.extractors.shopee import ShopeeExtractor
from src.extractors.tiktok_shop import TikTokShopExtractor

__all__ = [
    "BaseExtractor",
    "ExtractorError",
    "AuthenticationError",
    "RateLimitError",
    "APIError",
    "RateLimiter",
    "ShopeeExtractor",
    "LazadaExtractor",
    "TikTokShopExtractor",
]
