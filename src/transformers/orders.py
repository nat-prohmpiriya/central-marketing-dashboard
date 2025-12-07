"""Order transformers for e-commerce platforms.

Transforms raw order data from Shopee, Lazada, and TikTok Shop
to a unified staging format.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Generator

from pydantic import BaseModel, Field

from src.transformers.base import BaseTransformer, MappingError


# Unified Order Schema
class OrderItem(BaseModel):
    """Unified order item schema."""

    item_id: str
    product_id: str
    sku: str | None = None
    name: str
    quantity: int
    unit_price: float
    total_price: float
    discount: float = 0.0
    platform: str
    variation: str | None = None
    weight: float | None = None


class UnifiedOrder(BaseModel):
    """Unified order schema for all e-commerce platforms."""

    # Identifiers
    order_id: str
    platform: str
    platform_order_id: str

    # Customer info
    customer_id: str | None = None
    customer_name: str | None = None
    customer_phone: str | None = None

    # Order details
    status: str
    status_raw: str
    order_date: datetime
    paid_date: datetime | None = None
    shipped_date: datetime | None = None
    completed_date: datetime | None = None

    # Financial
    subtotal: float
    shipping_fee: float = 0.0
    discount: float = 0.0
    total: float
    currency: str = "THB"

    # Shipping
    shipping_address: str | None = None
    shipping_method: str | None = None
    tracking_number: str | None = None

    # Items
    items: list[OrderItem] = Field(default_factory=list)
    item_count: int = 0

    # Metadata
    extracted_at: datetime | None = None
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Status mappings for each platform
SHOPEE_STATUS_MAPPING = {
    "unpaid": "pending",
    "ready_to_ship": "confirmed",
    "processed": "confirmed",
    "shipped": "shipped",
    "to_confirm_receive": "shipped",
    "completed": "completed",
    "cancelled": "cancelled",
    "to_return": "return_pending",
    "in_cancel": "cancel_pending",
}

LAZADA_STATUS_MAPPING = {
    "pending": "pending",
    "unpaid": "pending",
    "packed": "confirmed",
    "ready_to_ship": "confirmed",
    "ready_to_ship_pending": "confirmed",
    "shipped": "shipped",
    "delivered": "completed",
    "closed": "completed",
    "cancelled": "cancelled",
    "returned": "returned",
    "failed": "failed",
}

TIKTOK_STATUS_MAPPING = {
    "unpaid": "pending",
    "awaiting_shipment": "confirmed",
    "awaiting_collection": "confirmed",
    "in_transit": "shipped",
    "delivered": "completed",
    "completed": "completed",
    "cancelled": "cancelled",
    "on_hold": "on_hold",
}


class ShopeeOrderTransformer(BaseTransformer):
    """Transform Shopee orders to unified staging format."""

    source_platform = "shopee"
    target_schema = UnifiedOrder

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform Shopee order records.

        Args:
            records: Raw Shopee order records.

        Yields:
            Transformed order records.
        """
        for record in records:
            # Handle extractor wrapper format
            if record.get("type") == "order":
                raw_order = record.get("data", {})
            else:
                raw_order = record

            transformed = self._transform_record(raw_order)
            if transformed:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map Shopee fields to unified schema."""
        order_sn = record.get("order_sn") or record.get("ordersn")
        if not order_sn:
            raise MappingError(
                message="Missing order_sn",
                source_platform=self.source_platform,
                record=record,
            )

        # Extract order items
        items = self._extract_items(record)

        return {
            "order_id": f"shopee_{order_sn}",
            "platform": self.source_platform,
            "platform_order_id": order_sn,
            "customer_id": str(record.get("buyer_user_id", "")),
            "customer_name": record.get("buyer_username") or record.get("recipient_address", {}).get("name"),
            "customer_phone": record.get("recipient_address", {}).get("phone"),
            "status_raw": record.get("order_status", ""),
            "order_date": record.get("create_time"),
            "paid_date": record.get("pay_time"),
            "shipped_date": record.get("ship_by_date"),
            "completed_date": record.get("update_time") if record.get("order_status") == "COMPLETED" else None,
            "subtotal": record.get("total_amount") or record.get("actual_shipping_fee", 0),
            "shipping_fee": record.get("actual_shipping_fee") or record.get("estimated_shipping_fee", 0),
            "discount": record.get("seller_discount") or 0 + (record.get("voucher_seller") or 0),
            "total": record.get("total_amount", 0),
            "currency": record.get("currency", "THB"),
            "shipping_address": self._format_address(record.get("recipient_address", {})),
            "shipping_method": record.get("shipping_carrier"),
            "tracking_number": record.get("tracking_no"),
            "items": items,
            "item_count": len(items),
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_items(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract order items from Shopee order."""
        items = []
        raw_items = record.get("item_list") or record.get("items") or []

        for item in raw_items:
            items.append({
                "item_id": str(item.get("item_id", "")),
                "product_id": str(item.get("item_id", "")),
                "sku": item.get("model_sku") or item.get("item_sku"),
                "name": item.get("item_name", ""),
                "quantity": item.get("model_quantity_purchased") or item.get("quantity", 1),
                "unit_price": float(item.get("model_discounted_price") or item.get("item_price", 0)),
                "total_price": float(item.get("model_discounted_price", 0) or item.get("item_price", 0)) * (item.get("model_quantity_purchased") or item.get("quantity", 1)),
                "discount": 0.0,
                "platform": self.source_platform,
                "variation": item.get("model_name"),
                "weight": item.get("weight"),
            })

        return items

    def _format_address(self, address: dict[str, Any]) -> str | None:
        """Format Shopee address to string."""
        if not address:
            return None

        parts = [
            address.get("full_address"),
            address.get("district"),
            address.get("city"),
            address.get("state"),
            address.get("zipcode"),
        ]
        return ", ".join(filter(None, parts)) or None

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize Shopee order values."""
        # Normalize status
        record["status"] = self.normalize_status(
            record["status_raw"],
            SHOPEE_STATUS_MAPPING,
        )

        # Normalize dates (Shopee uses Unix timestamps)
        for date_field in ["order_date", "paid_date", "shipped_date", "completed_date"]:
            if record.get(date_field):
                record[date_field] = self.normalize_datetime(
                    record[date_field],
                    source_timezone="UTC",
                    target_timezone="Asia/Bangkok",
                )

        # Normalize currency
        for amount_field in ["subtotal", "shipping_fee", "discount", "total"]:
            if record.get(amount_field) is not None:
                record[amount_field] = self.normalize_currency(
                    record[amount_field],
                    source_currency=record.get("currency", "THB"),
                    target_currency="THB",
                )

        return record


class LazadaOrderTransformer(BaseTransformer):
    """Transform Lazada orders to unified staging format."""

    source_platform = "lazada"
    target_schema = UnifiedOrder

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform Lazada order records.

        Args:
            records: Raw Lazada order records.

        Yields:
            Transformed order records.
        """
        for record in records:
            # Handle extractor wrapper format
            if record.get("type") == "order":
                raw_order = record.get("data", {})
            else:
                raw_order = record

            transformed = self._transform_record(raw_order)
            if transformed:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map Lazada fields to unified schema."""
        order_id = record.get("order_id") or record.get("order_number")
        if not order_id:
            raise MappingError(
                message="Missing order_id",
                source_platform=self.source_platform,
                record=record,
            )

        # Extract order items
        items = self._extract_items(record)

        # Calculate totals from items if not provided
        subtotal = record.get("price", 0) or sum(item["total_price"] for item in items)
        shipping_fee = record.get("shipping_fee", 0)
        discount = record.get("voucher_seller", 0) + record.get("voucher_platform", 0)

        return {
            "order_id": f"lazada_{order_id}",
            "platform": self.source_platform,
            "platform_order_id": str(order_id),
            "customer_id": str(record.get("customer_id", "") or record.get("buyer_id", "")),
            "customer_name": record.get("customer_first_name", "") + " " + record.get("customer_last_name", ""),
            "customer_phone": record.get("address_shipping", {}).get("phone") if isinstance(record.get("address_shipping"), dict) else None,
            "status_raw": record.get("statuses", [""])[0] if isinstance(record.get("statuses"), list) else record.get("status", ""),
            "order_date": record.get("created_at"),
            "paid_date": record.get("payment_method_paid_date"),
            "shipped_date": record.get("shipped_at"),
            "completed_date": record.get("updated_at") if "delivered" in str(record.get("statuses", [])).lower() else None,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "discount": discount,
            "total": record.get("price", subtotal - discount + shipping_fee),
            "currency": record.get("currency", "THB"),
            "shipping_address": self._format_address(record.get("address_shipping", {})),
            "shipping_method": record.get("shipping_provider"),
            "tracking_number": record.get("tracking_code"),
            "items": items,
            "item_count": len(items),
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_items(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract order items from Lazada order."""
        items = []
        raw_items = record.get("order_items") or record.get("items") or []

        for item in raw_items:
            quantity = item.get("quantity", 1)
            unit_price = float(item.get("item_price", 0) or item.get("paid_price", 0))

            items.append({
                "item_id": str(item.get("order_item_id", "")),
                "product_id": str(item.get("product_id", "") or item.get("sku_id", "")),
                "sku": item.get("sku") or item.get("seller_sku"),
                "name": item.get("name", ""),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": unit_price * quantity,
                "discount": float(item.get("voucher_seller", 0) + item.get("voucher_platform", 0)),
                "platform": self.source_platform,
                "variation": item.get("variation"),
                "weight": item.get("weight"),
            })

        return items

    def _format_address(self, address: dict[str, Any] | str) -> str | None:
        """Format Lazada address to string."""
        if not address:
            return None

        if isinstance(address, str):
            return address

        parts = [
            address.get("address1"),
            address.get("address2"),
            address.get("address3"),
            address.get("city"),
            address.get("ward"),
            address.get("region"),
            address.get("post_code"),
        ]
        return ", ".join(filter(None, parts)) or None

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize Lazada order values."""
        # Normalize status
        record["status"] = self.normalize_status(
            record["status_raw"],
            LAZADA_STATUS_MAPPING,
        )

        # Normalize dates (Lazada uses ISO format)
        for date_field in ["order_date", "paid_date", "shipped_date", "completed_date"]:
            if record.get(date_field):
                record[date_field] = self.normalize_datetime(
                    record[date_field],
                    source_timezone="UTC",
                    target_timezone="Asia/Bangkok",
                )

        # Normalize currency
        for amount_field in ["subtotal", "shipping_fee", "discount", "total"]:
            if record.get(amount_field) is not None:
                record[amount_field] = self.normalize_currency(
                    record[amount_field],
                    source_currency=record.get("currency", "THB"),
                    target_currency="THB",
                )

        return record


class TikTokOrderTransformer(BaseTransformer):
    """Transform TikTok Shop orders to unified staging format."""

    source_platform = "tiktok_shop"
    target_schema = UnifiedOrder

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform TikTok Shop order records.

        Args:
            records: Raw TikTok Shop order records.

        Yields:
            Transformed order records.
        """
        for record in records:
            # Handle extractor wrapper format
            if record.get("type") == "order":
                raw_order = record.get("data", {})
            else:
                raw_order = record

            transformed = self._transform_record(raw_order)
            if transformed:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map TikTok Shop fields to unified schema."""
        order_id = record.get("order_id")
        if not order_id:
            raise MappingError(
                message="Missing order_id",
                source_platform=self.source_platform,
                record=record,
            )

        # Extract order items
        items = self._extract_items(record)

        # Get payment info
        payment_info = record.get("payment_info", {})

        # Calculate totals
        subtotal = float(payment_info.get("sub_total", 0) or payment_info.get("original_total_product_price", 0))
        shipping_fee = float(payment_info.get("shipping_fee", 0) or payment_info.get("original_shipping_fee", 0))
        discount = float(payment_info.get("seller_discount", 0) or 0) + float(payment_info.get("platform_discount", 0) or 0)
        total = float(payment_info.get("total_amount", 0) or record.get("payment_method_amount", 0))

        # Get recipient info
        recipient = record.get("recipient_address", {})

        return {
            "order_id": f"tiktok_{order_id}",
            "platform": self.source_platform,
            "platform_order_id": order_id,
            "customer_id": str(record.get("buyer_uid", "")),
            "customer_name": recipient.get("full_name") or recipient.get("name"),
            "customer_phone": recipient.get("phone_number") or recipient.get("phone"),
            "status_raw": record.get("order_status", ""),
            "order_date": record.get("create_time"),
            "paid_date": record.get("paid_time"),
            "shipped_date": record.get("shipping_due_time"),
            "completed_date": record.get("complete_time"),
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "discount": discount,
            "total": total if total else (subtotal + shipping_fee - discount),
            "currency": payment_info.get("currency", "THB"),
            "shipping_address": self._format_address(recipient),
            "shipping_method": record.get("shipping_provider"),
            "tracking_number": record.get("tracking_number"),
            "items": items,
            "item_count": len(items),
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_items(self, record: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract order items from TikTok Shop order."""
        items = []
        raw_items = record.get("item_list") or record.get("line_items") or []

        for item in raw_items:
            quantity = item.get("quantity", 1)
            unit_price = float(item.get("sale_price", 0) or item.get("sku_sale_price", 0))

            items.append({
                "item_id": str(item.get("id", "")),
                "product_id": str(item.get("product_id", "")),
                "sku": item.get("seller_sku") or item.get("sku_id"),
                "name": item.get("product_name", ""),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": unit_price * quantity,
                "discount": float(item.get("platform_discount", 0) or 0) + float(item.get("seller_discount", 0) or 0),
                "platform": self.source_platform,
                "variation": item.get("sku_name"),
                "weight": item.get("weight"),
            })

        return items

    def _format_address(self, address: dict[str, Any]) -> str | None:
        """Format TikTok Shop address to string."""
        if not address:
            return None

        parts = [
            address.get("address_detail") or address.get("full_address"),
            address.get("district"),
            address.get("city"),
            address.get("state"),
            address.get("region"),
            address.get("zipcode") or address.get("postal_code"),
        ]
        return ", ".join(filter(None, parts)) or None

    def _normalize_values(self, record: dict[str, Any]) -> dict[str, Any]:
        """Normalize TikTok Shop order values."""
        # Normalize status
        record["status"] = self.normalize_status(
            record["status_raw"],
            TIKTOK_STATUS_MAPPING,
        )

        # Normalize dates (TikTok uses Unix timestamps in seconds)
        for date_field in ["order_date", "paid_date", "shipped_date", "completed_date"]:
            if record.get(date_field):
                record[date_field] = self.normalize_datetime(
                    record[date_field],
                    source_timezone="UTC",
                    target_timezone="Asia/Bangkok",
                )

        # Normalize currency
        for amount_field in ["subtotal", "shipping_fee", "discount", "total"]:
            if record.get(amount_field) is not None:
                record[amount_field] = self.normalize_currency(
                    record[amount_field],
                    source_currency=record.get("currency", "THB"),
                    target_currency="THB",
                )

        return record


