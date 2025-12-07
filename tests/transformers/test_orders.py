"""Tests for order transformers."""

from datetime import datetime, timezone

import pytest

from src.transformers.orders import (
    LazadaOrderTransformer,
    OrderItemTransformer,
    ShopeeOrderTransformer,
    TikTokOrderTransformer,
    UnifiedOrderTransformer,
)


# Sample test data for each platform
@pytest.fixture
def shopee_order_data():
    """Sample Shopee order data."""
    return {
        "order_sn": "SHP123456789",
        "order_status": "COMPLETED",
        "buyer_user_id": 12345678,
        "buyer_username": "test_buyer",
        "create_time": 1704067200,  # 2024-01-01 00:00:00 UTC
        "pay_time": 1704067500,
        "update_time": 1704153600,
        "total_amount": 1500.00,
        "actual_shipping_fee": 50.00,
        "seller_discount": 100.00,
        "currency": "THB",
        "shipping_carrier": "Kerry Express",
        "tracking_no": "TRACK123",
        "recipient_address": {
            "name": "John Doe",
            "phone": "0812345678",
            "full_address": "123 Main St",
            "district": "Watthana",
            "city": "Bangkok",
            "state": "Bangkok",
            "zipcode": "10110",
        },
        "item_list": [
            {
                "item_id": 111,
                "item_name": "Product A",
                "model_sku": "SKU-A-001",
                "model_quantity_purchased": 2,
                "model_discounted_price": 500.00,
                "model_name": "Size M",
                "weight": 0.5,
            },
            {
                "item_id": 222,
                "item_name": "Product B",
                "model_sku": "SKU-B-001",
                "model_quantity_purchased": 1,
                "model_discounted_price": 500.00,
                "model_name": "Color Red",
                "weight": 0.3,
            },
        ],
    }


@pytest.fixture
def lazada_order_data():
    """Sample Lazada order data."""
    return {
        "order_id": "LZD987654321",
        "statuses": ["delivered"],
        "customer_id": 87654321,
        "customer_first_name": "Jane",
        "customer_last_name": "Smith",
        "created_at": "2024-01-01T00:00:00Z",
        "payment_method_paid_date": "2024-01-01T00:05:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "price": 2000.00,
        "shipping_fee": 60.00,
        "voucher_seller": 50.00,
        "voucher_platform": 30.00,
        "currency": "THB",
        "shipping_provider": "J&T Express",
        "tracking_code": "JT123456",
        "address_shipping": {
            "phone": "0898765432",
            "address1": "456 Second St",
            "city": "Nonthaburi",
            "region": "Nonthaburi",
            "post_code": "11000",
        },
        "order_items": [
            {
                "order_item_id": "ITEM001",
                "product_id": 333,
                "sku": "LZD-SKU-001",
                "name": "Product X",
                "quantity": 1,
                "item_price": 1200.00,
                "voucher_seller": 20.00,
                "voucher_platform": 10.00,
                "variation": "Large",
                "weight": 1.0,
            },
            {
                "order_item_id": "ITEM002",
                "product_id": 444,
                "sku": "LZD-SKU-002",
                "name": "Product Y",
                "quantity": 2,
                "item_price": 400.00,
                "voucher_seller": 0.00,
                "voucher_platform": 20.00,
                "variation": "Small",
                "weight": 0.5,
            },
        ],
    }


@pytest.fixture
def tiktok_order_data():
    """Sample TikTok Shop order data."""
    return {
        "order_id": "TKT456789123",
        "order_status": "DELIVERED",
        "buyer_uid": "tiktok_user_123",
        "create_time": 1704067200,
        "paid_time": 1704067800,
        "complete_time": 1704240000,
        "payment_info": {
            "sub_total": 1800.00,
            "shipping_fee": 40.00,
            "seller_discount": 80.00,
            "platform_discount": 20.00,
            "total_amount": 1740.00,
            "currency": "THB",
        },
        "shipping_provider": "Flash Express",
        "tracking_number": "FLASH789",
        "recipient_address": {
            "full_name": "Bob Johnson",
            "phone_number": "0876543210",
            "address_detail": "789 Third Ave",
            "district": "Phra Khanong",
            "city": "Bangkok",
            "state": "Bangkok",
            "postal_code": "10260",
        },
        "item_list": [
            {
                "id": "LINE001",
                "product_id": 555,
                "seller_sku": "TK-SKU-001",
                "product_name": "Product P",
                "quantity": 3,
                "sale_price": 600.00,
                "platform_discount": 10.00,
                "seller_discount": 50.00,
                "sku_name": "Bundle Pack",
                "weight": 2.0,
            },
        ],
    }


