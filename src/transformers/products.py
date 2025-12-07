"""Product transformers for e-commerce platforms.

Transforms raw product data from order items across Shopee, Lazada,
and TikTok Shop to a unified product format for SKU mapping and analytics.
"""

from datetime import datetime, timezone
from typing import Any, Generator

from pydantic import BaseModel, Field

from src.transformers.base import BaseTransformer, MappingError


class UnifiedProduct(BaseModel):
    """Unified product schema across all e-commerce platforms."""

    # Identifiers
    product_id: str
    platform: str
    platform_product_id: str

    # SKU information
    sku: str | None = None
    seller_sku: str | None = None
    master_sku: str | None = None  # Mapped unified SKU

    # Product details
    name: str
    variation: str | None = None
    category: str | None = None
    brand: str | None = None

    # Pricing
    unit_price: float = 0.0
    original_price: float | None = None
    discount_price: float | None = None
    currency: str = "THB"

    # Physical attributes
    weight: float | None = None
    weight_unit: str = "kg"

    # Status
    is_active: bool = True
    is_mapped: bool = False

    # Metadata
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    extracted_at: datetime | None = None
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ShopeeProductTransformer(BaseTransformer):
    """Transform Shopee product data from order items."""

    source_platform = "shopee"
    target_schema = UnifiedProduct

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform Shopee product records.

        Args:
            records: Raw Shopee order item records or product records.

        Yields:
            Transformed product records.
        """
        seen_products: set[str] = set()

        for record in records:
            # Handle order item format
            if record.get("type") == "order_item":
                raw_item = record.get("data", {})
            elif record.get("type") == "product":
                raw_item = record.get("data", {})
            else:
                raw_item = record

            # Skip duplicates
            product_key = self._get_product_key(raw_item)
            if product_key in seen_products:
                continue

            transformed = self._transform_record(raw_item)
            if transformed:
                seen_products.add(product_key)
                yield transformed

    def _get_product_key(self, record: dict[str, Any]) -> str:
        """Get unique product key for deduplication."""
        product_id = str(record.get("item_id", ""))
        sku = record.get("model_sku") or record.get("item_sku") or ""
        return f"shopee_{product_id}_{sku}"

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map Shopee fields to unified schema."""
        item_id = record.get("item_id")
        if not item_id:
            raise MappingError(
                message="Missing item_id",
                source_platform=self.source_platform,
                record=record,
            )

        return {
            "product_id": f"shopee_{item_id}",
            "platform": self.source_platform,
            "platform_product_id": str(item_id),
            "sku": record.get("model_sku") or record.get("item_sku"),
            "seller_sku": record.get("item_sku"),
            "master_sku": None,
            "name": record.get("item_name", ""),
            "variation": record.get("model_name"),
            "category": record.get("category_path"),
            "brand": record.get("brand"),
            "unit_price": float(
                record.get("model_discounted_price")
                or record.get("item_price", 0)
            ),
            "original_price": float(record.get("model_original_price", 0))
            if record.get("model_original_price")
            else None,
            "discount_price": float(record.get("model_discounted_price", 0))
            if record.get("model_discounted_price")
            else None,
            "currency": record.get("currency", "THB"),
            "weight": record.get("weight"),
            "weight_unit": "kg",
            "is_active": True,
            "is_mapped": False,
            "last_seen_at": datetime.now(timezone.utc),
            "extracted_at": record.get("extracted_at"),
        }


class LazadaProductTransformer(BaseTransformer):
    """Transform Lazada product data from order items."""

    source_platform = "lazada"
    target_schema = UnifiedProduct

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform Lazada product records.

        Args:
            records: Raw Lazada order item records or product records.

        Yields:
            Transformed product records.
        """
        seen_products: set[str] = set()

        for record in records:
            # Handle order item format
            if record.get("type") == "order_item":
                raw_item = record.get("data", {})
            elif record.get("type") == "product":
                raw_item = record.get("data", {})
            else:
                raw_item = record

            # Skip duplicates
            product_key = self._get_product_key(raw_item)
            if product_key in seen_products:
                continue

            transformed = self._transform_record(raw_item)
            if transformed:
                seen_products.add(product_key)
                yield transformed

    def _get_product_key(self, record: dict[str, Any]) -> str:
        """Get unique product key for deduplication."""
        product_id = str(record.get("product_id") or record.get("sku_id", ""))
        sku = record.get("sku") or record.get("seller_sku") or ""
        return f"lazada_{product_id}_{sku}"

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map Lazada fields to unified schema."""
        product_id = record.get("product_id") or record.get("sku_id")
        if not product_id:
            raise MappingError(
                message="Missing product_id or sku_id",
                source_platform=self.source_platform,
                record=record,
            )

        return {
            "product_id": f"lazada_{product_id}",
            "platform": self.source_platform,
            "platform_product_id": str(product_id),
            "sku": record.get("sku") or record.get("seller_sku"),
            "seller_sku": record.get("seller_sku"),
            "master_sku": None,
            "name": record.get("name", ""),
            "variation": record.get("variation"),
            "category": record.get("category"),
            "brand": record.get("brand"),
            "unit_price": float(
                record.get("item_price") or record.get("paid_price", 0)
            ),
            "original_price": float(record.get("original_price", 0))
            if record.get("original_price")
            else None,
            "discount_price": float(record.get("item_price", 0))
            if record.get("item_price")
            else None,
            "currency": record.get("currency", "THB"),
            "weight": record.get("weight"),
            "weight_unit": "kg",
            "is_active": True,
            "is_mapped": False,
            "last_seen_at": datetime.now(timezone.utc),
            "extracted_at": record.get("extracted_at"),
        }


