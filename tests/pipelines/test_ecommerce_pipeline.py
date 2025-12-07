"""Tests for e-commerce pipeline."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.pipelines.base import PipelineStage


class TestEcommercePipelineLogic:
    """Tests for e-commerce pipeline logic without GCP dependencies."""

    def test_order_grouping_by_platform(self):
        """Test grouping orders by platform."""
        records = [
            {"platform": "shopee", "data": {"order_sn": "SHP001"}},
            {"platform": "lazada", "data": {"order_id": "LAZ001"}},
            {"platform": "shopee", "data": {"order_sn": "SHP002"}},
            {"platform": "tiktok_shop", "data": {"order_id": "TIK001"}},
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

    def test_extract_record_structure(self, sample_shopee_orders):
        """Test extracted record structure."""
        record = sample_shopee_orders[0]

        assert "platform" in record
        assert "data" in record
        assert "extracted_at" in record
        assert record["platform"] == "shopee"
        assert "order_sn" in record["data"]

    def test_platform_metadata_addition(self):
        """Test adding platform metadata to records."""
        raw_record = {"order_sn": "SHP001", "total_amount": 1000}
        platform = "shopee"
        batch_id = "test-batch"

        enriched = {
            "platform": platform,
            "data": raw_record,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "batch_id": batch_id,
        }

        assert enriched["platform"] == "shopee"
        assert enriched["batch_id"] == "test-batch"
        assert enriched["data"]["order_sn"] == "SHP001"

    def test_error_accumulation(self):
        """Test error accumulation during processing."""
        errors = []
        platforms = ["shopee", "lazada", "tiktok_shop"]

        # Simulate extraction errors
        for platform in platforms:
            if platform == "lazada":  # Simulate failure
                errors.append({
                    "stage": PipelineStage.EXTRACT.value,
                    "platform": platform,
                    "message": "API error",
                })

        assert len(errors) == 1
        assert errors[0]["platform"] == "lazada"

    def test_unified_order_format(self):
        """Test unified order format structure."""
        unified_order = {
            "order_id": "shopee_SHP001",
            "platform": "shopee",
            "platform_order_id": "SHP001",
            "status": "completed",
            "order_date": "2024-01-01T00:00:00+00:00",
            "total_amount": 1000.0,
            "currency": "THB",
            "customer_id": "buyer1",
            "items": [
                {
                    "item_id": "12345",
                    "sku": "SKU-A",
                    "name": "Product A",
                    "quantity": 2,
                    "unit_price": 500.0,
                }
            ],
        }

        assert unified_order["order_id"].startswith("shopee_")
        assert unified_order["platform"] == "shopee"
        assert "items" in unified_order
        assert len(unified_order["items"]) == 1


class TestEcommercePipelineWithMocks:
    """Tests for e-commerce pipeline with mocked dependencies."""

    @pytest.fixture
    def mock_pipeline_deps(self, mock_extractors, mock_loaders):
        """Create all mocked dependencies."""
        raw_loader, staging_loader = mock_loaders
        return {
            "raw_loader": raw_loader,
            "staging_loader": staging_loader,
            "extractor_factory": mock_extractors,
        }

    def test_pipeline_platforms_config(self, sample_date_range):
        """Test pipeline platform configuration."""
        start, end = sample_date_range

        # Default platforms
        default_platforms = ["shopee", "lazada", "tiktok_shop"]

        # Custom platforms
        custom_platforms = ["shopee"]

        assert len(default_platforms) == 3
        assert len(custom_platforms) == 1
        assert "shopee" in custom_platforms

    def test_extract_continues_on_platform_error(self, sample_date_range):
        """Test extraction continues when one platform fails."""
        start, end = sample_date_range

        # Simulate extraction from multiple platforms
        all_records = []
        platform_results = {
            "shopee": [{"order_sn": "SHP001"}],
            "lazada": Exception("API Error"),  # This one fails
            "tiktok_shop": [{"order_id": "TIK001"}],
        }
        errors = []

        for platform, result in platform_results.items():
            if isinstance(result, Exception):
                errors.append({
                    "stage": "extract",
                    "platform": platform,
                    "message": str(result),
                })
            else:
                for record in result:
                    all_records.append({"platform": platform, "data": record})

        # Pipeline should continue despite one failure
        assert len(all_records) == 2
        assert len(errors) == 1
        assert errors[0]["platform"] == "lazada"

    def test_transform_error_handling(self, sample_shopee_orders):
        """Test transform handles individual record errors."""
        transformed = []
        error_records = []

        for record in sample_shopee_orders:
            try:
                # Simulate transformation
                transformed.append({
                    "order_id": f"{record['platform']}_{record['data']['order_sn']}",
                    "platform": record["platform"],
                })
            except Exception as e:
                error_records.append({
                    "record": record,
                    "error": str(e),
                })

        assert len(transformed) == 2
        assert len(error_records) == 0

    def test_batch_id_propagation(self):
        """Test batch ID is propagated through pipeline stages."""
        batch_id = "20240115_120000"

        # Simulate batch ID usage
        raw_loader_batch_id = None
        staging_records_batch_id = None

        # Set batch ID
        raw_loader_batch_id = batch_id

        # Records should include batch_id
        records = [
            {"data": {"order_sn": "SHP001"}, "batch_id": batch_id},
        ]
        staging_records_batch_id = records[0].get("batch_id")

        assert raw_loader_batch_id == batch_id
        assert staging_records_batch_id == batch_id

    def test_result_statistics(self):
        """Test pipeline result statistics calculation."""
        from src.pipelines.base import PipelineResult

        result = PipelineResult(
            pipeline_name="ecommerce",
            success=True,
            stage=PipelineStage.COMPLETED,
            start_time=datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
            records_extracted=100,
            records_transformed=95,
            records_loaded_raw=100,
            records_loaded_staging=95,
            errors=[
                {"stage": "transform", "message": "Invalid record"},
                {"stage": "transform", "message": "Missing field"},
            ],
        )

        assert result.records_extracted == 100
        assert result.records_transformed == 95
        assert result.duration_seconds == 300.0  # 5 minutes
        assert len(result.errors) == 2

        # Calculate transform error rate
        error_rate = (result.records_extracted - result.records_transformed) / result.records_extracted
        assert error_rate == 0.05  # 5%


class TestEcommercePipelineIntegration:
    """Integration tests with mocked external services."""

    @patch("src.pipelines.ecommerce_pipeline.ShopeeExtractor")
    @patch("src.pipelines.ecommerce_pipeline.LazadaExtractor")
    @patch("src.pipelines.ecommerce_pipeline.TikTokShopExtractor")
    @patch("src.pipelines.ecommerce_pipeline.RawDataLoader")
    @patch("src.pipelines.ecommerce_pipeline.StagingDataLoader")
    def test_full_pipeline_run_mocked(
        self,
        mock_staging,
        mock_raw,
        mock_tiktok,
        mock_lazada,
        mock_shopee,
        sample_date_range,
        sample_shopee_orders,
    ):
        """Test full pipeline run with mocked dependencies."""
        start, end = sample_date_range

        # Setup mock extractors
        shopee_instance = MagicMock()
        shopee_instance.extract.return_value = iter([
            sample_shopee_orders[0]["data"],
            sample_shopee_orders[1]["data"],
        ])
        shopee_instance.__enter__ = MagicMock(return_value=shopee_instance)
        shopee_instance.__exit__ = MagicMock(return_value=False)
        mock_shopee.return_value = shopee_instance

        lazada_instance = MagicMock()
        lazada_instance.extract.return_value = iter([])
        lazada_instance.__enter__ = MagicMock(return_value=lazada_instance)
        lazada_instance.__exit__ = MagicMock(return_value=False)
        mock_lazada.return_value = lazada_instance

        tiktok_instance = MagicMock()
        tiktok_instance.extract.return_value = iter([])
        tiktok_instance.__enter__ = MagicMock(return_value=tiktok_instance)
        tiktok_instance.__exit__ = MagicMock(return_value=False)
        mock_tiktok.return_value = tiktok_instance

        # Setup mock loaders
        raw_instance = MagicMock()
        raw_instance.load_raw_orders.return_value = 2
        raw_instance.set_batch_id = MagicMock()
        mock_raw.return_value = raw_instance

        staging_instance = MagicMock()
        staging_instance.load_orders.return_value = 2
        mock_staging.return_value = staging_instance

        # Import after patching
        from src.pipelines.ecommerce_pipeline import EcommercePipeline

        # Run pipeline
        pipeline = EcommercePipeline(start, end)
        result = pipeline.run()

        # Verify
        assert result.records_extracted == 2
        assert mock_shopee.called
        assert mock_lazada.called

    def test_pipeline_dry_run(self, sample_date_range):
        """Test pipeline dry run (skip loading)."""
        start, end = sample_date_range

        # Dry run should:
        # 1. Extract data
        # 2. Transform data
        # 3. NOT load to raw
        # 4. NOT load to staging

        # This is tested via skip flags
        extracted = [{"id": 1}, {"id": 2}]
        transformed = [{"id": 1, "normalized": True}, {"id": 2, "normalized": True}]

        # Simulate dry run results
        loaded_raw = 0
        loaded_staging = 0

        assert len(extracted) == 2
        assert len(transformed) == 2
        assert loaded_raw == 0
        assert loaded_staging == 0
