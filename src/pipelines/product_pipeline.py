"""Product ETL pipeline for product catalog and SKU mapping."""

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
    LazadaProductTransformer,
    ShopeeProductTransformer,
    SKUMapper,
    TikTokProductTransformer,
    UnifiedProductTransformer,
)


class ProductPipeline(BasePipeline):
    """Pipeline for extracting, transforming, and loading product data.

    Supports:
    - Shopee products
    - Lazada products
    - TikTok Shop products

    Features:
    - Product catalog sync
    - SKU mapping management
    - Cross-platform product matching

    Flow:
    1. Extract products from all configured platforms
    2. Transform to unified product format
    3. Load raw data to BigQuery raw layer
    4. Load transformed data to BigQuery staging layer
    5. Update SKU mappings
    """

    pipeline_name = "product"

    def __init__(
        self,
        start_date: datetime,
        end_date: datetime,
        batch_id: str | None = None,
        platforms: list[str] | None = None,
        update_sku_mappings: bool = True,
    ):
        """Initialize product pipeline.

        Args:
            start_date: Start date for data extraction.
            end_date: End date for data extraction.
            batch_id: Optional batch identifier.
            platforms: List of platforms to extract from.
                       Default: ["shopee", "lazada", "tiktok_shop"]
            update_sku_mappings: Whether to update SKU mappings after load.
        """
        super().__init__(start_date, end_date, batch_id)

        self.platforms = platforms or ["shopee", "lazada", "tiktok_shop"]
        self.update_sku_mappings = update_sku_mappings

        # Initialize extractors
        self._extractors: dict[str, Any] = {}
        self._transformers: dict[str, Any] = {}

        if "shopee" in self.platforms:
            self._extractors["shopee"] = ShopeeExtractor()
            self._transformers["shopee"] = ShopeeProductTransformer()

        if "lazada" in self.platforms:
            self._extractors["lazada"] = LazadaExtractor()
            self._transformers["lazada"] = LazadaProductTransformer()

        if "tiktok_shop" in self.platforms:
            self._extractors["tiktok_shop"] = TikTokShopExtractor()
            self._transformers["tiktok_shop"] = TikTokProductTransformer()

        # Unified transformer and SKU mapper
        self._unified_transformer = UnifiedProductTransformer()
        self._sku_mapper = SKUMapper()

        # Loaders
        self._raw_loader: RawDataLoader | None = None
        self._staging_loader: StagingDataLoader | None = None

        # SKU mapping records generated during transform
        self._sku_mappings: list[dict[str, Any]] = []

    def extract(self) -> list[dict[str, Any]]:
        """Extract products from all configured e-commerce platforms.

        Returns:
            List of raw product records with platform metadata.
        """
        all_records: list[dict[str, Any]] = []

        for platform, extractor in self._extractors.items():
            try:
                self.logger.info(f"Extracting products from {platform}")

                with extractor:
                    # Use extract_products method if available
                    if hasattr(extractor, "extract_products"):
                        products = extractor.extract_products()
                    else:
                        # Fallback to generic extract with product type
                        products = extractor.extract(
                            start_date=self.start_date,
                            end_date=self.end_date,
                            extract_type="products",
                        )

                    for record in products:
                        all_records.append({
                            "platform": platform,
                            "data": record,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                            "batch_id": self.batch_id,
                        })

                platform_count = len(
                    [r for r in all_records if r["platform"] == platform]
                )
                self.logger.info(
                    f"Extracted products from {platform}",
                    count=platform_count,
                )

            except Exception as e:
                self.logger.error(
                    f"Failed to extract products from {platform}",
                    error=str(e),
                )
                if self._result:
                    self._result.errors.append({
                        "stage": PipelineStage.EXTRACT.value,
                        "platform": platform,
                        "message": str(e),
                    })

        if not all_records:
            self.logger.warning("No products extracted from any platform")

        return all_records

    def transform(
        self, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Transform raw products to unified format.

        Args:
            records: Raw product records with platform metadata.

        Returns:
            List of unified product records.
        """
        transformed_records: list[dict[str, Any]] = []
        self._sku_mappings = []

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

                    # Generate SKU mapping if we have platform SKU
                    platform_sku = transformed.get("platform_sku") or transformed.get("sku")
                    if platform_sku:
                        self._sku_mappings.append({
                            "platform": platform,
                            "platform_sku": platform_sku,
                            "platform_product_id": transformed.get("product_id", ""),
                            "product_name": transformed.get("name", ""),
                            "master_sku": None,  # Will be resolved later
                        })

                error_records = transformer.get_error_records()
                if error_records:
                    self.logger.warning(
                        f"Transform errors for {platform}",
                        error_count=len(error_records),
                    )

            except Exception as e:
                self.logger.error(
                    f"Failed to transform {platform} products",
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

            # Apply SKU mapping to get master SKUs
            if self.update_sku_mappings:
                self._resolve_sku_mappings(unified_records)

            return unified_records

        except Exception as e:
            self.logger.error("Unified product transformation failed", error=str(e))
            return transformed_records

    def _resolve_sku_mappings(
        self, products: list[dict[str, Any]]
    ) -> None:
        """Resolve master SKUs for products using SKU mapper.

        Args:
            products: List of transformed products.
        """
        for mapping in self._sku_mappings:
            platform = mapping.get("platform", "")
            platform_sku = mapping.get("platform_sku", "")

            if not platform or not platform_sku:
                continue

            try:
                # Try to find existing master SKU
                master_sku = self._sku_mapper.get_master_sku(platform, platform_sku)
                if master_sku:
                    mapping["master_sku"] = master_sku
                else:
                    # Generate new master SKU based on product name
                    product_name = mapping.get("product_name", "")
                    suggested_sku = self._generate_master_sku(
                        platform_sku, product_name
                    )
                    mapping["master_sku"] = suggested_sku
                    mapping["is_new"] = True

            except Exception as e:
                self.logger.warning(
                    "Failed to resolve master SKU",
                    platform=platform,
                    platform_sku=platform_sku,
                    error=str(e),
                )

    def _generate_master_sku(self, platform_sku: str, product_name: str) -> str:
        """Generate a suggested master SKU.

        Args:
            platform_sku: Platform-specific SKU.
            product_name: Product name.

        Returns:
            Suggested master SKU.
        """
        # Simple logic: use platform SKU if it looks like a standard SKU
        if platform_sku and len(platform_sku) <= 20 and "-" in platform_sku:
            return platform_sku.upper()

        # Otherwise, generate from product name
        if product_name:
            # Take first 3 words, first 2 letters each
            words = product_name.split()[:3]
            prefix = "".join(w[:2].upper() for w in words if w)
            return f"{prefix}-{platform_sku[:8].upper()}" if platform_sku else prefix

        return platform_sku.upper() if platform_sku else "UNKNOWN"

    def load_raw(self, records: list[dict[str, Any]]) -> int:
        """Load raw product data to BigQuery raw layer.

        Args:
            records: Raw product records.

        Returns:
            Number of records loaded.
        """
        if not records:
            return 0

        try:
            self._raw_loader = RawDataLoader()
            self._raw_loader.set_batch_id(self.batch_id)

            loaded = self._raw_loader.load_raw_products(records)
            return loaded

        except Exception as e:
            raise PipelineError(
                message=f"Failed to load raw products: {e}",
                pipeline=self.pipeline_name,
                stage=PipelineStage.LOAD_RAW,
                details={"error": str(e)},
            )
        finally:
            if self._raw_loader:
                self._raw_loader.close()

    def load_staging(self, records: list[dict[str, Any]]) -> int:
        """Load transformed products to BigQuery staging layer.

        Also loads SKU mappings if update_sku_mappings is enabled.

        Args:
            records: Transformed product records.

        Returns:
            Number of records loaded.
        """
        if not records:
            return 0

        total_loaded = 0

        try:
            self._staging_loader = StagingDataLoader()

            # Load products
            loaded = self._staging_loader.load_products(records)
            total_loaded += loaded
            self.logger.info("Loaded staging products", count=loaded)

            # Load SKU mappings
            if self.update_sku_mappings and self._sku_mappings:
                # Filter out incomplete mappings
                valid_mappings = [
                    m for m in self._sku_mappings
                    if m.get("master_sku") and m.get("platform_sku")
                ]

                if valid_mappings:
                    loaded = self._staging_loader.load_sku_mappings(valid_mappings)
                    self.logger.info("Loaded SKU mappings", count=loaded)

                    # Add to metadata
                    if self._result:
                        new_mappings = len([m for m in valid_mappings if m.get("is_new")])
                        self._result.metadata["sku_mappings_loaded"] = loaded
                        self._result.metadata["new_sku_mappings"] = new_mappings

            return total_loaded

        except Exception as e:
            raise PipelineError(
                message=f"Failed to load staging products: {e}",
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

        self._sku_mappings = []

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