class UnifiedOrderTransformer(BaseTransformer):
    """Unified transformer that routes to platform-specific transformers."""

    source_platform = "unified"
    target_schema = UnifiedOrder

    def __init__(self):
        super().__init__()
        self._transformers = {
            "shopee": ShopeeOrderTransformer(),
            "lazada": LazadaOrderTransformer(),
            "tiktok_shop": TikTokOrderTransformer(),
        }

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform orders from any supported platform.

        Args:
            records: Raw order records with platform identifier.

        Yields:
            Transformed order records.
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
            # If record has "data" key, wrap it properly, otherwise use record directly
            if "data" in record:
                transform_record = {"type": "order", "data": record["data"]}
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
            record: Raw order record.

        Returns:
            Platform name or 'unknown'.
        """
        # Handle extractor wrapper format
        data = record.get("data", record)

        # Shopee-specific fields
        if "order_sn" in data or "ordersn" in data:
            return "shopee"

        # Lazada-specific fields
        if "statuses" in data or ("order_id" in data and "order_items" in data):
            return "lazada"

        # TikTok-specific fields
        if "buyer_uid" in data or "payment_info" in data:
            return "tiktok_shop"

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


class OrderItemTransformer(BaseTransformer):
    """Extract and transform order items independently."""

    source_platform = "order_items"
    target_schema = None  # Uses OrderItem model for validation

    def __init__(self):
        super().__init__()
        self._order_transformer = UnifiedOrderTransformer()

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Extract items from orders and yield individually.

        Args:
            records: Raw order records.

        Yields:
            Individual order item records with order reference.
        """
        for transformed_order in self._order_transformer.transform(records):
            order_id = transformed_order.get("order_id")
            platform = transformed_order.get("platform")
            order_date = transformed_order.get("order_date")

            for item in transformed_order.get("items", []):
                yield {
                    "order_id": order_id,
                    "platform": platform,
                    "order_date": order_date,
                    **item,
                    "transformed_at": datetime.now(timezone.utc).isoformat(),
                }

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Not used directly - delegates to UnifiedOrderTransformer."""
        return record
