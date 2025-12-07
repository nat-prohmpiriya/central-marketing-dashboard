"""Tests for Shopee extractor."""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.shopee import ShopeeExtractor


class TestShopeeSignature:
    """Tests for Shopee signature generation."""

    def test_generate_signature_public_api(self):
        """Test signature generation for public APIs."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            timestamp = 1700000000
            path = "/api/v2/shop/auth_partner"

            signature = extractor._generate_signature(path, timestamp)

            # Verify signature format (64 char hex)
            assert len(signature) == 64
            assert all(c in "0123456789abcdef" for c in signature)

            # Verify signature is deterministic
            signature2 = extractor._generate_signature(path, timestamp)
            assert signature == signature2

    def test_generate_signature_shop_api(self):
        """Test signature generation for shop-level APIs."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            timestamp = 1700000000
            path = "/api/v2/order/get_order_list"
            access_token = "test_access_token"
            shop_id = 67890

            signature = extractor._generate_signature(
                path, timestamp, access_token, shop_id
            )

            # Verify different signature with access_token and shop_id
            signature_public = extractor._generate_signature(path, timestamp)
            assert signature != signature_public

    def test_generate_signature_manual_verification(self):
        """Manually verify signature calculation."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="secret_key",
                shopee_shop_id="67890",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            timestamp = 1700000000
            path = "/api/v2/shop/auth_partner"

            # Manual calculation
            base_string = f"12345{path}{timestamp}"
            expected_signature = hmac.new(
                "secret_key".encode("utf-8"),
                base_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            signature = extractor._generate_signature(path, timestamp)
            assert signature == expected_signature


class TestShopeeAuthentication:
    """Tests for Shopee authentication."""

    def test_authenticate_missing_credentials(self):
        """Test authentication fails without credentials."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="",
                shopee_partner_key="",
                shopee_shop_id="",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "Missing Shopee credentials" in str(exc_info.value)

    def test_authenticate_missing_shop_id(self):
        """Test authentication fails without shop_id."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "Missing Shopee shop_id" in str(exc_info.value)

    def test_authenticate_no_tokens(self):
        """Test authentication fails without tokens."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "No valid access_token or refresh_token" in str(exc_info.value)

    @patch("src.extractors.shopee.ShopeeExtractor._get_shop_info")
    def test_authenticate_with_valid_token(self, mock_get_shop_info):
        """Test authentication succeeds with valid token."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="valid_token",
                shopee_refresh_token="refresh_token",
            )

            mock_get_shop_info.return_value = {"shop_name": "Test Shop"}

            extractor = ShopeeExtractor()
            result = extractor.authenticate()

            assert result is True
            assert extractor._authenticated is True


class TestShopeeAuthorizationURL:
    """Tests for OAuth authorization URL generation."""

    def test_get_authorization_url(self):
        """Test authorization URL generation."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            redirect_url = "https://myapp.com/callback"

            url = extractor.get_authorization_url(redirect_url)

            assert "partner.shopeemobile.com" in url
            assert "/api/v2/shop/auth_partner" in url
            assert "partner_id=12345" in url
            assert "sign=" in url
            assert f"redirect={redirect_url}" in url


class TestShopeeCommonParams:
    """Tests for common parameter building."""

    def test_build_common_params_with_shop(self):
        """Test building params with shop credentials."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            path = "/api/v2/order/get_order_list"

            params = extractor._build_common_params(path, include_shop=True)

            assert params["partner_id"] == 12345
            assert params["shop_id"] == 67890
            assert params["access_token"] == "test_token"
            assert "timestamp" in params
            assert "sign" in params

    def test_build_common_params_without_shop(self):
        """Test building params without shop credentials."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            path = "/api/v2/shop/auth_partner"

            params = extractor._build_common_params(path, include_shop=False)

            assert params["partner_id"] == 12345
            assert "shop_id" not in params
            assert "access_token" not in params
            assert "timestamp" in params
            assert "sign" in params


