"""Tests for TikTok Shop extractor."""

import hashlib
import hmac
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.tiktok_shop import TikTokShopExtractor


class TestTikTokShopSignature:
    """Tests for TikTok Shop signature generation."""

    def test_generate_signature_basic(self):
        """Test basic signature generation."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            params = {
                "app_key": "test_app_key",
                "timestamp": "1700000000",
            }

            signature = extractor._generate_signature("/order/202309/orders/search", params)

            # Verify signature format (64 char hex, lowercase)
            assert len(signature) == 64
            assert signature == signature.lower()

    def test_generate_signature_excludes_sign_and_access_token(self):
        """Test that sign and access_token are excluded from signature."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            params_without = {
                "app_key": "test_app_key",
                "timestamp": "1700000000",
            }

            params_with = {
                "app_key": "test_app_key",
                "timestamp": "1700000000",
                "sign": "old_signature",
                "access_token": "some_token",
            }

            sig_without = extractor._generate_signature("/test", params_without)
            sig_with = extractor._generate_signature("/test", params_with)

            # Signatures should be identical (sign and access_token excluded)
            assert sig_without == sig_with

    def test_generate_signature_parameter_sorting(self):
        """Test that parameters are sorted correctly."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

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

    def test_generate_signature_with_body(self):
        """Test signature generation with request body."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            params = {
                "app_key": "test_app_key",
                "timestamp": "1700000000",
            }

            sig_without_body = extractor._generate_signature("/test", params)
            sig_with_body = extractor._generate_signature(
                "/test", params, body='{"key":"value"}'
            )

            # Signatures should be different
            assert sig_without_body != sig_with_body

    def test_generate_signature_manual_verification(self):
        """Manually verify signature calculation."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="secret_key",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            params = {
                "app_key": "test_app_key",
                "timestamp": "1700000000",
            }
            path = "/test/path"

            # Manual calculation:
            # path + sorted params + wrap with secret
            # /test/path + app_keytest_app_key + timestamp1700000000
            base_string = f"{path}app_keytest_app_keytimestamp1700000000"
            base_string = f"secret_key{base_string}secret_key"

            expected_signature = hmac.new(
                "secret_key".encode("utf-8"),
                base_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            signature = extractor._generate_signature(path, params)
            assert signature == expected_signature


class TestTikTokShopInitialization:
    """Tests for TikTok Shop extractor initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="test_token",
            )

            extractor = TikTokShopExtractor()

            assert extractor.app_key == "test_app_key"
            assert extractor.app_secret == "test_secret"
            assert extractor._access_token == "test_token"
            assert extractor.shop_cipher is None

    def test_initialization_with_shop_cipher(self):
        """Test initialization with shop cipher."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="test_token",
            )

            extractor = TikTokShopExtractor(shop_cipher="shop_cipher_123")

            assert extractor.shop_cipher == "shop_cipher_123"


class TestTikTokShopAuthentication:
    """Tests for TikTok Shop authentication."""

    def test_authenticate_missing_credentials(self):
        """Test authentication fails without credentials."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="",
                tiktok_shop_app_secret="",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "Missing TikTok Shop credentials" in str(exc_info.value)

    def test_authenticate_no_token(self):
        """Test authentication fails without token."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            from src.extractors.base import AuthenticationError

            with pytest.raises(AuthenticationError) as exc_info:
                extractor.authenticate()

            assert "No access_token available" in str(exc_info.value)

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._get_shop_info")
    def test_authenticate_with_valid_token(self, mock_get_shop):
        """Test authentication succeeds with valid token."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_get_shop.return_value = {"shop_name": "Test Shop"}

            extractor = TikTokShopExtractor()
            result = extractor.authenticate()

            assert result is True
            assert extractor._authenticated is True


class TestTikTokShopAuthorizationURL:
    """Tests for OAuth authorization URL generation."""

    def test_get_authorization_url(self):
        """Test authorization URL generation."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()
            redirect_url = "https://myapp.com/callback"

            url = extractor.get_authorization_url(redirect_url)

            assert "services.tiktokshop.com/open/authorize" in url
            assert "app_key=test_app_key" in url
            assert "redirect_url=" in url

    def test_get_authorization_url_with_state(self):
        """Test authorization URL generation with state."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()
            redirect_url = "https://myapp.com/callback"

            url = extractor.get_authorization_url(redirect_url, state="my_state")

            assert "state=my_state" in url


