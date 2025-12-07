"""Tests for Product transformers and SKU mapper."""

import csv
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.transformers.products import (
    LazadaProductTransformer,
    ShopeeProductTransformer,
    TikTokProductTransformer,
    UnifiedProduct,
    UnifiedProductTransformer,
)
from src.transformers.sku_mapper import (
    SKUMapper,
    SKUMapping,
    SKUMappingNotFoundError,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def shopee_product_data():
    """Sample Shopee product/order item data."""
    return {
        "item_id": "123456789",
        "item_name": "Test Shopee Product",
        "item_sku": "SP-SKU-001",
        "model_sku": "SP-MODEL-001",
        "model_name": "Size M",
        "item_price": 299.00,
        "model_discounted_price": 249.00,
        "model_original_price": 299.00,
        "category_path": "Fashion > Clothing > T-Shirts",
        "brand": "TestBrand",
        "weight": 0.5,
        "currency": "THB",
    }


@pytest.fixture
def lazada_product_data():
    """Sample Lazada product/order item data."""
    return {
        "product_id": "987654321",
        "sku_id": "LZ-SKU-001",
        "name": "Test Lazada Product",
        "sku": "LZ-MODEL-001",
        "seller_sku": "LZ-SELLER-001",
        "variation": "Color: Red",
        "item_price": 399.00,
        "original_price": 499.00,
        "category": "Electronics",
        "brand": "LazadaBrand",
        "weight": 1.2,
        "currency": "THB",
    }


@pytest.fixture
def tiktok_product_data():
    """Sample TikTok Shop product/order item data."""
    return {
        "product_id": "456789123",
        "product_name": "Test TikTok Product",
        "seller_sku": "TT-SKU-001",
        "sku_id": "TT-MODEL-001",
        "sku_name": "Blue / Large",
        "sale_price": 199.00,
        "original_price": 249.00,
        "category_name": "Home & Living",
        "brand_name": "TikTokBrand",
        "weight": 0.8,
        "currency": "THB",
    }


@pytest.fixture
def sku_mapping_csv(tmp_path):
    """Create a temporary SKU mapping CSV file."""
    csv_path = tmp_path / "test_sku_mapping.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["master_sku", "platform", "platform_sku", "product_name", "variation", "notes"])
        writer.writerow(["MASTER-001", "shopee", "SP-SKU-001", "Test Product", "Size M", "Test note"])
        writer.writerow(["MASTER-001", "lazada", "LZ-SKU-001", "Test Product", "Size M", ""])
        writer.writerow(["MASTER-001", "tiktok_shop", "TT-SKU-001", "Test Product", "Size M", ""])
        writer.writerow(["MASTER-002", "shopee", "SP-SKU-002", "Another Product", "", ""])
    return csv_path


# ============================================================================
# Shopee Product Transformer Tests
# ============================================================================


class TestShopeeProductTransformer:
    """Tests for ShopeeProductTransformer."""

    def test_transform_single_product(self, shopee_product_data):
        """Test transforming a single Shopee product."""
        transformer = ShopeeProductTransformer()
        results = list(transformer.transform([shopee_product_data]))

        assert len(results) == 1
        product = results[0]

        assert product["product_id"] == "shopee_123456789"
        assert product["platform"] == "shopee"
        assert product["platform_product_id"] == "123456789"
        assert product["sku"] == "SP-MODEL-001"
        assert product["seller_sku"] == "SP-SKU-001"
        assert product["name"] == "Test Shopee Product"
        assert product["variation"] == "Size M"
        assert product["unit_price"] == 249.00
        assert product["original_price"] == 299.00
        assert product["brand"] == "TestBrand"
        assert product["weight"] == 0.5

    def test_transform_with_wrapper_format(self, shopee_product_data):
        """Test transforming with extractor wrapper format."""
        transformer = ShopeeProductTransformer()
        wrapped = {"type": "order_item", "data": shopee_product_data}
        results = list(transformer.transform([wrapped]))

        assert len(results) == 1
        assert results[0]["name"] == "Test Shopee Product"

    def test_deduplication(self, shopee_product_data):
        """Test that duplicate products are filtered out."""
        transformer = ShopeeProductTransformer()
        # Send same product twice
        results = list(transformer.transform([shopee_product_data, shopee_product_data]))

        assert len(results) == 1

    def test_missing_item_id(self):
        """Test handling of missing item_id."""
        transformer = ShopeeProductTransformer()
        invalid_data = {"item_name": "No ID Product"}
        results = list(transformer.transform([invalid_data]))

        assert len(results) == 0
        assert len(transformer.get_error_records()) == 1

    def test_fallback_sku(self):
        """Test SKU fallback from model_sku to item_sku."""
        transformer = ShopeeProductTransformer()
        data = {
            "item_id": "111",
            "item_name": "Fallback SKU Product",
            "item_sku": "FALLBACK-SKU",
            # No model_sku
        }
        results = list(transformer.transform([data]))

        assert len(results) == 1
        assert results[0]["sku"] == "FALLBACK-SKU"


# ============================================================================
# Lazada Product Transformer Tests
# ============================================================================


class TestLazadaProductTransformer:
    """Tests for LazadaProductTransformer."""

    def test_transform_single_product(self, lazada_product_data):
        """Test transforming a single Lazada product."""
        transformer = LazadaProductTransformer()
        results = list(transformer.transform([lazada_product_data]))

        assert len(results) == 1
        product = results[0]

        assert product["product_id"] == "lazada_987654321"
        assert product["platform"] == "lazada"
        assert product["platform_product_id"] == "987654321"
        assert product["sku"] == "LZ-MODEL-001"
        assert product["seller_sku"] == "LZ-SELLER-001"
        assert product["name"] == "Test Lazada Product"
        assert product["variation"] == "Color: Red"
        assert product["unit_price"] == 399.00
        assert product["original_price"] == 499.00
        assert product["brand"] == "LazadaBrand"

    def test_transform_with_sku_id_fallback(self):
        """Test using sku_id when product_id is missing."""
        transformer = LazadaProductTransformer()
        data = {
            "sku_id": "SKU-ONLY-001",
            "name": "SKU Only Product",
        }
        results = list(transformer.transform([data]))

        assert len(results) == 1
        assert results[0]["platform_product_id"] == "SKU-ONLY-001"

    def test_missing_product_id(self):
        """Test handling of missing product_id and sku_id."""
        transformer = LazadaProductTransformer()
        invalid_data = {"name": "No ID Product"}
        results = list(transformer.transform([invalid_data]))

        assert len(results) == 0
        assert len(transformer.get_error_records()) == 1


# ============================================================================
# TikTok Product Transformer Tests
# ============================================================================


class TestTikTokProductTransformer:
    """Tests for TikTokProductTransformer."""

    def test_transform_single_product(self, tiktok_product_data):
        """Test transforming a single TikTok Shop product."""
        transformer = TikTokProductTransformer()
        results = list(transformer.transform([tiktok_product_data]))

        assert len(results) == 1
        product = results[0]

        assert product["product_id"] == "tiktok_456789123"
        assert product["platform"] == "tiktok_shop"
        assert product["platform_product_id"] == "456789123"
        assert product["sku"] == "TT-SKU-001"
        assert product["name"] == "Test TikTok Product"
        assert product["variation"] == "Blue / Large"
        assert product["unit_price"] == 199.00
        assert product["original_price"] == 249.00
        assert product["brand"] == "TikTokBrand"

    def test_missing_product_id(self):
        """Test handling of missing product_id."""
        transformer = TikTokProductTransformer()
        invalid_data = {"product_name": "No ID Product"}
        results = list(transformer.transform([invalid_data]))

        assert len(results) == 0
        assert len(transformer.get_error_records()) == 1


# ============================================================================
# Unified Product Transformer Tests
# ============================================================================


class TestUnifiedProductTransformer:
    """Tests for UnifiedProductTransformer."""

    def test_auto_detect_shopee(self, shopee_product_data):
        """Test auto-detection of Shopee products."""
        transformer = UnifiedProductTransformer()
        results = list(transformer.transform([shopee_product_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "shopee"

    def test_auto_detect_lazada(self, lazada_product_data):
        """Test auto-detection of Lazada products."""
        transformer = UnifiedProductTransformer()
        results = list(transformer.transform([lazada_product_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "lazada"

    def test_auto_detect_tiktok(self, tiktok_product_data):
        """Test auto-detection of TikTok products."""
        transformer = UnifiedProductTransformer()
        results = list(transformer.transform([tiktok_product_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "tiktok_shop"

    def test_explicit_platform(self, shopee_product_data):
        """Test with explicit platform field."""
        transformer = UnifiedProductTransformer()
        shopee_product_data["platform"] = "shopee"
        results = list(transformer.transform([shopee_product_data]))

        assert len(results) == 1
        assert results[0]["platform"] == "shopee"

    def test_unknown_platform_skipped(self):
        """Test that unknown platforms are skipped."""
        transformer = UnifiedProductTransformer()
        data = {"platform": "unknown_platform", "id": "123"}
        results = list(transformer.transform([data]))

        assert len(results) == 0

    def test_mixed_platforms(self, shopee_product_data, lazada_product_data, tiktok_product_data):
        """Test transforming products from multiple platforms."""
        transformer = UnifiedProductTransformer()
        all_products = [shopee_product_data, lazada_product_data, tiktok_product_data]
        results = list(transformer.transform(all_products))

        assert len(results) == 3
        platforms = {r["platform"] for r in results}
        assert platforms == {"shopee", "lazada", "tiktok_shop"}

    def test_get_all_error_records(self, shopee_product_data):
        """Test collecting error records from all sub-transformers."""
        transformer = UnifiedProductTransformer()

        # Transform valid and invalid data
        invalid_shopee = {"item_name": "Invalid"}  # Missing item_id
        invalid_lazada = {"name": "Invalid", "platform": "lazada"}  # Missing product_id
        results = list(transformer.transform([shopee_product_data, invalid_shopee, invalid_lazada]))

        # Should have 1 success and 2 in error records
        assert len(results) == 1
        errors = transformer.get_error_records()
        assert len(errors) >= 1  # At least lazada error

    def test_clear_error_records(self):
        """Test clearing error records from all transformers."""
        transformer = UnifiedProductTransformer()
        invalid_data = {"item_name": "Invalid"}
        list(transformer.transform([invalid_data]))

        transformer.clear_error_records()
        assert len(transformer.get_error_records()) == 0


# ============================================================================
# Unified Product Schema Tests
# ============================================================================


class TestUnifiedProductSchema:
    """Tests for UnifiedProduct schema."""

    def test_required_fields(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):
            UnifiedProduct()

    def test_minimal_valid_product(self):
        """Test creating product with minimal required fields."""
        product = UnifiedProduct(
            product_id="test-001",
            platform="shopee",
            platform_product_id="001",
            name="Test Product",
        )
        assert product.product_id == "test-001"
        assert product.is_active is True
        assert product.is_mapped is False
        assert product.currency == "THB"

    def test_default_values(self):
        """Test default values are applied correctly."""
        product = UnifiedProduct(
            product_id="test-001",
            platform="shopee",
            platform_product_id="001",
            name="Test Product",
        )
        assert product.unit_price == 0.0
        assert product.weight_unit == "kg"
        assert product.master_sku is None
        assert product.transformed_at is not None


# ============================================================================
# SKU Mapper Tests
# ============================================================================


class TestSKUMapper:
    """Tests for SKUMapper."""

    def test_add_mapping(self):
        """Test adding a single mapping."""
        mapper = SKUMapper()
        mapping = mapper.add_mapping(
            master_sku="MASTER-001",
            platform="shopee",
            platform_sku="SP-001",
            product_name="Test Product",
        )

        assert mapping.master_sku == "MASTER-001"
        assert mapping.platform == "shopee"
        assert mapping.platform_sku == "SP-001"

    def test_get_master_sku(self):
        """Test retrieving master SKU."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        assert mapper.get_master_sku("shopee", "SP-001") == "MASTER-001"
        assert mapper.get_master_sku("shopee", "UNKNOWN") is None

    def test_get_master_sku_raise_if_not_found(self):
        """Test raising exception when SKU not found."""
        mapper = SKUMapper()

        with pytest.raises(SKUMappingNotFoundError) as exc_info:
            mapper.get_master_sku("shopee", "UNKNOWN", raise_if_not_found=True)

        assert exc_info.value.platform == "shopee"
        assert exc_info.value.sku == "UNKNOWN"

    def test_get_platform_skus(self):
        """Test getting all platform SKUs for a master SKU."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")
        mapper.add_mapping("MASTER-001", "lazada", "LZ-001")
        mapper.add_mapping("MASTER-001", "tiktok_shop", "TT-001")

        platform_skus = mapper.get_platform_skus("MASTER-001")
        assert len(platform_skus) == 3
        assert ("shopee", "SP-001") in platform_skus
        assert ("lazada", "LZ-001") in platform_skus

    def test_remove_mapping(self):
        """Test removing a mapping."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        assert mapper.remove_mapping("shopee", "SP-001") is True
        assert mapper.get_master_sku("shopee", "SP-001") is None
        assert mapper.remove_mapping("shopee", "SP-001") is False

    def test_contains(self):
        """Test __contains__ for checking mapping existence."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        assert ("shopee", "SP-001") in mapper
        assert ("shopee", "UNKNOWN") not in mapper

    def test_len(self):
        """Test __len__ returns total mappings."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")
        mapper.add_mapping("MASTER-001", "lazada", "LZ-001")

        assert len(mapper) == 2

    def test_unsupported_platform(self):
        """Test that unsupported platforms raise error."""
        mapper = SKUMapper()

        with pytest.raises(ValueError, match="Unsupported platform"):
            mapper.add_mapping("MASTER-001", "amazon", "AM-001")

    def test_load_from_csv(self, sku_mapping_csv):
        """Test loading mappings from CSV file."""
        mapper = SKUMapper(sku_mapping_csv)

        assert len(mapper) == 4
        assert mapper.get_master_sku("shopee", "SP-SKU-001") == "MASTER-001"
        assert mapper.get_master_sku("lazada", "LZ-SKU-001") == "MASTER-001"
        assert mapper.get_master_sku("tiktok_shop", "TT-SKU-001") == "MASTER-001"
        assert mapper.get_master_sku("shopee", "SP-SKU-002") == "MASTER-002"

    def test_load_from_csv_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            SKUMapper("/path/to/nonexistent.csv")

    def test_load_from_csv_missing_columns(self, tmp_path):
        """Test loading from CSV with missing columns."""
        csv_path = tmp_path / "invalid.csv"
        with open(csv_path, "w") as f:
            f.write("master_sku,platform\n")  # Missing platform_sku
            f.write("MASTER-001,shopee\n")

        with pytest.raises(ValueError, match="Missing required columns"):
            SKUMapper(csv_path)

    def test_save_to_csv(self, tmp_path):
        """Test saving mappings to CSV file."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001", "Test Product", "Size M")
        mapper.add_mapping("MASTER-001", "lazada", "LZ-001", "Test Product", "Size M")

        csv_path = tmp_path / "output.csv"
        count = mapper.save_to_csv(csv_path)

        assert count == 2
        assert csv_path.exists()

        # Reload and verify
        new_mapper = SKUMapper(csv_path)
        assert len(new_mapper) == 2

    def test_map_product(self):
        """Test mapping a single product."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        product = {"platform": "shopee", "sku": "SP-001", "name": "Test"}
        mapped = mapper.map_product(product)

        assert mapped["master_sku"] == "MASTER-001"
        assert mapped["is_mapped"] is True
        assert mapped["name"] == "Test"

    def test_map_product_not_found(self):
        """Test mapping a product with no mapping."""
        mapper = SKUMapper()

        product = {"platform": "shopee", "sku": "UNKNOWN", "name": "Test"}
        mapped = mapper.map_product(product)

        assert mapped["master_sku"] is None
        assert mapped["is_mapped"] is False

    def test_map_products(self):
        """Test mapping multiple products."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        products = [
            {"platform": "shopee", "sku": "SP-001", "name": "Product 1"},
            {"platform": "shopee", "sku": "SP-002", "name": "Product 2"},
        ]
        mapped = mapper.map_products(products)

        assert len(mapped) == 2
        assert mapped[0]["is_mapped"] is True
        assert mapped[1]["is_mapped"] is False

    def test_get_unmapped_skus(self):
        """Test finding unmapped SKUs."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        products = [
            {"platform": "shopee", "sku": "SP-001", "name": "Mapped"},
            {"platform": "shopee", "sku": "SP-002", "name": "Unmapped 1"},
            {"platform": "lazada", "sku": "LZ-001", "name": "Unmapped 2"},
        ]
        unmapped = mapper.get_unmapped_skus(products)

        assert len(unmapped) == 2
        skus = {(u["platform"], u["sku"]) for u in unmapped}
        assert ("shopee", "SP-002") in skus
        assert ("lazada", "LZ-001") in skus

    def test_generate_unmapped_csv(self, tmp_path):
        """Test generating CSV for unmapped SKUs."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")

        products = [
            {"platform": "shopee", "sku": "SP-001", "name": "Mapped"},
            {"platform": "shopee", "sku": "SP-002", "name": "Unmapped", "variation": "Red"},
        ]

        csv_path = tmp_path / "unmapped.csv"
        count = mapper.generate_unmapped_csv(products, csv_path)

        assert count == 1
        assert csv_path.exists()

        # Verify content
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            assert rows[0]["platform_sku"] == "SP-002"
            assert rows[0]["master_sku"] == ""  # Empty for manual filling

    def test_get_stats(self):
        """Test getting mapping statistics."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")
        mapper.add_mapping("MASTER-001", "lazada", "LZ-001")
        mapper.add_mapping("MASTER-002", "shopee", "SP-002")

        stats = mapper.get_stats()

        assert stats["total_mappings"] == 3
        assert stats["unique_master_skus"] == 2
        assert stats["by_platform"]["shopee"] == 2
        assert stats["by_platform"]["lazada"] == 1

    def test_get_mapping_details(self):
        """Test getting detailed mapping information."""
        mapper = SKUMapper()
        mapper.add_mapping(
            master_sku="MASTER-001",
            platform="shopee",
            platform_sku="SP-001",
            product_name="Test Product",
            variation="Size M",
            notes="Main SKU",
        )

        details = mapper.get_mapping_details("shopee", "SP-001")

        assert details is not None
        assert details.master_sku == "MASTER-001"
        assert details.product_name == "Test Product"
        assert details.variation == "Size M"
        assert details.notes == "Main SKU"

    def test_case_insensitive_platform(self):
        """Test that platform names are case-insensitive."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "SHOPEE", "SP-001")

        assert mapper.get_master_sku("shopee", "SP-001") == "MASTER-001"
        assert mapper.get_master_sku("SHOPEE", "SP-001") == "MASTER-001"


# ============================================================================
# Integration Tests
# ============================================================================


class TestProductSKUMapperIntegration:
    """Integration tests for Product transformers with SKU Mapper."""

    def test_transform_and_map_shopee(self, shopee_product_data, tmp_path):
        """Test transforming Shopee products and mapping SKUs."""
        # Setup SKU mapper
        csv_path = tmp_path / "mapping.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["master_sku", "platform", "platform_sku", "product_name", "variation", "notes"])
            writer.writerow(["MASTER-001", "shopee", "SP-MODEL-001", "Test Product", "Size M", ""])

        mapper = SKUMapper(csv_path)
        transformer = ShopeeProductTransformer()

        # Transform products
        products = list(transformer.transform([shopee_product_data]))

        # Map SKUs
        mapped = mapper.map_products(products)

        assert len(mapped) == 1
        assert mapped[0]["master_sku"] == "MASTER-001"
        assert mapped[0]["is_mapped"] is True

    def test_transform_and_find_unmapped(self, shopee_product_data, lazada_product_data):
        """Test transforming products and finding unmapped SKUs."""
        mapper = SKUMapper()
        # Only add Shopee mapping
        mapper.add_mapping("MASTER-001", "shopee", "SP-MODEL-001")

        transformer = UnifiedProductTransformer()
        products = list(transformer.transform([shopee_product_data, lazada_product_data]))

        unmapped = mapper.get_unmapped_skus(products)

        # Lazada product should be unmapped
        assert len(unmapped) == 1
        assert unmapped[0]["platform"] == "lazada"


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_input(self):
        """Test handling empty input."""
        transformer = UnifiedProductTransformer()
        results = list(transformer.transform([]))
        assert len(results) == 0

    def test_none_values(self):
        """Test handling None values in product data."""
        transformer = ShopeeProductTransformer()
        data = {
            "item_id": "123",
            "item_name": "Test Product",
            "model_sku": None,
            "item_sku": None,
            "weight": None,
        }
        results = list(transformer.transform([data]))

        assert len(results) == 1
        assert results[0]["sku"] is None
        assert results[0]["weight"] is None

    def test_product_with_zero_price(self):
        """Test handling products with zero price."""
        transformer = ShopeeProductTransformer()
        data = {
            "item_id": "123",
            "item_name": "Free Product",
            "item_price": 0,
        }
        results = list(transformer.transform([data]))

        assert len(results) == 1
        assert results[0]["unit_price"] == 0.0

    def test_sku_mapper_empty_values(self):
        """Test SKU mapper with empty values."""
        mapper = SKUMapper()

        product = {"platform": "", "sku": ""}
        mapped = mapper.map_product(product)
        assert mapped["is_mapped"] is False

        product = {"platform": "shopee", "sku": ""}
        mapped = mapper.map_product(product)
        assert mapped["is_mapped"] is False

    def test_duplicate_mappings_same_master(self):
        """Test adding duplicate platform SKUs to same master."""
        mapper = SKUMapper()
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")
        mapper.add_mapping("MASTER-001", "shopee", "SP-001")  # Duplicate

        # Should not create duplicate in reverse mapping
        platform_skus = mapper.get_platform_skus("MASTER-001")
        assert len(platform_skus) == 1