class TestShopeeOrderTransformer:
    """Tests for ShopeeOrderTransformer."""

    def test_transform_basic_order(self, shopee_order_data):
        """Test basic Shopee order transformation."""
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        assert len(results) == 1
        order = results[0]

        assert order["order_id"] == "shopee_SHP123456789"
        assert order["platform"] == "shopee"
        assert order["platform_order_id"] == "SHP123456789"
        assert order["status"] == "completed"
        assert order["status_raw"] == "COMPLETED"
        # customer_name falls back to buyer_username if recipient_address.name not available first
        assert order["customer_name"] in ["John Doe", "test_buyer"]
        assert order["customer_phone"] == "0812345678"

    def test_transform_with_extractor_wrapper(self, shopee_order_data):
        """Test transformation with extractor wrapper format."""
        wrapped = {"type": "order", "platform": "shopee", "data": shopee_order_data}
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["order_id"] == "shopee_SHP123456789"

    def test_extract_items(self, shopee_order_data):
        """Test order items extraction."""
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        assert order["item_count"] == 2
        assert len(order["items"]) == 2

        item1 = order["items"][0]
        assert item1["item_id"] == "111"
        assert item1["name"] == "Product A"
        assert item1["sku"] == "SKU-A-001"
        assert item1["quantity"] == 2
        assert item1["unit_price"] == 500.00
        assert item1["total_price"] == 1000.00
        assert item1["variation"] == "Size M"

    def test_status_mapping(self, shopee_order_data):
        """Test Shopee status mapping."""
        transformer = ShopeeOrderTransformer()

        # Test various statuses
        statuses = [
            ("UNPAID", "pending"),
            ("READY_TO_SHIP", "confirmed"),
            ("SHIPPED", "shipped"),
            ("COMPLETED", "completed"),
            ("CANCELLED", "cancelled"),
            ("UNKNOWN_STATUS", "unknown"),
        ]

        for raw_status, expected_status in statuses:
            shopee_order_data["order_status"] = raw_status
            results = list(transformer.transform([shopee_order_data]))
            assert results[0]["status"] == expected_status

    def test_currency_normalization(self, shopee_order_data):
        """Test currency normalization."""
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        assert isinstance(order["total"], float)
        assert order["total"] == 1500.00

    def test_datetime_normalization(self, shopee_order_data):
        """Test datetime normalization to Bangkok timezone."""
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        assert isinstance(order["order_date"], datetime)
        assert str(order["order_date"].tzinfo) == "Asia/Bangkok"

    def test_missing_order_sn_error(self):
        """Test error handling for missing order_sn."""
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([{"order_status": "COMPLETED"}]))

        assert len(results) == 0
        errors = transformer.get_error_records()
        assert len(errors) == 1
        assert "Missing order_sn" in errors[0]["error"]

    def test_address_formatting(self, shopee_order_data):
        """Test address formatting."""
        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        assert "123 Main St" in order["shipping_address"]
        assert "Bangkok" in order["shipping_address"]
        assert "10110" in order["shipping_address"]


