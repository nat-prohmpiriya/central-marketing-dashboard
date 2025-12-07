"""Tests for Lazada extractor."""

import hashlib
import hmac
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.lazada import LazadaExtractor


class TestLazadaSignature:
    """Tests for Lazada signature generation."""

    def test_generate_signature_basic(self):
        """Test basic signature generation."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            params = {
                "app_key": "123456",
                "timestamp": "1700000000000",
                "sign_method": "sha256",
            }

            signature = extractor._generate_signature("/orders/get", params)

            # Verify signature format (64 char hex, uppercase)
            assert len(signature) == 64
            assert signature == signature.upper()

    def test_generate_signature_parameter_sorting(self):
        """Test that parameters are sorted correctly."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            # Parameters in random order
            params1 = {
                "z_param": "z_value",
                "a_param": "a_value",
                "m_param": "m_value",
            }

            # Same parameters in different order
            params2 = {
                "a_param": "a_value",
                "m_param": "m_value",
                "z_param": "z_value",
            }

            sig1 = extractor._generate_signature("/test", params1)
            sig2 = extractor._generate_signature("/test", params2)

            # Signatures should be identical
            assert sig1 == sig2

    def test_generate_signature_manual_verification(self):
        """Manually verify signature calculation."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="secret_key",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            params = {
                "app_key": "123456",
                "timestamp": "1700000000000",
            }
            api_path = "/orders/get"

            # Manual calculation: path + sorted key-value pairs
            # /orders/get + app_key123456 + timestamp1700000000000
            base_string = f"{api_path}app_key123456timestamp1700000000000"

            expected_signature = hmac.new(
                "secret_key".encode("utf-8"),
                base_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest().upper()

            signature = extractor._generate_signature(api_path, params)
            assert signature == expected_signature


class TestLazadaRegionalEndpoints:
    """Tests for regional endpoint selection."""

    @pytest.mark.parametrize(
        "region,expected_url",
        [
            ("TH", "https://api.lazada.co.th/rest"),
            ("SG", "https://api.lazada.sg/rest"),
            ("MY", "https://api.lazada.com.my/rest"),
            ("VN", "https://api.lazada.vn/rest"),
            ("PH", "https://api.lazada.com.ph/rest"),
            ("ID", "https://api.lazada.co.id/rest"),
        ],
    )
    def test_regional_endpoint_selection(self, region, expected_url):
        """Test correct regional endpoint is selected."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor(region=region)

            assert extractor.base_url == expected_url
            assert extractor.region == region

    def test_default_region_is_thailand(self):
        """Test default region is Thailand."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            assert extractor.region == "TH"
            assert extractor.base_url == "https://api.lazada.co.th/rest"

    def test_unknown_region_defaults_to_thailand(self):
        """Test unknown region falls back to Thailand."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor(region="XX")

            assert extractor.base_url == "https://api.lazada.co.th/rest"


class TestLazadaAuthentication:
    """Tests for Lazada authentication."""

    def test_authenticate_missing_credentials(self):
        """Test authentication fails without credentials."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="",
                lazada_app_secret="",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "Missing Lazada credentials" in str(exc_info.value)

    def test_authenticate_no_tokens(self):
        """Test authentication fails without tokens."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "No valid access_token or refresh_token" in str(exc_info.value)

    @patch("src.extractors.lazada.LazadaExtractor._get_seller_info")
    def test_authenticate_with_valid_token(self, mock_get_seller):
        """Test authentication succeeds with valid token."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="refresh_token",
            )

            mock_get_seller.return_value = {"name": "Test Seller"}

            extractor = LazadaExtractor()
            result = extractor.authenticate()

            assert result is True
            assert extractor._authenticated is True


class TestLazadaAuthorizationURL:
    """Tests for OAuth authorization URL generation."""

    def test_get_authorization_url(self):
        """Test authorization URL generation."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()
            redirect_url = "https://myapp.com/callback"

            url = extractor.get_authorization_url(redirect_url)

            assert "auth.lazada.com/oauth/authorize" in url
            assert "response_type=code" in url
            assert "client_id=123456" in url
            assert "redirect_uri=" in url


