"""Ads transformers for advertising platforms.

Transforms raw ads data from Facebook, Google, and TikTok Ads
to a unified staging format.
"""

from datetime import datetime, timezone
from typing import Any, Generator

from pydantic import BaseModel, Field

from src.transformers.base import BaseTransformer, MappingError


# Unified Ads Schema
class UnifiedAd(BaseModel):
    """Unified ad performance schema for all advertising platforms."""

    # Identifiers
    record_id: str
    platform: str
    account_id: str
    campaign_id: str
    campaign_name: str | None = None
    adgroup_id: str | None = None
    adgroup_name: str | None = None
    ad_id: str | None = None
    ad_name: str | None = None

    # Performance metrics
    impressions: int = 0
    clicks: int = 0
    reach: int | None = None
    ctr: float | None = None  # Click-through rate (%)
    cpc: float | None = None  # Cost per click
    cpm: float | None = None  # Cost per mille (1000 impressions)

    # Cost metrics (normalized to THB)
    spend: float = 0.0
    spend_raw: float = 0.0
    currency: str = "THB"
    currency_raw: str = "THB"

    # Conversion metrics
    conversions: int = 0
    conversion_value: float = 0.0
    cost_per_conversion: float | None = None
    conversion_rate: float | None = None

    # Video metrics
    video_views: int | None = None
    video_views_p25: int | None = None
    video_views_p50: int | None = None
    video_views_p75: int | None = None
    video_views_p100: int | None = None

    # Engagement metrics (for social platforms)
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    follows: int | None = None

    # Status and type
    status: str | None = None
    campaign_type: str | None = None
    objective: str | None = None

    # Date information
    date: datetime
    date_start: datetime | None = None
    date_end: datetime | None = None
    level: str = "ad"  # campaign, adgroup, ad

    # Metadata
    extracted_at: datetime | None = None
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Status mappings
FACEBOOK_STATUS_MAPPING = {
    "active": "active",
    "paused": "paused",
    "deleted": "deleted",
    "archived": "archived",
    "pending_review": "pending",
    "disapproved": "rejected",
    "preapproved": "pending",
    "campaign_paused": "paused",
    "adset_paused": "paused",
}

GOOGLE_STATUS_MAPPING = {
    "enabled": "active",
    "paused": "paused",
    "removed": "deleted",
    "unknown": "unknown",
}

TIKTOK_STATUS_MAPPING = {
    "enable": "active",
    "disable": "paused",
    "delete": "deleted",
    "status_enable": "active",
    "status_disable": "paused",
    "status_delete": "deleted",
}

# Campaign type mappings
FACEBOOK_CAMPAIGN_TYPE_MAPPING = {
    "link_clicks": "traffic",
    "conversions": "conversions",
    "app_installs": "app_install",
    "brand_awareness": "awareness",
    "reach": "reach",
    "video_views": "video",
    "lead_generation": "leads",
    "messages": "messages",
    "engagement": "engagement",
    "store_traffic": "store_visits",
    "catalog_sales": "sales",
    "outcome_awareness": "awareness",
    "outcome_engagement": "engagement",
    "outcome_leads": "leads",
    "outcome_sales": "sales",
    "outcome_traffic": "traffic",
    "outcome_app_promotion": "app_install",
}

GOOGLE_CAMPAIGN_TYPE_MAPPING = {
    "search": "search",
    "display": "display",
    "shopping": "shopping",
    "video": "video",
    "multi_channel": "performance_max",
    "smart": "smart",
    "local": "local",
    "hotel": "hotel",
    "performance_max": "performance_max",
    "demand_gen": "demand_gen",
}

TIKTOK_CAMPAIGN_TYPE_MAPPING = {
    "traffic": "traffic",
    "conversions": "conversions",
    "app_install": "app_install",
    "reach": "reach",
    "video_views": "video",
    "lead_generation": "leads",
    "catalog_sales": "sales",
}