class TestLazadaOrderTransformer:
    """Tests for LazadaOrderTransformer."""

    def test_transform_basic_order(self, lazada_order_data):
        """Test basic Lazada order transformation."""
        transformer = LazadaOrderTransformer()
        results = list(transformer.transform([lazada_order_data]))

        assert len(results) == 1
        order = results[0]

        assert order["order_id"] == "lazada_LZD987654321"
        assert order["platform"] == "lazada"
        assert order["platform_order_id"] == "LZD987654321"
        assert order["status"] == "completed"
        assert order["customer_name"] == "Jane Smith"

    def test_transform_with_extractor_wrapper(self, lazada_order_data):
        """Test transformation with extractor wrapper format."""
        wrapped = {"type": "order", "platform": "lazada", "data": lazada_order_data}
        transformer = LazadaOrderTransformer()
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["order_id"] == "lazada_LZD987654321"

    def test_extract_items(self, lazada_order_data):
        """Test order items extraction."""
        transformer = LazadaOrderTransformer()
        results = list(transformer.transform([lazada_order_data]))

        order = results[0]
        assert order["item_count"] == 2
        assert len(order["items"]) == 2

        item1 = order["items"][0]
        assert item1["item_id"] == "ITEM001"
        assert item1["name"] == "Product X"
        assert item1["sku"] == "LZD-SKU-001"
        assert item1["quantity"] == 1
        assert item1["unit_price"] == 1200.00
        assert item1["discount"] == 30.00

    def test_status_mapping(self, lazada_order_data):
        """Test Lazada status mapping."""
        transformer = LazadaOrderTransformer()

        statuses = [
            (["pending"], "pending"),
            (["packed"], "confirmed"),
            (["shipped"], "shipped"),
            (["delivered"], "completed"),
            (["cancelled"], "cancelled"),
            (["unknown"], "unknown"),
        ]

        for raw_status, expected_status in statuses:
            lazada_order_data["statuses"] = raw_status
            results = list(transformer.transform([lazada_order_data]))
            assert results[0]["status"] == expected_status

    def test_financial_calculations(self, lazada_order_data):
        """Test financial calculations."""
        transformer = LazadaOrderTransformer()
        results = list(transformer.transform([lazada_order_data]))

        order = results[0]
        assert order["shipping_fee"] == 60.00
        assert order["discount"] == 80.00  # 50 + 30
        assert order["total"] == 2000.00

    def test_iso_datetime_parsing(self, lazada_order_data):
        """Test ISO datetime parsing."""
        transformer = LazadaOrderTransformer()
        results = list(transformer.transform([lazada_order_data]))

        order = results[0]
        assert isinstance(order["order_date"], datetime)
        assert str(order["order_date"].tzinfo) == "Asia/Bangkok"


class TestTikTokOrderTransformer:
    """Tests for TikTokOrderTransformer."""

    def test_transform_basic_order(self, tiktok_order_data):
        """Test basic TikTok Shop order transformation."""
        transformer = TikTokOrderTransformer()
        results = list(transformer.transform([tiktok_order_data]))

        assert len(results) == 1
        order = results[0]

        assert order["order_id"] == "tiktok_TKT456789123"
        assert order["platform"] == "tiktok_shop"
        assert order["platform_order_id"] == "TKT456789123"
        assert order["status"] == "completed"
        assert order["customer_name"] == "Bob Johnson"
        assert order["customer_phone"] == "0876543210"

    def test_transform_with_extractor_wrapper(self, tiktok_order_data):
        """Test transformation with extractor wrapper format."""
        wrapped = {"type": "order", "platform": "tiktok_shop", "data": tiktok_order_data}
        transformer = TikTokOrderTransformer()
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["order_id"] == "tiktok_TKT456789123"

    def test_extract_items(self, tiktok_order_data):
        """Test order items extraction."""
        transformer = TikTokOrderTransformer()
        results = list(transformer.transform([tiktok_order_data]))

        order = results[0]
        assert order["item_count"] == 1
        assert len(order["items"]) == 1

        item = order["items"][0]
        assert item["item_id"] == "LINE001"
        assert item["name"] == "Product P"
        assert item["sku"] == "TK-SKU-001"
        assert item["quantity"] == 3
        assert item["unit_price"] == 600.00
        assert item["total_price"] == 1800.00
        assert item["discount"] == 60.00

    def test_status_mapping(self, tiktok_order_data):
        """Test TikTok status mapping."""
        transformer = TikTokOrderTransformer()

        statuses = [
            ("UNPAID", "pending"),
            ("AWAITING_SHIPMENT", "confirmed"),
            ("IN_TRANSIT", "shipped"),
            ("DELIVERED", "completed"),
            ("CANCELLED", "cancelled"),
            ("UNKNOWN", "unknown"),
        ]

        for raw_status, expected_status in statuses:
            tiktok_order_data["order_status"] = raw_status
            results = list(transformer.transform([tiktok_order_data]))
            assert results[0]["status"] == expected_status

    def test_payment_info_extraction(self, tiktok_order_data):
        """Test payment info extraction."""
        transformer = TikTokOrderTransformer()
        results = list(transformer.transform([tiktok_order_data]))

        order = results[0]
        assert order["subtotal"] == 1800.00
        assert order["shipping_fee"] == 40.00
        assert order["discount"] == 100.00  # 80 + 20
        assert order["total"] == 1740.00

    def test_unix_timestamp_parsing(self, tiktok_order_data):
        """Test Unix timestamp parsing."""
        transformer = TikTokOrderTransformer()
        results = list(transformer.transform([tiktok_order_data]))

        order = results[0]
        assert isinstance(order["order_date"], datetime)
        assert str(order["order_date"].tzinfo) == "Asia/Bangkok"