class TestLazadaCommonParams:
    """Tests for common parameter building."""

    def test_build_common_params(self):
        """Test building common parameters."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()
            params = extractor._build_common_params()

            assert params["app_key"] == "123456"
            assert params["sign_method"] == "sha256"
            assert "timestamp" in params


class TestLazadaOrderExtraction:
    """Tests for order extraction."""

    @patch("src.extractors.lazada.LazadaExtractor.authenticate")
    @patch("src.extractors.lazada.LazadaExtractor._ensure_authenticated")
    @patch("src.extractors.lazada.LazadaExtractor._make_request")
    @patch("src.extractors.lazada.LazadaExtractor._get_order_items")
    def test_extract_orders_empty(
        self, mock_items, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test order extraction with empty response."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="",
            )

            mock_request.return_value = {
                "data": {"orders": [], "countTotal": 0}
            }

            extractor = LazadaExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            orders = list(extractor.extract_orders(start_date, end_date))

            assert len(orders) == 0

    @patch("src.extractors.lazada.LazadaExtractor.authenticate")
    @patch("src.extractors.lazada.LazadaExtractor._ensure_authenticated")
    @patch("src.extractors.lazada.LazadaExtractor._make_request")
    @patch("src.extractors.lazada.LazadaExtractor._get_order_items")
    def test_extract_orders_with_data(
        self, mock_items, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test order extraction with data."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="",
            )

            mock_request.return_value = {
                "data": {
                    "orders": [
                        {"order_id": 123, "status": "pending"}
                    ],
                    "countTotal": 1,
                }
            }
            mock_items.return_value = [{"item_id": 456}]

            extractor = LazadaExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            orders = list(extractor.extract_orders(start_date, end_date))

            assert len(orders) == 1
            assert orders[0]["type"] == "order"
            assert orders[0]["platform"] == "lazada"
            assert orders[0]["region"] == "TH"
            assert orders[0]["data"]["items"] == [{"item_id": 456}]


class TestLazadaProductExtraction:
    """Tests for product extraction."""

    @patch("src.extractors.lazada.LazadaExtractor.authenticate")
    @patch("src.extractors.lazada.LazadaExtractor._ensure_authenticated")
    @patch("src.extractors.lazada.LazadaExtractor._make_request")
    def test_extract_products_empty(
        self, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test product extraction with empty response."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="",
            )

            mock_request.return_value = {
                "data": {"products": [], "total_products": 0}
            }

            extractor = LazadaExtractor()
            extractor._authenticated = True

            products = list(extractor.extract_products())

            assert len(products) == 0

    @patch("src.extractors.lazada.LazadaExtractor.authenticate")
    @patch("src.extractors.lazada.LazadaExtractor._ensure_authenticated")
    @patch("src.extractors.lazada.LazadaExtractor._make_request")
    def test_extract_products_with_data(
        self, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test product extraction with data."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="",
            )

            mock_request.return_value = {
                "data": {
                    "products": [
                        {"item_id": 123, "name": "Test Product"}
                    ],
                    "total_products": 1,
                }
            }

            extractor = LazadaExtractor()
            extractor._authenticated = True

            products = list(extractor.extract_products())

            assert len(products) == 1
            assert products[0]["type"] == "product"
            assert products[0]["platform"] == "lazada"
            assert products[0]["data"]["name"] == "Test Product"


class TestLazadaExtractMethod:
    """Tests for the main extract method."""

    @patch("src.extractors.lazada.LazadaExtractor.authenticate")
    @patch("src.extractors.lazada.LazadaExtractor._ensure_authenticated")
    @patch("src.extractors.lazada.LazadaExtractor.extract_orders")
    @patch("src.extractors.lazada.LazadaExtractor.extract_products")
    def test_extract_all(
        self, mock_products, mock_orders, mock_ensure_auth, mock_auth
    ):
        """Test extract method with data_type='all'."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="",
            )

            mock_orders.return_value = iter([{"type": "order"}])
            mock_products.return_value = iter([{"type": "product"}])

            extractor = LazadaExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(
                extractor.extract(start_date, end_date, data_type="all")
            )

            assert len(results) == 2
            mock_orders.assert_called_once()
            mock_products.assert_called_once()

    @patch("src.extractors.lazada.LazadaExtractor.authenticate")
    @patch("src.extractors.lazada.LazadaExtractor._ensure_authenticated")
    @patch("src.extractors.lazada.LazadaExtractor.extract_orders")
    @patch("src.extractors.lazada.LazadaExtractor.extract_products")
    def test_extract_products_only(
        self, mock_products, mock_orders, mock_ensure_auth, mock_auth
    ):
        """Test extract method with data_type='products'."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="valid_token",
                lazada_refresh_token="",
            )

            mock_products.return_value = iter([{"type": "product"}])

            extractor = LazadaExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(
                extractor.extract(start_date, end_date, data_type="products")
            )

            assert len(results) == 1
            mock_orders.assert_not_called()
            mock_products.assert_called_once()


class TestLazadaContextManager:
    """Tests for context manager behavior."""

    def test_context_manager(self):
        """Test that extractor works as context manager."""
        with patch("src.extractors.lazada.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                lazada_app_key="123456",
                lazada_app_secret="test_secret",
                lazada_access_token="",
                lazada_refresh_token="",
            )

            extractor = LazadaExtractor()

            # Create a mock client
            mock_client = MagicMock()
            extractor._client = mock_client

            # Test __enter__ and __exit__
            with extractor:
                pass

            # Client should be closed
            mock_client.close.assert_called_once()