class TestTikTokShopCommonParams:
    """Tests for common parameter building."""

    def test_build_common_params(self):
        """Test building common parameters."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()
            params = extractor._build_common_params()

            assert params["app_key"] == "test_app_key"
            assert "timestamp" in params

    def test_build_common_params_with_shop_cipher(self):
        """Test building common parameters with shop cipher."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor(shop_cipher="shop_cipher_123")
            params = extractor._build_common_params()

            assert params["shop_cipher"] == "shop_cipher_123"


class TestTikTokShopOrderExtraction:
    """Tests for order extraction."""

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.authenticate")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._ensure_authenticated")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._make_request")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._get_order_detail")
    def test_extract_orders_empty(
        self, mock_detail, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test order extraction with empty response."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_request.return_value = {
                "code": 0,
                "data": {"orders": [], "next_page_token": None}
            }

            extractor = TikTokShopExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            orders = list(extractor.extract_orders(start_date, end_date))

            assert len(orders) == 0

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.authenticate")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._ensure_authenticated")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._make_request")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._get_order_detail")
    def test_extract_orders_with_data(
        self, mock_detail, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test order extraction with data."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_request.return_value = {
                "code": 0,
                "data": {
                    "orders": [{"id": "order_123"}],
                    "next_page_token": None,
                }
            }
            mock_detail.return_value = {
                "id": "order_123",
                "status": "COMPLETED",
            }

            extractor = TikTokShopExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            orders = list(extractor.extract_orders(start_date, end_date))

            assert len(orders) == 1
            assert orders[0]["type"] == "order"
            assert orders[0]["platform"] == "tiktok_shop"
            assert orders[0]["data"]["status"] == "COMPLETED"


class TestTikTokShopProductExtraction:
    """Tests for product extraction."""

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.authenticate")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._ensure_authenticated")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._make_request")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._get_product_detail")
    def test_extract_products_empty(
        self, mock_detail, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test product extraction with empty response."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_request.return_value = {
                "code": 0,
                "data": {"products": [], "next_page_token": None}
            }

            extractor = TikTokShopExtractor()
            extractor._authenticated = True

            products = list(extractor.extract_products())

            assert len(products) == 0

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.authenticate")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._ensure_authenticated")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._make_request")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._get_product_detail")
    def test_extract_products_with_data(
        self, mock_detail, mock_request, mock_ensure_auth, mock_auth
    ):
        """Test product extraction with data."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_request.return_value = {
                "code": 0,
                "data": {
                    "products": [{"id": "product_123"}],
                    "next_page_token": None,
                }
            }
            mock_detail.return_value = {
                "id": "product_123",
                "title": "Test Product",
            }

            extractor = TikTokShopExtractor()
            extractor._authenticated = True

            products = list(extractor.extract_products())

            assert len(products) == 1
            assert products[0]["type"] == "product"
            assert products[0]["platform"] == "tiktok_shop"
            assert products[0]["data"]["title"] == "Test Product"


class TestTikTokShopExtractMethod:
    """Tests for the main extract method."""

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.authenticate")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._ensure_authenticated")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.extract_orders")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.extract_products")
    def test_extract_all(
        self, mock_products, mock_orders, mock_ensure_auth, mock_auth
    ):
        """Test extract method with data_type='all'."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_orders.return_value = iter([{"type": "order"}])
            mock_products.return_value = iter([{"type": "product"}])

            extractor = TikTokShopExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(
                extractor.extract(start_date, end_date, data_type="all")
            )

            assert len(results) == 2
            mock_orders.assert_called_once()
            mock_products.assert_called_once()

    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.authenticate")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor._ensure_authenticated")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.extract_orders")
    @patch("src.extractors.tiktok_shop.TikTokShopExtractor.extract_products")
    def test_extract_orders_only(
        self, mock_products, mock_orders, mock_ensure_auth, mock_auth
    ):
        """Test extract method with data_type='orders'."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="valid_token",
            )

            mock_orders.return_value = iter([{"type": "order"}])

            extractor = TikTokShopExtractor()
            extractor._authenticated = True

            start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)

            results = list(
                extractor.extract(start_date, end_date, data_type="orders")
            )

            assert len(results) == 1
            mock_orders.assert_called_once()
            mock_products.assert_not_called()


class TestTikTokShopContextManager:
    """Tests for context manager behavior."""

    def test_context_manager(self):
        """Test that extractor works as context manager."""
        with patch("src.extractors.tiktok_shop.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                tiktok_shop_app_key="test_app_key",
                tiktok_shop_app_secret="test_secret",
                tiktok_shop_access_token="",
            )

            extractor = TikTokShopExtractor()

            # Create a mock client
            mock_client = MagicMock()
            extractor._client = mock_client

            # Test __enter__ and __exit__
            with extractor:
                pass

            # Client should be closed
            mock_client.close.assert_called_once()
