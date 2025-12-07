"""Configuration management module."""

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # GCP Settings
    gcp_project_id: str = Field(default="", description="Google Cloud Project ID")
    gcp_region: str = Field(default="asia-southeast1", description="GCP region")
    bigquery_dataset_raw: str = Field(default="raw", description="BigQuery raw dataset")
    bigquery_dataset_staging: str = Field(default="staging", description="BigQuery staging dataset")
    bigquery_dataset_mart: str = Field(default="mart", description="BigQuery mart dataset")
    gcs_staging_bucket: str = Field(default="", description="GCS bucket for staging")

    # Shopee API
    shopee_partner_id: str = Field(default="", description="Shopee Partner ID")
    shopee_partner_key: str = Field(default="", description="Shopee Partner Key")
    shopee_shop_id: str = Field(default="", description="Shopee Shop ID")
    shopee_access_token: str = Field(default="", description="Shopee Access Token")
    shopee_refresh_token: str = Field(default="", description="Shopee Refresh Token")

    # Lazada API
    lazada_app_key: str = Field(default="", description="Lazada App Key")
    lazada_app_secret: str = Field(default="", description="Lazada App Secret")
    lazada_access_token: str = Field(default="", description="Lazada Access Token")
    lazada_refresh_token: str = Field(default="", description="Lazada Refresh Token")

    # TikTok Shop API
    tiktok_shop_app_key: str = Field(default="", description="TikTok Shop App Key")
    tiktok_shop_app_secret: str = Field(default="", description="TikTok Shop App Secret")
    tiktok_shop_access_token: str = Field(default="", description="TikTok Shop Access Token")

    # LINE Ads API
    line_ads_access_token: str = Field(default="", description="LINE Ads Access Token")
    line_ads_access_key: str = Field(default="", description="LINE Ads Access Key")
    line_ads_secret_key: str = Field(default="", description="LINE Ads Secret Key")
    line_ads_ad_account_id: str = Field(default="", description="LINE Ads Ad Account ID")

    # Facebook Ads API
    facebook_app_id: str = Field(default="", description="Facebook App ID")
    facebook_app_secret: str = Field(default="", description="Facebook App Secret")
    facebook_access_token: str = Field(default="", description="Facebook Access Token")
    facebook_ad_account_id: str = Field(default="", description="Facebook Ad Account ID")

    # Google Ads API
    google_ads_developer_token: str = Field(default="", description="Google Ads Developer Token")
    google_ads_client_id: str = Field(default="", description="Google Ads OAuth Client ID")
    google_ads_client_secret: str = Field(default="", description="Google Ads OAuth Client Secret")
    google_ads_refresh_token: str = Field(default="", description="Google Ads OAuth Refresh Token")
    google_ads_customer_id: str = Field(default="", description="Google Ads Customer ID")
    google_ads_login_customer_id: str = Field(default="", description="Google Ads Manager Account ID (optional)")

    # TikTok Ads API
    tiktok_ads_app_id: str = Field(default="", description="TikTok Ads App ID")
    tiktok_ads_app_secret: str = Field(default="", description="TikTok Ads App Secret")
    tiktok_ads_access_token: str = Field(default="", description="TikTok Ads Access Token")
    tiktok_ads_advertiser_id: str = Field(default="", description="TikTok Ads Advertiser ID")

    # GA4 (Google Analytics 4)
    ga4_property_id: str = Field(default="", description="GA4 Property ID")
    ga4_credentials_path: str = Field(default="", description="Path to GA4 service account JSON file")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or console")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def load_yaml_config(file_path: str | Path) -> dict[str, Any]:
    """Load configuration from a YAML file.

    Args:
        file_path: Path to the YAML configuration file.

    Returns:
        Dictionary containing the configuration.

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        yaml.YAMLError: If the YAML file is invalid.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_platform_config() -> dict[str, Any]:
    """Load platform configuration from config/platforms.yaml."""
    config_path = Path(__file__).parent.parent.parent / "config" / "platforms.yaml"
    if config_path.exists():
        return load_yaml_config(config_path)
    return {}


# Rate limits configuration (can be overridden by platforms.yaml)
DEFAULT_RATE_LIMITS = {
    "shopee": {
        "requests_per_minute": 60,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "lazada": {
        "requests_per_minute": 50,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "tiktok_shop": {
        "requests_per_minute": 100,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "line_ads": {
        "requests_per_minute": 60,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "facebook_ads": {
        "requests_per_minute": 200,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "google_ads": {
        "requests_per_minute": 100,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "tiktok_ads": {
        "requests_per_minute": 100,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "ga4": {
        "requests_per_minute": 60,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "shopee_ads": {
        "requests_per_minute": 60,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
    "lazada_ads": {
        "requests_per_minute": 50,
        "retry_after_seconds": 60,
        "max_retries": 3,
    },
}


def get_rate_limits(platform: str) -> dict[str, int]:
    """Get rate limit configuration for a platform.

    Args:
        platform: Platform name (shopee, lazada, tiktok_shop, etc.)

    Returns:
        Dictionary with rate limit settings.
    """
    platform_config = load_platform_config()
    rate_limits = platform_config.get("rate_limits", {})
    return rate_limits.get(platform, DEFAULT_RATE_LIMITS.get(platform, {}))