class TestUnifiedOrderTransformer:
    """Tests for UnifiedOrderTransformer."""

    def test_transform_shopee_order(self, shopee_order_data):
        """Test unified transformer with Shopee order."""
        transformer = UnifiedOrderTransformer()
        wrapped = {"type": "order", "platform": "shopee", "data": shopee_order_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["platform"] == "shopee"

    def test_transform_lazada_order(self, lazada_order_data):
        """Test unified transformer with Lazada order."""
        transformer = UnifiedOrderTransformer()
        wrapped = {"type": "order", "platform": "lazada", "data": lazada_order_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["platform"] == "lazada"

    def test_transform_tiktok_order(self, tiktok_order_data):
        """Test unified transformer with TikTok order."""
        transformer = UnifiedOrderTransformer()
        wrapped = {"type": "order", "platform": "tiktok_shop", "data": tiktok_order_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["platform"] == "tiktok_shop"

    def test_auto_detect_shopee(self, shopee_order_data):
        """Test auto-detection of Shopee platform."""
        transformer = UnifiedOrderTransformer()
        # No platform specified, should detect from order_sn
        results = list(transformer.transform([shopee_order_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "shopee"

    def test_auto_detect_lazada(self, lazada_order_data):
        """Test auto-detection of Lazada platform."""
        transformer = UnifiedOrderTransformer()
        results = list(transformer.transform([lazada_order_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "lazada"

    def test_auto_detect_tiktok(self, tiktok_order_data):
        """Test auto-detection of TikTok platform."""
        transformer = UnifiedOrderTransformer()
        results = list(transformer.transform([tiktok_order_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "tiktok_shop"

    def test_transform_mixed_orders(
        self, shopee_order_data, lazada_order_data, tiktok_order_data
    ):
        """Test transformation of mixed platform orders."""
        transformer = UnifiedOrderTransformer()
        orders = [
            {"platform": "shopee", "data": shopee_order_data},
            {"platform": "lazada", "data": lazada_order_data},
            {"platform": "tiktok_shop", "data": tiktok_order_data},
        ]
        results = list(transformer.transform(orders))

        assert len(results) == 3
        platforms = {r["platform"] for r in results}
        assert platforms == {"shopee", "lazada", "tiktok_shop"}

    def test_unknown_platform_skipped(self):
        """Test unknown platform is skipped."""
        transformer = UnifiedOrderTransformer()
        order = {"platform": "unknown_platform", "data": {"id": "123"}}
        results = list(transformer.transform([order]))

        assert len(results) == 0

    def test_aggregated_error_records(
        self, shopee_order_data, lazada_order_data
    ):
        """Test error records aggregation from all transformers."""
        transformer = UnifiedOrderTransformer()

        # Create invalid orders for both platforms
        invalid_shopee = {"platform": "shopee", "data": {}}  # Missing order_sn
        invalid_lazada = {"platform": "lazada", "data": {}}  # Missing order_id

        list(transformer.transform([invalid_shopee, invalid_lazada]))

        errors = transformer.get_error_records()
        assert len(errors) == 2

    def test_clear_error_records(self):
        """Test clearing error records from all transformers."""
        transformer = UnifiedOrderTransformer()

        invalid_order = {"platform": "shopee", "data": {}}
        list(transformer.transform([invalid_order]))

        assert len(transformer.get_error_records()) > 0

        transformer.clear_error_records()
        assert len(transformer.get_error_records()) == 0


class TestOrderItemTransformer:
    """Tests for OrderItemTransformer."""

    def test_extract_items_from_shopee(self, shopee_order_data):
        """Test item extraction from Shopee order."""
        transformer = OrderItemTransformer()
        wrapped = {"platform": "shopee", "data": shopee_order_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 2

        item1 = results[0]
        assert item1["order_id"] == "shopee_SHP123456789"
        assert item1["platform"] == "shopee"
        assert item1["item_id"] == "111"
        assert item1["name"] == "Product A"
        assert "transformed_at" in item1

    def test_extract_items_from_lazada(self, lazada_order_data):
        """Test item extraction from Lazada order."""
        transformer = OrderItemTransformer()
        wrapped = {"platform": "lazada", "data": lazada_order_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 2

        item1 = results[0]
        assert item1["order_id"] == "lazada_LZD987654321"
        assert item1["platform"] == "lazada"

    def test_extract_items_from_tiktok(self, tiktok_order_data):
        """Test item extraction from TikTok order."""
        transformer = OrderItemTransformer()
        wrapped = {"platform": "tiktok_shop", "data": tiktok_order_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1

        item = results[0]
        assert item["order_id"] == "tiktok_TKT456789123"
        assert item["platform"] == "tiktok_shop"

    def test_items_include_order_date(self, shopee_order_data):
        """Test items include order date reference."""
        transformer = OrderItemTransformer()
        wrapped = {"platform": "shopee", "data": shopee_order_data}
        results = list(transformer.transform([wrapped]))

        for item in results:
            assert "order_date" in item
            assert isinstance(item["order_date"], datetime)

    def test_extract_from_multiple_orders(
        self, shopee_order_data, lazada_order_data
    ):
        """Test item extraction from multiple orders."""
        transformer = OrderItemTransformer()
        orders = [
            {"platform": "shopee", "data": shopee_order_data},
            {"platform": "lazada", "data": lazada_order_data},
        ]
        results = list(transformer.transform(orders))

        assert len(results) == 4  # 2 from Shopee + 2 from Lazada


class TestTransformerErrorHandling:
    """Tests for error handling in transformers."""

    def test_dead_letter_queue(self):
        """Test dead letter queue functionality."""
        transformer = ShopeeOrderTransformer()

        # Transform invalid record
        invalid_record = {"invalid": "data"}
        list(transformer.transform([invalid_record]))

        errors = transformer.get_error_records()
        assert len(errors) == 1
        assert "error" in errors[0]
        assert "timestamp" in errors[0]
        assert errors[0]["source_platform"] == "shopee"

    def test_partial_success(self, shopee_order_data):
        """Test partial success with mixed valid/invalid records."""
        transformer = ShopeeOrderTransformer()

        records = [
            shopee_order_data,  # Valid
            {"invalid": "data"},  # Invalid
            {**shopee_order_data, "order_sn": "SHP999999999"},  # Valid
        ]

        results = list(transformer.transform(records))

        assert len(results) == 2  # Only valid records
        assert len(transformer.get_error_records()) == 1  # One error

    def test_clear_errors(self):
        """Test clearing error records."""
        transformer = ShopeeOrderTransformer()

        # Generate some errors
        list(transformer.transform([{"invalid": "data"}]))
        assert len(transformer.get_error_records()) > 0

        # Clear errors
        transformer.clear_error_records()
        assert len(transformer.get_error_records()) == 0

    def test_get_stats(self, shopee_order_data):
        """Test getting transformation stats."""
        transformer = ShopeeOrderTransformer()

        records = [shopee_order_data, {"invalid": "data"}]
        list(transformer.transform(records))

        stats = transformer.get_stats()
        assert "error_count" in stats
        assert stats["error_count"] == 1


class TestCurrencyNormalization:
    """Tests for currency normalization."""

    def test_usd_to_thb_conversion(self, shopee_order_data):
        """Test USD to THB conversion."""
        shopee_order_data["currency"] = "USD"
        shopee_order_data["total_amount"] = 100.00

        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        # Should be converted at rate of 35.0
        assert order["total"] == 3500.00

    def test_thb_no_conversion(self, shopee_order_data):
        """Test THB currency (no conversion needed)."""
        shopee_order_data["currency"] = "THB"
        shopee_order_data["total_amount"] = 1500.00

        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        assert order["total"] == 1500.00


class TestTimezoneConversion:
    """Tests for timezone conversion."""

    def test_utc_to_bangkok(self, shopee_order_data):
        """Test UTC to Bangkok timezone conversion."""
        # 2024-01-01 00:00:00 UTC = 2024-01-01 07:00:00 Bangkok
        shopee_order_data["create_time"] = 1704067200

        transformer = ShopeeOrderTransformer()
        results = list(transformer.transform([shopee_order_data]))

        order = results[0]
        assert str(order["order_date"].tzinfo) == "Asia/Bangkok"
        assert order["order_date"].hour == 7  # Bangkok is UTC+7

    def test_iso_string_parsing(self, lazada_order_data):
        """Test ISO string datetime parsing."""
        lazada_order_data["created_at"] = "2024-01-01T00:00:00Z"

        transformer = LazadaOrderTransformer()
        results = list(transformer.transform([lazada_order_data]))

        order = results[0]
        assert str(order["order_date"].tzinfo) == "Asia/Bangkok"