class FacebookAdsTransformer(BaseTransformer):
    """Transform Facebook Ads insights to unified staging format."""

    source_platform = "facebook_ads"
    target_schema = UnifiedAd

    # USD to THB exchange rate (should be fetched dynamically in production)
    USD_TO_THB_RATE = 35.0

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform Facebook Ads records.

        Args:
            records: Raw Facebook Ads insight records.

        Yields:
            Transformed ad performance records.
        """
        for record in records:
            # Handle extractor wrapper format
            if record.get("type") in ("insight", "campaign", "adset", "ad"):
                raw_data = record.get("data", {})
                level = record.get("level", record.get("type", "ad"))
                account_id = record.get("ad_account_id", "")
            else:
                raw_data = record
                level = record.get("level", "ad")
                account_id = record.get("ad_account_id", "")

            # Set context for transformation
            self._current_level = level
            self._current_account_id = account_id

            transformed = self._transform_record(raw_data)
            if transformed:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map Facebook Ads fields to unified schema."""
        # Get identifiers
        campaign_id = record.get("campaign_id", "")
        adset_id = record.get("adset_id", "")
        ad_id = record.get("ad_id", "")

        # Create unique record ID based on level
        level = getattr(self, "_current_level", "ad")
        if level == "campaign":
            record_id = f"fb_{campaign_id}"
        elif level == "adset":
            record_id = f"fb_{campaign_id}_{adset_id}"
        else:
            record_id = f"fb_{campaign_id}_{adset_id}_{ad_id}"

        # Extract date from date_start or use current date
        date_start = record.get("date_start")
        date_end = record.get("date_end")

        # Parse actions for conversions
        actions = record.get("actions", [])
        conversions = self._extract_conversions(actions)

        # Parse cost per action
        cost_per_action = record.get("cost_per_action_type", [])
        cost_per_conversion = self._extract_cost_per_conversion(cost_per_action)

        # Extract video metrics
        video_p25 = self._extract_video_metric(record, "video_p25_watched_actions")
        video_p50 = self._extract_video_metric(record, "video_p50_watched_actions")
        video_p75 = self._extract_video_metric(record, "video_p75_watched_actions")
        video_p100 = self._extract_video_metric(record, "video_p100_watched_actions")

        return {
            "record_id": record_id,
            "platform": self.source_platform,
            "account_id": getattr(self, "_current_account_id", ""),
            "campaign_id": campaign_id,
            "campaign_name": record.get("campaign_name"),
            "adgroup_id": adset_id,
            "adgroup_name": record.get("adset_name"),
            "ad_id": ad_id,
            "ad_name": record.get("ad_name"),
            "impressions": int(record.get("impressions", 0) or 0),
            "clicks": int(record.get("clicks", 0) or 0),
            "reach": int(record.get("reach", 0) or 0) if record.get("reach") else None,
            "ctr": float(record.get("ctr", 0) or 0) if record.get("ctr") else None,
            "cpc": float(record.get("cpc", 0) or 0) if record.get("cpc") else None,
            "cpm": float(record.get("cpm", 0) or 0) if record.get("cpm") else None,
            "spend_raw": float(record.get("spend", 0) or 0),
            "currency_raw": "USD",  # Facebook reports in USD
            "conversions": conversions,
            "conversion_value": float(record.get("action_values", [{}])[0].get("value", 0)) if record.get("action_values") else 0.0,
            "cost_per_conversion": cost_per_conversion,
            "video_views_p25": video_p25,
            "video_views_p50": video_p50,
            "video_views_p75": video_p75,
            "video_views_p100": video_p100,
            "date_start": date_start,
            "date_end": date_end,
            "date": date_start,
            "level": level,
            "objective": record.get("objective"),
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_conversions(self, actions: list[dict[str, Any]]) -> int:
        """Extract conversion count from actions array."""
        total = 0
        conversion_types = [
            "purchase",
            "complete_registration",
            "lead",
            "add_to_cart",
            "add_payment_info",
            "initiate_checkout",
        ]

        for action in actions:
            action_type = action.get("action_type", "")
            if any(ct in action_type for ct in conversion_types):
                total += int(action.get("value", 0) or 0)

        return total

    def _extract_cost_per_conversion(self, cost_per_action: list[dict[str, Any]]) -> float | None:
        """Extract cost per conversion from cost_per_action array."""
        conversion_types = ["purchase", "complete_registration", "lead"]

        for cpa in cost_per_action:
            action_type = cpa.get("action_type", "")
            if any(ct in action_type for ct in conversion_types):
                return float(cpa.get("value", 0) or 0)

        return None

    def _extract_video_metric(self, record: dict[str, Any], field: str) -> int | None:
        """Extract video metric value from actions array."""
        actions = record.get(field, [])
        if actions and isinstance(actions, list) and len(actions) > 0:
            return int(actions[0].get("value", 0) or 0)
        return None

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize Facebook Ads values."""
        # Normalize currency (Facebook reports in USD)
        spend_usd = record.get("spend_raw", 0)
        record["spend"] = self.normalize_currency(
            spend_usd,
            source_currency="USD",
            target_currency="THB",
        )
        record["currency"] = "THB"

        # Also normalize cost per conversion if present
        if record.get("cost_per_conversion"):
            record["cost_per_conversion"] = self.normalize_currency(
                record["cost_per_conversion"],
                source_currency="USD",
                target_currency="THB",
            )

        # Also normalize CPC and CPM
        if record.get("cpc"):
            record["cpc"] = self.normalize_currency(
                record["cpc"],
                source_currency="USD",
                target_currency="THB",
            )

        if record.get("cpm"):
            record["cpm"] = self.normalize_currency(
                record["cpm"],
                source_currency="USD",
                target_currency="THB",
            )

        # Normalize dates
        for date_field in ["date", "date_start", "date_end"]:
            if record.get(date_field):
                record[date_field] = self.normalize_datetime(
                    record[date_field],
                    source_timezone="UTC",
                    target_timezone="Asia/Bangkok",
                )

        # Normalize status
        if record.get("status"):
            record["status"] = self.normalize_status(
                record["status"],
                FACEBOOK_STATUS_MAPPING,
            )

        # Normalize campaign type
        if record.get("objective"):
            record["campaign_type"] = self.normalize_status(
                record["objective"].lower(),
                FACEBOOK_CAMPAIGN_TYPE_MAPPING,
                default="other",
            )

        return record


class GoogleAdsTransformer(BaseTransformer):
    """Transform Google Ads data to unified staging format."""

    source_platform = "google_ads"
    target_schema = UnifiedAd

    # Google Ads uses micros (1/1,000,000 of currency unit)
    MICROS = 1_000_000

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform Google Ads records.

        Args:
            records: Raw Google Ads performance records.

        Yields:
            Transformed ad performance records.
        """
        for record in records:
            # Handle extractor wrapper format
            if record.get("type") in ("campaign", "adgroup", "ad", "keyword", "custom"):
                raw_data = record.get("data", {})
                level = record.get("type", "campaign")
                customer_id = record.get("customer_id", "")
            else:
                raw_data = record
                level = record.get("type", "campaign")
                customer_id = record.get("customer_id", "")

            # Set context for transformation
            self._current_level = level
            self._current_customer_id = customer_id

            transformed = self._transform_record(raw_data)
            if transformed:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map Google Ads fields to unified schema."""
        # Google Ads returns nested objects (campaign, adGroup, etc.)
        campaign = record.get("campaign", {})
        ad_group = record.get("adGroup", {})
        ad = record.get("adGroupAd", {}).get("ad", {})
        metrics = record.get("metrics", {})

        campaign_id = str(campaign.get("id", ""))
        adgroup_id = str(ad_group.get("id", ""))
        ad_id = str(ad.get("id", ""))

        # Create unique record ID based on level
        level = getattr(self, "_current_level", "campaign")
        if level == "campaign":
            record_id = f"gads_{campaign_id}"
        elif level == "adgroup":
            record_id = f"gads_{campaign_id}_{adgroup_id}"
        else:
            record_id = f"gads_{campaign_id}_{adgroup_id}_{ad_id}"

        # Get cost in micros and convert
        cost_micros = int(metrics.get("costMicros", 0) or 0)
        spend_raw = cost_micros / self.MICROS

        # Get average CPC in micros
        avg_cpc_micros = float(metrics.get("averageCpc", 0) or 0)
        cpc = avg_cpc_micros / self.MICROS if avg_cpc_micros else None

        # Get average CPM in micros
        avg_cpm_micros = float(metrics.get("averageCpm", 0) or 0)
        cpm = avg_cpm_micros / self.MICROS if avg_cpm_micros else None

        return {
            "record_id": record_id,
            "platform": self.source_platform,
            "account_id": getattr(self, "_current_customer_id", ""),
            "campaign_id": campaign_id,
            "campaign_name": campaign.get("name"),
            "adgroup_id": adgroup_id if adgroup_id else None,
            "adgroup_name": ad_group.get("name"),
            "ad_id": ad_id if ad_id else None,
            "ad_name": ad.get("name"),
            "impressions": int(metrics.get("impressions", 0) or 0),
            "clicks": int(metrics.get("clicks", 0) or 0),
            "ctr": float(metrics.get("ctr", 0) or 0) if metrics.get("ctr") else None,
            "cpc": cpc,
            "cpm": cpm,
            "spend_raw": spend_raw,
            "currency_raw": "THB",  # Assume Thai accounts report in THB
            "conversions": int(float(metrics.get("conversions", 0) or 0)),
            "conversion_value": float(metrics.get("conversionsValue", 0) or 0),
            "status": campaign.get("status", "").lower(),
            "campaign_type": campaign.get("advertisingChannelType", "").lower(),
            "date": record.get("date", record.get("extracted_at")),
            "level": level,
            "extracted_at": record.get("extracted_at"),
        }

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize Google Ads values."""
        # Currency is already in THB (assuming Thai Google Ads account)
        record["spend"] = record.get("spend_raw", 0)
        record["currency"] = "THB"

        # Calculate cost per conversion
        conversions = record.get("conversions", 0)
        spend = record.get("spend", 0)
        if conversions > 0 and spend > 0:
            record["cost_per_conversion"] = round(spend / conversions, 2)

        # Calculate conversion rate
        clicks = record.get("clicks", 0)
        if clicks > 0 and conversions > 0:
            record["conversion_rate"] = round((conversions / clicks) * 100, 2)

        # Normalize dates
        for date_field in ["date", "date_start", "date_end"]:
            if record.get(date_field):
                record[date_field] = self.normalize_datetime(
                    record[date_field],
                    source_timezone="UTC",
                    target_timezone="Asia/Bangkok",
                )

        # Normalize status
        if record.get("status"):
            record["status"] = self.normalize_status(
                record["status"],
                GOOGLE_STATUS_MAPPING,
            )

        # Normalize campaign type
        if record.get("campaign_type"):
            record["campaign_type"] = self.normalize_status(
                record["campaign_type"],
                GOOGLE_CAMPAIGN_TYPE_MAPPING,
                default="other",
            )

        return record


class TikTokAdsTransformer(BaseTransformer):
    """Transform TikTok Ads reports to unified staging format."""

    source_platform = "tiktok_ads"
    target_schema = UnifiedAd

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform TikTok Ads records.

        Args:
            records: Raw TikTok Ads report records.

        Yields:
            Transformed ad performance records.
        """
        for record in records:
            # Handle extractor wrapper format
            if record.get("type") in ("campaign", "adgroup", "ad"):
                raw_data = record.get("data", {})
                level = record.get("type", "ad")
                advertiser_id = record.get("advertiser_id", "")
            else:
                raw_data = record
                level = record.get("type", "ad")
                advertiser_id = record.get("advertiser_id", "")

            # Set context for transformation
            self._current_level = level
            self._current_advertiser_id = advertiser_id

            transformed = self._transform_record(raw_data)
            if transformed:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map TikTok Ads fields to unified schema."""
        # TikTok returns metrics in different format based on report type
        dimensions = record.get("dimensions", {})
        metrics = record.get("metrics", {})

        # Get identifiers from dimensions or record
        campaign_id = str(dimensions.get("campaign_id", record.get("campaign_id", "")))
        adgroup_id = str(dimensions.get("adgroup_id", record.get("adgroup_id", "")))
        ad_id = str(dimensions.get("ad_id", record.get("ad_id", "")))

        # Create unique record ID based on level
        level = getattr(self, "_current_level", "ad")
        stat_time = dimensions.get("stat_time_day", "")

        if level == "campaign":
            record_id = f"tiktok_{campaign_id}_{stat_time}"
        elif level == "adgroup":
            record_id = f"tiktok_{campaign_id}_{adgroup_id}_{stat_time}"
        else:
            record_id = f"tiktok_{campaign_id}_{adgroup_id}_{ad_id}_{stat_time}"

        # Get spend (TikTok reports in account currency, typically THB for Thai accounts)
        spend_raw = float(metrics.get("spend", 0) or 0)

        return {
            "record_id": record_id,
            "platform": self.source_platform,
            "account_id": getattr(self, "_current_advertiser_id", ""),
            "campaign_id": campaign_id,
            "campaign_name": record.get("campaign_name"),
            "adgroup_id": adgroup_id if adgroup_id else None,
            "adgroup_name": record.get("adgroup_name"),
            "ad_id": ad_id if ad_id else None,
            "ad_name": record.get("ad_name"),
            "impressions": int(metrics.get("impressions", 0) or 0),
            "clicks": int(metrics.get("clicks", 0) or 0),
            "reach": int(metrics.get("reach", 0) or 0) if metrics.get("reach") else None,
            "ctr": float(metrics.get("ctr", 0) or 0) if metrics.get("ctr") else None,
            "cpc": float(metrics.get("cpc", 0) or 0) if metrics.get("cpc") else None,
            "cpm": float(metrics.get("cpm", 0) or 0) if metrics.get("cpm") else None,
            "spend_raw": spend_raw,
            "currency_raw": "THB",
            "conversions": int(metrics.get("conversion", 0) or 0),
            "conversion_value": float(metrics.get("total_purchase_value", 0) or 0),
            "cost_per_conversion": float(metrics.get("cost_per_conversion", 0) or 0) if metrics.get("cost_per_conversion") else None,
            "conversion_rate": float(metrics.get("conversion_rate", 0) or 0) if metrics.get("conversion_rate") else None,
            # Video metrics
            "video_views": int(metrics.get("video_play_actions", 0) or 0) if metrics.get("video_play_actions") else None,
            "video_views_p25": int(metrics.get("video_views_p25", 0) or 0) if metrics.get("video_views_p25") else None,
            "video_views_p50": int(metrics.get("video_views_p50", 0) or 0) if metrics.get("video_views_p50") else None,
            "video_views_p75": int(metrics.get("video_views_p75", 0) or 0) if metrics.get("video_views_p75") else None,
            "video_views_p100": int(metrics.get("video_views_p100", 0) or 0) if metrics.get("video_views_p100") else None,
            # Engagement metrics
            "likes": int(metrics.get("likes", 0) or 0) if metrics.get("likes") else None,
            "comments": int(metrics.get("comments", 0) or 0) if metrics.get("comments") else None,
            "shares": int(metrics.get("shares", 0) or 0) if metrics.get("shares") else None,
            "follows": int(metrics.get("follows", 0) or 0) if metrics.get("follows") else None,
            "date": stat_time if stat_time else record.get("extracted_at"),
            "level": level,
            "extracted_at": record.get("extracted_at"),
        }

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize TikTok Ads values."""
        # TikTok reports in account currency (THB for Thai accounts)
        record["spend"] = record.get("spend_raw", 0)
        record["currency"] = "THB"

        # Normalize dates
        for date_field in ["date", "date_start", "date_end"]:
            if record.get(date_field):
                record[date_field] = self.normalize_datetime(
                    record[date_field],
                    source_timezone="UTC",
                    target_timezone="Asia/Bangkok",
                )

        # Normalize status
        if record.get("status"):
            record["status"] = self.normalize_status(
                record["status"],
                TIKTOK_STATUS_MAPPING,
            )

        return record


class UnifiedAdsTransformer(BaseTransformer):
    """Unified transformer that routes to platform-specific ads transformers."""

    source_platform = "unified_ads"
    target_schema = UnifiedAd

    def __init__(self):
        super().__init__()
        self._transformers = {
            "facebook_ads": FacebookAdsTransformer(),
            "google_ads": GoogleAdsTransformer(),
            "tiktok_ads": TikTokAdsTransformer(),
        }

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform ads from any supported platform.

        Args:
            records: Raw ads records with platform identifier.

        Yields:
            Transformed ads records.
        """
        for record in records:
            # Determine platform from record
            platform = record.get("platform") or self._detect_platform(record)

            if platform not in self._transformers:
                self.logger.warning(
                    "Unknown platform, skipping record",
                    platform=platform,
                )
                continue

            transformer = self._transformers[platform]

            # Transform using platform-specific transformer
            try:
                for transformed in transformer.transform([record]):
                    yield transformed
            except Exception as e:
                self.logger.error(
                    "Transform failed",
                    platform=platform,
                    error=str(e),
                )
                self._add_to_dead_letter(record, e)

    def _detect_platform(self, record: dict[str, Any]) -> str:
        """Detect platform from record structure.

        Args:
            record: Raw ads record.

        Returns:
            Platform name or 'unknown'.
        """
        data = record.get("data", record)

        # Facebook-specific fields
        if "adset_id" in data or "ad_account_id" in record:
            return "facebook_ads"

        # Google-specific fields
        if "costMicros" in data.get("metrics", {}) or "customer_id" in record:
            return "google_ads"

        # TikTok-specific fields
        if "advertiser_id" in record or "adgroup_id" in data.get("dimensions", {}):
            return "tiktok_ads"

        return "unknown"

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Not used directly - delegates to platform transformers."""
        return record

    def get_error_records(self) -> list[dict[str, Any]]:
        """Get all error records from all transformers."""
        errors = self._error_records.copy()
        for transformer in self._transformers.values():
            errors.extend(transformer.get_error_records())
        return errors

    def clear_error_records(self) -> None:
        """Clear error records from all transformers."""
        self._error_records = []
        for transformer in self._transformers.values():
            transformer.clear_error_records()