class TikTokProductTransformer(BaseTransformer):
    """Transform TikTok Shop product data from order items."""

    source_platform = "tiktok_shop"
    target_schema = UnifiedProduct

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform TikTok Shop product records.

        Args:
            records: Raw TikTok Shop order item records or product records.

        Yields:
            Transformed product records.
        """
        seen_products: set[str] = set()

        for record in records:
            # Handle order item format
            if record.get("type") == "order_item":
                raw_item = record.get("data", {})
            elif record.get("type") == "product":
                raw_item = record.get("data", {})
            else:
                raw_item = record

            # Skip duplicates
            product_key = self._get_product_key(raw_item)
            if product_key in seen_products:
                continue

            transformed = self._transform_record(raw_item)
            if transformed:
                seen_products.add(product_key)
                yield transformed

    def _get_product_key(self, record: dict[str, Any]) -> str:
        """Get unique product key for deduplication."""
        product_id = str(record.get("product_id", ""))
        sku = record.get("seller_sku") or record.get("sku_id") or ""
        return f"tiktok_{product_id}_{sku}"

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map TikTok Shop fields to unified schema."""
        product_id = record.get("product_id")
        if not product_id:
            raise MappingError(
                message="Missing product_id",
                source_platform=self.source_platform,
                record=record,
            )

        return {
            "product_id": f"tiktok_{product_id}",
            "platform": self.source_platform,
            "platform_product_id": str(product_id),
            "sku": record.get("seller_sku") or record.get("sku_id"),
            "seller_sku": record.get("seller_sku"),
            "master_sku": None,
            "name": record.get("product_name", ""),
            "variation": record.get("sku_name"),
            "category": record.get("category_name"),
            "brand": record.get("brand_name"),
            "unit_price": float(
                record.get("sale_price") or record.get("sku_sale_price", 0)
            ),
            "original_price": float(record.get("original_price", 0))
            if record.get("original_price")
            else None,
            "discount_price": float(record.get("sale_price", 0))
            if record.get("sale_price")
            else None,
            "currency": record.get("currency", "THB"),
            "weight": record.get("weight"),
            "weight_unit": "kg",
            "is_active": True,
            "is_mapped": False,
            "last_seen_at": datetime.now(timezone.utc),
            "extracted_at": record.get("extracted_at"),
        }


class UnifiedProductTransformer(BaseTransformer):
    """Unified transformer that routes to platform-specific product transformers."""

    source_platform = "unified"
    target_schema = UnifiedProduct

    def __init__(self):
        super().__init__()
        self._transformers = {
            "shopee": ShopeeProductTransformer(),
            "lazada": LazadaProductTransformer(),
            "tiktok_shop": TikTokProductTransformer(),
        }

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform products from any supported platform.

        Args:
            records: Raw product/order item records with platform identifier.

        Yields:
            Transformed product records.
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

            # Prepare record for platform transformer
            if "data" in record:
                transform_record = {"type": "order_item", "data": record["data"]}
            else:
                transform_record = record

            # Transform using platform-specific transformer
            try:
                for transformed in transformer.transform([transform_record]):
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
            record: Raw product record.

        Returns:
            Platform name or 'unknown'.
        """
        data = record.get("data", record)

        # Shopee-specific fields
        if "item_id" in data or "model_sku" in data:
            return "shopee"

        # TikTok-specific fields (check before Lazada as TikTok has unique fields)
        # TikTok uses product_name, sku_name, sale_price, brand_name
        if "sku_name" in data or "sku_sale_price" in data or "product_name" in data:
            return "tiktok_shop"

        # Lazada-specific fields
        # Lazada uses name (not product_name), seller_sku
        if "sku_id" in data or ("name" in data and "seller_sku" in data):
            return "lazada"

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
