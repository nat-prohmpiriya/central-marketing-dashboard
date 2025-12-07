"""Extractors package for data extraction from various platforms."""

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
    ExtractorError,
    RateLimitError,
    RateLimiter,
)

# E-commerce extractors
from src.extractors.lazada import LazadaExtractor
from src.extractors.shopee import ShopeeExtractor
from src.extractors.tiktok_shop import TikTokShopExtractor

# Ads & Analytics extractors
from src.extractors.facebook_ads import FacebookAdsExtractor
from src.extractors.ga4 import GA4Extractor
from src.extractors.google_ads import GoogleAdsExtractor
from src.extractors.lazada_ads import LazadaAdsExtractor
from src.extractors.line_ads import LINEAdsExtractor
from src.extractors.shopee_ads import ShopeeAdsExtractor
from src.extractors.tiktok_ads import TikTokAdsExtractor

__all__ = [
    # Base
    "BaseExtractor",
    "ExtractorError",
    "AuthenticationError",
    "RateLimitError",
    "APIError",
    "RateLimiter",
    # E-commerce
    "ShopeeExtractor",
    "LazadaExtractor",
    "TikTokShopExtractor",
    # Ads & Analytics
    "FacebookAdsExtractor",
    "GoogleAdsExtractor",
    "TikTokAdsExtractor",
    "GA4Extractor",
    "LINEAdsExtractor",
    "ShopeeAdsExtractor",
    "LazadaAdsExtractor",
]
