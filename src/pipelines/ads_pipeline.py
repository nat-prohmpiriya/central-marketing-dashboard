"""Ads ETL pipeline for advertising data."""

from datetime import datetime, timezone
from typing import Any

from src.extractors import (
    FacebookAdsExtractor,
    GA4Extractor,
    GoogleAdsExtractor,
    LazadaAdsExtractor,
    LINEAdsExtractor,
    ShopeeAdsExtractor,
    TikTokAdsExtractor,
)
from src.loaders import RawDataLoader, StagingDataLoader
from src.pipelines.base import BasePipeline, PipelineError, PipelineStage
from src.transformers import (
    FacebookAdsTransformer,
    GoogleAdsTransformer,
    TikTokAdsTransformer,
    UnifiedAdsTransformer,
    UnifiedGA4Transformer,
)


class AdsPipeline(BasePipeline):
    """Pipeline for extracting, transforming, and loading advertising data.

    Supports:
    - Facebook Ads
    - Google Ads
    - TikTok Ads
    - LINE Ads
    - Shopee Ads
    - Lazada Ads
    - GA4 Analytics

    Flow:
    1. Extract ads data from all configured platforms
    2. Transform to unified ads/analytics format
    3. Load raw data to BigQuery raw layer
    4. Load transformed data to BigQuery staging layer
    """

    pipeline_name = "ads"

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        batch_id: str | None = None,
        platforms: list[str] | None = None,
        include_ga4: bool = True,
    ):
        """Initialize ads pipeline.

        Args:
            start_date: Start date for data extraction.
            end_date: End date for data extraction.
            batch_id: Optional batch identifier.
            platforms: List of ad platforms to extract from.
                       Default: ["facebook_ads", "google_ads", "tiktok_ads"]
            include_ga4: Whether to include GA4 analytics data.
        """
        super().__init__(start_date, end_date, batch_id)

        self.platforms = platforms or [
            "facebook_ads",
            "google_ads",
            "tiktok_ads",
            "line_ads",
            "shopee_ads",
            "lazada_ads",
        ]
        self.include_ga4 = include_ga4

        # Initialize extractors
        self._extractors: dict[str, Any] = {}
        self._transformers: dict[str, Any] = {}

        # Ads extractors
        if "facebook_ads" in self.platforms:
            self._extractors["facebook_ads"] = FacebookAdsExtractor()
            self._transformers["facebook_ads"] = FacebookAdsTransformer()

        if "google_ads" in self.platforms:
            self._extractors["google_ads"] = GoogleAdsExtractor()
            self._transformers["google_ads"] = GoogleAdsTransformer()

        if "tiktok_ads" in self.platforms:
            self._extractors["tiktok_ads"] = TikTokAdsExtractor()
            self._transformers["tiktok_ads"] = TikTokAdsTransformer()

        if "line_ads" in self.platforms:
            self._extractors["line_ads"] = LINEAdsExtractor()
            # LINE Ads uses Facebook transformer (similar structure)
            self._transformers["line_ads"] = FacebookAdsTransformer()

        if "shopee_ads" in self.platforms:
            self._extractors["shopee_ads"] = ShopeeAdsExtractor()
            # Shopee Ads may need custom transformer
            self._transformers["shopee_ads"] = FacebookAdsTransformer()

        if "lazada_ads" in self.platforms:
            self._extractors["lazada_ads"] = LazadaAdsExtractor()
            # Lazada Ads may need custom transformer
            self._transformers["lazada_ads"] = FacebookAdsTransformer()

        # GA4 extractor
        if self.include_ga4:
            self._extractors["ga4"] = GA4Extractor()
            self._transformers["ga4"] = UnifiedGA4Transformer()

        # Unified transformer for ads
        self._unified_ads_transformer = UnifiedAdsTransformer()

        # Loaders
        self._raw_loader: RawDataLoader | None = None
        self._staging_loader: StagingDataLoader | None = None

        # Separate storage for different data types
        self._ads_records: list[dict[str, Any]] = []
        self._ga4_records: list[dict[str, Any]] = []

    def extract(self) -> list[dict[str, Any]]:
        """Extract ads and analytics data from all configured platforms.

        Returns:
            List of raw records with platform metadata.
        """
        all_records: list[dict[str, Any]] = []

        for platform, extractor in self._extractors.items():
            try:
                self.logger.info(f"Extracting from {platform}")

                with extractor:
                    for record in extractor.extract(
                        start_date=self.start_date,
                        end_date=self.end_date,
                    ):
                        data_type = "ga4" if platform == "ga4" else "ads"

                        all_records.append({
                            "platform": platform,
                            "data_type": data_type,
                            "data": record,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            "batch_id": self.batch_id,
                        })

                platform_count = len(
                    [r for r in all_records if r["platform"] == platform]
                )
                self.logger.info(
                    f"Extracted from {platform}",
                    count=platform_count,
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to extract from {platform}",
                    error=str(e),
                )
                if self._result:
                    self._result.errors.append({
                        "stage": PipelineStage.EXTRACT.value,
                        "platform": platform,
                        "message": str(e),
                    })

        if not all_records:
            self.logger.warning("No records extracted from any platform")

        # Separate records by type for later processing
        self._ads_records = [r for r in all_records if r.get("data_type") == "ads"]
        self._ga4_records = [r for r in all_records if r.get("data_type") == "ga4"]

        return all_records

    def transform(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform raw ads/analytics data to unified format.

        Args:
            records: Raw records with platform metadata.

        Returns:
            List of unified records.
        """
        transformed_records: list[dict[str, Any]] = []

        # Group ads records by platform
        ads_by_platform: dict[str, list[dict[str, Any]]] = {}
        for record in self._ads_records:
            platform = record.get("platform", "unknown")
            if platform not in ads_by_platform:
                ads_by_platform[platform] = []
            ads_by_platform[platform].append(record.get("data", record))

        # Transform ads data
        for platform, platform_data in ads_by_platform.items():
            if platform == "ga4":
                continue  # Handle GA4 separately

            transformer = self._transformers.get(platform)
            if transformer is None:
                self.logger.warning(f"No transformer for platform: {platform}")
                continue

            try:
                for transformed in transformer.transform(platform_data):
                    transformed["_data_type"] = "ads"
                    transformed_records.append(transformed)

                error_records = transformer.get_error_records()
                if error_records:
                    self.logger.warning(
                        f"Transform errors for {platform}",
                        error_count=len(error_records),
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to transform {platform} records",
                    error=str(e),
                )
                if self._result:
                    self._result.errors.append({
                        "stage": PipelineStage.TRANSFORM.value,
                        "platform": platform,
                        "message": str(e),
                    })

        # Transform GA4 data
        if self._ga4_records:
            ga4_data = [r.get("data", r) for r in self._ga4_records]
            ga4_transformer = self._transformers.get("ga4")

            if ga4_transformer:
                try:
                    for transformed in ga4_transformer.transform(ga4_data):
                        transformed["_data_type"] = "ga4"
                        transformed_records.append(transformed)
                except Exception as e:
                    self.logger.error("Failed to transform GA4 records", error=str(e))
                    if self._result:
                        self._result.errors.append({
                            "stage": PipelineStage.TRANSFORM.value,
                            "platform": "ga4",
                            "message": str(e),
                        })

        # Apply unified ads transformation
        ads_only = [r for r in transformed_records if r.get("_data_type") == "ads"]
        if ads_only:
            try:
                unified_ads = list(
                    self._unified_ads_transformer.transform(ads_only)
                )
                # Replace ads records with unified version
                transformed_records = [
                    r for r in transformed_records if r.get("_data_type") != "ads"
                ]
                transformed_records.extend(unified_ads)
            except Exception as e:
                self.logger.error("Unified ads transformation failed", error=str(e))

        return transformed_records

    def load_raw(self, records: list[dict[str, Any]]) -> int:
        """Load raw ads data to BigQuery raw layer.

        Args:
            records: Raw records.

        Returns:
            Number of records loaded.
        """
        if not records:
            return 0

        total_loaded = 0

        try:
            self._raw_loader = RawDataLoader()
            self._raw_loader.set_batch_id(self.batch_id)

            # Load ads records
            if self._ads_records:
                loaded = self._raw_loader.load_raw_ads(self._ads_records)
                total_loaded += loaded
                self.logger.info("Loaded raw ads", count=loaded)

            # Load GA4 records
            if self._ga4_records:
                loaded = self._raw_loader.load_raw_ga4(self._ga4_records)
                total_loaded += loaded
                self.logger.info("Loaded raw GA4", count=loaded)

            return total_loaded

        except Exception as e:
            raise PipelineError(
                message=f"Failed to load raw ads data: {e}",
                pipeline=self.pipeline_name,
                stage=PipelineStage.LOAD_RAW,
                details={"error": str(e)},
            )
        finally:
            if self._raw_loader:
                self._raw_loader.close()

    def load_staging(self, records: list[dict[str, Any]]) -> int:
        """Load transformed ads data to BigQuery staging layer.

        Args:
            records: Transformed records.

        Returns:
            Number of records loaded.
        """
        if not records:
            return 0

        total_loaded = 0

        try:
            self._staging_loader = StagingDataLoader()

            # Separate by data type
            ads_records = [
                r for r in records
                if r.get("_data_type") == "ads" or "ad_id" in r or "campaign_id" in r
            ]
            ga4_records = [r for r in records if r.get("_data_type") == "ga4"]

            # Load ads
            if ads_records:
                # Remove internal type marker
                for r in ads_records:
                    r.pop("_data_type", None)
                loaded = self._staging_loader.load_ads(ads_records)
                total_loaded += loaded
                self.logger.info("Loaded staging ads", count=loaded)

            # Load GA4 sessions
            ga4_sessions = [r for r in ga4_records if "sessions" in r or "session" in str(r.get("record_id", ""))]
            if ga4_sessions:
                for r in ga4_sessions:
                    r.pop("_data_type", None)
                loaded = self._staging_loader.load_ga4_sessions(ga4_sessions)
                total_loaded += loaded
                self.logger.info("Loaded staging GA4 sessions", count=loaded)

            # Load GA4 traffic
            ga4_traffic = [r for r in ga4_records if "traffic" in str(r.get("record_id", "")) or "source" in r]
            if ga4_traffic:
                for r in ga4_traffic:
                    r.pop("_data_type", None)
                loaded = self._staging_loader.load_ga4_traffic(ga4_traffic)
                total_loaded += loaded
                self.logger.info("Loaded staging GA4 traffic", count=loaded)

            return total_loaded

        except Exception as e:
            raise PipelineError(
                message=f"Failed to load staging ads data: {e}",
                pipeline=self.pipeline_name,
                stage=PipelineStage.LOAD_STAGING,
                details={"error": str(e)},
            )
        finally:
            if self._staging_loader:
                self._staging_loader.close()

    def _cleanup(self) -> None:
        """Clean up resources."""
        super()._cleanup()

        self._ads_records = []
        self._ga4_records = []

        for extractor in self._extractors.values():
            try:
                extractor.close()
            except Exception:
                pass

        if self._raw_loader:
            try:
                self._raw_loader.close()
            except Exception:
                pass

        if self._staging_loader:
            try:
                self._staging_loader.close()
            except Exception:
                pass
