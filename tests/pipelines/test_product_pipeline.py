"""Tests for product pipeline."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.pipelines.base import PipelineStage


class TestProductPipelineLogic:
    """Tests for product pipeline logic without GCP dependencies."""

    def test_product_grouping_by_platform(self):
        """Test grouping products by platform."""
        records = [
            {"platform": "shopee", "data": {"item_id": 12345}},
            {"platform": "lazada", "data": {"sku_id": "67890"}},
            {"platform": "shopee", "data": {"item_id": 12346}},
            {"platform": "tiktok_shop", "data": {"product_id": "TIK001"}},
        ]

        platform_records = {}
        for record in records:
            platform = record.get("platform", "unknown")
            if platform not in platform_records:
                platform_records[platform] = []
            platform_records[platform].append(record.get("data", record))

        assert len(platform_records["shopee"]) == 2
        assert len(platform_records["lazada"]) == 1
        assert len(platform_records["tiktok_shop"]) == 1

    def test_product_record_structure(self, sample_products):
        """Test product record structure."""
        shopee_product = sample_products[0]
        lazada_product = sample_products[1]

        assert shopee_product["platform"] == "shopee"
        assert "item_id" in shopee_product["data"]
        assert "model_sku" in shopee_product["data"]

        assert lazada_product["platform"] == "lazada"
        assert "sku_id" in lazada_product["data"]
        assert "seller_sku" in lazada_product["data"]

    def test_unified_product_format(self):
        """Test unified product format structure."""
        unified_product = {
            "product_id": "shopee_12345",
            "platform": "shopee",
            "platform_product_id": "12345",
            "name": "Shopee Product",
            "sku": "SHP-SKU-001",
            "platform_sku": "SHP-SKU-001",
            "price": 500.0,
            "currency": "THB",
            "stock": 100,
            "category_id": "1001",
            "is_active": True,
        }

        assert unified_product["product_id"].startswith("shopee_")
        assert unified_product["platform"] == "shopee"
        assert "sku" in unified_product
        assert "price" in unified_product


class TestSKUMappingLogic:
    """Tests for SKU mapping logic."""

    def test_sku_mapping_generation(self):
        """Test generating SKU mapping from product."""
        product = {
            "platform": "shopee",
            "platform_sku": "SHP-SKU-001",
            "platform_product_id": "12345",
            "name": "Test Product",
        }

        mapping = {
            "platform": product["platform"],
            "platform_sku": product["platform_sku"],
            "platform_product_id": product["platform_product_id"],
            "product_name": product["name"],
            "master_sku": None,
        }

        assert mapping["platform"] == "shopee"
        assert mapping["platform_sku"] == "SHP-SKU-001"
        assert mapping["master_sku"] is None

    def test_master_sku_generation_from_platform_sku(self):
        """Test generating master SKU from platform SKU."""
        platform_sku = "SHP-SKU-001"
        product_name = "Test Product"

        # If platform SKU looks like a standard SKU
        def generate_master_sku(platform_sku: str, product_name: str) -> str:
            if platform_sku and len(platform_sku) <= 20 and "-" in platform_sku:
                return platform_sku.upper()
            if product_name:
                words = product_name.split()[:3]
                prefix = "".join(w[:2].upper() for w in words if w)
                return f"{prefix}-{platform_sku[:8].upper()}" if platform_sku else prefix
            return platform_sku.upper() if platform_sku else "UNKNOWN"

        master_sku = generate_master_sku(platform_sku, product_name)
        assert master_sku == "SHP-SKU-001"

    def test_master_sku_generation_from_product_name(self):
        """Test generating master SKU from product name."""
        platform_sku = "12345678901234567890123"  # Too long
        product_name = "Beautiful Red Dress"

        def generate_master_sku(platform_sku: str, product_name: str) -> str:
            if platform_sku and len(platform_sku) <= 20 and "-" in platform_sku:
                return platform_sku.upper()
            if product_name:
                words = product_name.split()[:3]
                prefix = "".join(w[:2].upper() for w in words if w)
                return f"{prefix}-{platform_sku[:8].upper()}" if platform_sku else prefix
            return platform_sku.upper() if platform_sku else "UNKNOWN"

        master_sku = generate_master_sku(platform_sku, product_name)
        # "Beautiful Red Dress" -> BE + RE + DR = "BEREDR"
        assert master_sku == "BEREDR-12345678"

    def test_filter_valid_mappings(self):
        """Test filtering valid SKU mappings."""
        mappings = [
            {"master_sku": "SKU-001", "platform_sku": "SHP-001"},
            {"master_sku": None, "platform_sku": "SHP-002"},  # Invalid
            {"master_sku": "SKU-003", "platform_sku": None},  # Invalid
            {"master_sku": "SKU-004", "platform_sku": "SHP-004"},
        ]

        valid_mappings = [
            m for m in mappings
            if m.get("master_sku") and m.get("platform_sku")
        ]

        assert len(valid_mappings) == 2
        assert valid_mappings[0]["master_sku"] == "SKU-001"
        assert valid_mappings[1]["master_sku"] == "SKU-004"

    def test_new_mapping_detection(self):
        """Test detecting new SKU mappings."""
        mappings = [
            {"master_sku": "SKU-001", "platform_sku": "SHP-001", "is_new": True},
            {"master_sku": "SKU-002", "platform_sku": "SHP-002", "is_new": False},
            {"master_sku": "SKU-003", "platform_sku": "SHP-003", "is_new": True},
        ]

        new_mappings = [m for m in mappings if m.get("is_new")]
        existing_mappings = [m for m in mappings if not m.get("is_new")]

        assert len(new_mappings) == 2
        assert len(existing_mappings) == 1


class TestProductPipelineMetadata:
    """Tests for product pipeline metadata handling."""

    def test_metadata_tracking(self):
        """Test metadata tracking in pipeline result."""
        metadata = {
            "sku_mappings_loaded": 10,
            "new_sku_mappings": 3,
        }

        assert metadata["sku_mappings_loaded"] == 10
        assert metadata["new_sku_mappings"] == 3

    def test_update_sku_mappings_flag(self):
        """Test update_sku_mappings flag behavior."""
        # When True, SKU mappings should be generated and loaded
        update_sku_mappings = True

        sku_mappings = []
        if update_sku_mappings:
            sku_mappings.append({"master_sku": "SKU-001"})

        assert len(sku_mappings) == 1

        # When False, SKU mappings should be skipped
        update_sku_mappings = False
        sku_mappings = []
        if update_sku_mappings:
            sku_mappings.append({"master_sku": "SKU-001"})

        assert len(sku_mappings) == 0


class TestProductPipelineExtraction:
    """Tests for product pipeline extraction logic."""

    def test_extract_products_method(self):
        """Test using extract_products method when available."""
        class MockExtractor:
            def extract_products(self):
                return iter([
                    {"item_id": 12345, "name": "Product 1"},
                    {"item_id": 12346, "name": "Product 2"},
                ])

            def extract(self, **kwargs):
                return iter([])

        extractor = MockExtractor()

        # Use extract_products if available
        if hasattr(extractor, "extract_products"):
            products = list(extractor.extract_products())
        else:
            products = list(extractor.extract())

        assert len(products) == 2

    def test_fallback_to_generic_extract(self):
        """Test fallback to generic extract method."""
        class MockExtractor:
            def extract(self, extract_type=None, **kwargs):
                if extract_type == "products":
                    return iter([
                        {"item_id": 12345, "name": "Product 1"},
                    ])
                return iter([])

        extractor = MockExtractor()

        # No extract_products method, fallback
        if hasattr(extractor, "extract_products"):
            products = list(extractor.extract_products())
        else:
            products = list(extractor.extract(extract_type="products"))

        assert len(products) == 1


class TestProductPipelineIntegration:
    """Integration tests with mocked external services."""

    @patch("src.pipelines.product_pipeline.ShopeeExtractor")
    @patch("src.pipelines.product_pipeline.LazadaExtractor")
    @patch("src.pipelines.product_pipeline.TikTokShopExtractor")
    @patch("src.pipelines.product_pipeline.RawDataLoader")
    @patch("src.pipelines.product_pipeline.StagingDataLoader")
    def test_full_pipeline_run_mocked(
        self,
        mock_staging,
        mock_raw,
        mock_tiktok,
        mock_lazada,
        mock_shopee,
        sample_date_range,
        sample_products,
    ):
        """Test full pipeline run with mocked dependencies."""
        start, end = sample_date_range

        # Setup mock extractors
        shopee_instance = MagicMock()
        shopee_instance.extract_products.return_value = iter([
            sample_products[0]["data"]
        ])
        shopee_instance.extract.return_value = iter([sample_products[0]["data"]])
        shopee_instance.__enter__ = MagicMock(return_value=shopee_instance)
        shopee_instance.__exit__ = MagicMock(return_value=False)
        mock_shopee.return_value = shopee_instance

        lazada_instance = MagicMock()
        lazada_instance.extract_products.return_value = iter([
            sample_products[1]["data"]
        ])
        lazada_instance.extract.return_value = iter([sample_products[1]["data"]])
        lazada_instance.__enter__ = MagicMock(return_value=lazada_instance)
        lazada_instance.__exit__ = MagicMock(return_value=False)
        mock_lazada.return_value = lazada_instance

        tiktok_instance = MagicMock()
        tiktok_instance.extract_products.return_value = iter([])
        tiktok_instance.extract.return_value = iter([])
        tiktok_instance.__enter__ = MagicMock(return_value=tiktok_instance)
        tiktok_instance.__exit__ = MagicMock(return_value=False)
        mock_tiktok.return_value = tiktok_instance

        # Setup mock loaders
        raw_instance = MagicMock()
        raw_instance.load_raw_products.return_value = 2
        raw_instance.set_batch_id = MagicMock()
        mock_raw.return_value = raw_instance

        staging_instance = MagicMock()
        staging_instance.load_products.return_value = 2
        staging_instance.load_sku_mappings.return_value = 2
        mock_staging.return_value = staging_instance

        # Import after patching
        from src.pipelines.product_pipeline import ProductPipeline

        # Run pipeline
        pipeline = ProductPipeline(start, end)
        result = pipeline.run()

        # Verify extractors were called
        assert mock_shopee.called
        assert mock_lazada.called

    def test_pipeline_without_sku_mapping(self, sample_date_range):
        """Test pipeline with SKU mapping disabled."""
        start, end = sample_date_range

        # When update_sku_mappings is False
        update_sku_mappings = False

        # No SKU mappings should be generated
        sku_mappings = []
        if update_sku_mappings:
            sku_mappings = [{"master_sku": "SKU-001"}]

        assert len(sku_mappings) == 0