class TestShopeeOrderExtraction:
    """Tests for order extraction."""

    @patch("src.extractors.shopee.ShopeeExtractor.authenticate")
    @patch("src.extractors.shopee.ShopeeExtractor._ensure_authenticated")
    def test_extract_orders_date_conversion(
        self, mock_ensure_auth, mock_auth
    ):
        """Test that dates are properly converted to timestamps."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)

            # Mock the HTTP client
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "response": {"order_list": [], "more": False}
            }
            mock_client.get.return_value = mock_response
            extractor._client = mock_client

            # Run extraction
            list(extractor.extract_orders(start_date, end_date))

            # Verify the API was called
            mock_client.get.assert_called()

    @patch("src.extractors.shopee.ShopeeExtractor.authenticate")
    @patch("src.extractors.shopee.ShopeeExtractor._ensure_authenticated")
    def test_extract_orders_pagination(self, mock_ensure_auth, mock_auth):
        """Test that order extraction handles pagination."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            extractor._authenticated = True

            # Mock responses for pagination
            responses = [
                # First page
                {
                    "response": {
                        "order_list": [{"order_sn": "ORDER001"}],
                        "more": True,
                        "next_cursor": "cursor1",
                    }
                },
                # Order details for first page
                {
                    "response": {
                        "order_list": [
                            {"order_sn": "ORDER001", "total_amount": 100.0}
                        ]
                    }
                },
                # Second page (empty - end of pagination)
                {"response": {"order_list": [], "more": False}},
            ]

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.side_effect = responses
            mock_client.get.return_value = mock_response
            extractor._client = mock_client

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            orders = list(extractor.extract_orders(start_date, end_date))

            assert len(orders) == 1
            assert orders[0]["type"] == "order"
            assert orders[0]["platform"] == "shopee"


class TestShopeeProductExtraction:
    """Tests for product extraction."""

    @patch("src.extractors.shopee.ShopeeExtractor.authenticate")
    @patch("src.extractors.shopee.ShopeeExtractor._ensure_authenticated")
    def test_extract_products_empty(self, mock_ensure_auth, mock_auth):
        """Test product extraction with empty response."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            extractor._authenticated = True

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "response": {"item": [], "has_next_page": False}
            }
            mock_client.get.return_value = mock_response
            extractor._client = mock_client

            products = list(extractor.extract_products())

            assert len(products) == 0

    @patch("src.extractors.shopee.ShopeeExtractor.authenticate")
    @patch("src.extractors.shopee.ShopeeExtractor._ensure_authenticated")
    def test_extract_products_with_data(self, mock_ensure_auth, mock_auth):
        """Test product extraction with data."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()
            extractor._authenticated = True

            responses = [
                # Product list
                {
                    "response": {
                        "item": [{"item_id": 123}],
                        "has_next_page": False,
                    }
                },
                # Product details
                {
                    "response": {
                        "item_list": [
                            {"item_id": 123, "item_name": "Test Product"}
                        ]
                    }
                },
            ]

            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.side_effect = responses
            mock_client.get.return_value = mock_response
            extractor._client = mock_client

            products = list(extractor.extract_products())

            assert len(products) == 1
            assert products[0]["type"] == "product"
            assert products[0]["platform"] == "shopee"
            assert products[0]["data"]["item_name"] == "Test Product"


class TestShopeeExtractMethod:
    """Tests for the main extract method."""

    @patch("src.extractors.shopee.ShopeeExtractor.authenticate")
    @patch("src.extractors.shopee.ShopeeExtractor._ensure_authenticated")
    @patch("src.extractors.shopee.ShopeeExtractor.extract_orders")
    @patch("src.extractors.shopee.ShopeeExtractor.extract_products")
    def test_extract_all(
        self, mock_products, mock_orders, mock_ensure_auth, mock_auth
    ):
        """Test extract method with data_type='all'."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            mock_orders.return_value = iter([{"type": "order"}])
            mock_products.return_value = iter([{"type": "product"}])

            extractor = ShopeeExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(
                extractor.extract(start_date, end_date, data_type="all")
            )

            assert len(results) == 2
            mock_orders.assert_called_once()
            mock_products.assert_called_once()

    @patch("src.extractors.shopee.ShopeeExtractor.authenticate")
    @patch("src.extractors.shopee.ShopeeExtractor._ensure_authenticated")
    @patch("src.extractors.shopee.ShopeeExtractor.extract_orders")
    @patch("src.extractors.shopee.ShopeeExtractor.extract_products")
    def test_extract_orders_only(
        self, mock_products, mock_orders, mock_ensure_auth, mock_auth
    ):
        """Test extract method with data_type='orders'."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="test_token",
                shopee_refresh_token="",
            )

            mock_orders.return_value = iter([{"type": "order"}])

            extractor = ShopeeExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(
                extractor.extract(start_date, end_date, data_type="orders")
            )

            assert len(results) == 1
            mock_orders.assert_called_once()
            mock_products.assert_not_called()


class TestShopeeContextManager:
    """Tests for context manager behavior."""

    def test_context_manager(self):
        """Test that extractor works as context manager."""
        with patch("src.extractors.shopee.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                shopee_partner_id="12345",
                shopee_partner_key="test_key",
                shopee_shop_id="67890",
                shopee_access_token="",
                shopee_refresh_token="",
            )

            extractor = ShopeeExtractor()

            # Create a mock client
            mock_client = MagicMock()
            extractor._client = mock_client

            # Test __enter__ and __exit__
            with extractor:
                pass

            # Client should be closed
            mock_client.close.assert_called_once()
