"""E-commerce ETL pipeline for order data."""

from datetime import datetime, timezone
from typing import Any

from src.extractors import (
    LazadaExtractor,
    ShopeeExtractor,
    TikTokShopExtractor,
)
from src.loaders import RawDataLoader, StagingDataLoader
from src.pipelines.base import BasePipeline, PipelineError, PipelineStage
from src.transformers import (
    LazadaOrderTransformer,
    ShopeeOrderTransformer,
    TikTokOrderTransformer,
    UnifiedOrderTransformer,
)


class EcommercePipeline(BasePipeline):
    """Pipeline for extracting, transforming, and loading e-commerce order data.

    Supports:
    - Shopee orders
    - Lazada orders
    - TikTok Shop orders

    Flow:
    1. Extract orders from all configured platforms
    2. Transform to unified order format
    3. Load raw data to BigQuery raw layer
    4. Load transformed data to BigQuery staging layer
    """

    pipeline_name = "ecommerce"

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        batch_id: str | None = None,
        platforms: list[str] | None = None,
    ):
        """Initialize e-commerce pipeline.

        Args:
            start_date: Start date for data extraction.
            end_date: End date for data extraction.
            batch_id: Optional batch identifier.
            platforms: List of platforms to extract from.
                       Default: ["shopee", "lazada", "tiktok_shop"]
        """
        super().__init__(start_date, end_date, batch_id)

        self.platforms = platforms or ["shopee", "lazada", "tiktok_shop"]

        # Initialize extractors
        self._extractors: dict[str, Any] = {}
        self._transformers: dict[str, Any] = {}

        # Initialize based on configured platforms
        if "shopee" in self.platforms:
            self._extractors["shopee"] = ShopeeExtractor()
            self._transformers["shopee"] = ShopeeOrderTransformer()

        if "lazada" in self.platforms:
            self._extractors["lazada"] = LazadaExtractor()
            self._transformers["lazada"] = LazadaOrderTransformer()

        if "tiktok_shop" in self.platforms:
            self._extractors["tiktok_shop"] = TikTokShopExtractor()
            self._transformers["tiktok_shop"] = TikTokOrderTransformer()

        # Unified transformer for final output
        self._unified_transformer = UnifiedOrderTransformer()

        # Loaders
        self._raw_loader: RawDataLoader | None = None
        self._staging_loader: StagingDataLoader | None = None

    def extract(self) -> list[dict[str, Any]]:
        """Extract orders from all configured e-commerce platforms.

        Returns:
            List of raw order records with platform metadata.
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
                        # Add platform metadata
                        all_records.append({
                            "platform": platform,
                            "data": record,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            "batch_id": self.batch_id,
                        })

                self.logger.info(
                    f"Extracted from {platform}",
                    count=len([r for r in all_records if r["platform"] == platform]),
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to extract from {platform}",
                    error=str(e),
                )
                # Continue with other platforms
                if self._result:
                    self._result.errors.append({
                        "stage": PipelineStage.EXTRACT.value,
                        "platform": platform,
                        "message": str(e),
                    })

        if not all_records:
            self.logger.warning("No records extracted from any platform")

        return all_records

    def transform(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform raw orders to unified format.

        Args:
            records: Raw order records with platform metadata.

        Returns:
            List of unified order records.
        """
        transformed_records: list[dict[str, Any]] = []

        # Group records by platform
        platform_records: dict[str, list[dict[str, Any]]] = {}
        for record in records:
            platform = record.get("platform", "unknown")
            if platform not in platform_records:
                platform_records[platform] = []
            platform_records[platform].append(record.get("data", record))

        # Transform each platform's records
        for platform, platform_data in platform_records.items():
            transformer = self._transformers.get(platform)
            if transformer is None:
                self.logger.warning(f"No transformer for platform: {platform}")
                continue

            try:
                for transformed in transformer.transform(platform_data):
                    transformed_records.append(transformed)

                # Log any errors from transformer
                error_records = transformer.get_error_records()
                if error_records:
                    self.logger.warning(
                        f"Transform errors for {platform}",
                        error_count=len(error_records),
                    )
                    if self._result:
                        self._result.errors.extend([
                            {
                                "stage": PipelineStage.TRANSFORM.value,
                                "platform": platform,
                                **err,
                            }
                            for err in error_records
                        ])

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

        # Apply unified transformation (cross-platform logic)
        try:
            unified_records = list(
                self._unified_transformer.transform(transformed_records)
            )
            return unified_records
        except Exception as e:
            self.logger.error("Unified transformation failed", error=str(e))
            # Return platform-transformed records if unified fails
            return transformed_records

    def load_raw(self, records: list[dict[str, Any]]) -> int:
        """Load raw order data to BigQuery raw layer.

        Args:
            records: Raw order records.

        Returns:
            Number of records loaded.
        """
        if not records:
            return 0

        try:
            self._raw_loader = RawDataLoader()
            self._raw_loader.set_batch_id(self.batch_id)

            loaded = self._raw_loader.load_raw_orders(records)
            return loaded

        except Exception as e:
            raise PipelineError(
                message=f"Failed to load raw orders: {e}",
                pipeline=self.pipeline_name,
                stage=PipelineStage.LOAD_RAW,
                details={"error": str(e)},
            )
        finally:
            if self._raw_loader:
                self._raw_loader.close()

    def load_staging(self, records: list[dict[str, Any]]) -> int:
        """Load transformed orders to BigQuery staging layer.

        Args:
            records: Transformed order records.

        Returns:
            Number of records loaded.
        """
        if not records:
            return 0

        try:
            self._staging_loader = StagingDataLoader()

            loaded = self._staging_loader.load_orders(records)
            return loaded

        except Exception as e:
            raise PipelineError(
                message=f"Failed to load staging orders: {e}",
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

        # Close any remaining connections
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
