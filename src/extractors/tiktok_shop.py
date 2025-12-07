"""TikTok Shop API extractor.

TikTok Shop API documentation:
- Authentication: HMAC-SHA256 signature
- Rate limit: 100 requests per minute (varies by endpoint)
- Token expiry: Access token validity varies
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Generator

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class TikTokShopExtractor(BaseExtractor):
    """Extractor for TikTok Shop API.

    Implements TikTok Shop's signature-based authentication and provides
    methods for extracting orders and products data.

    Regional endpoints:
    - Global: https://open-api.tiktokglobalshop.com
    - US: https://open-api.tiktokglobalshop.com (us region)
    - UK: https://open-api.tiktokglobalshop.com (uk region)
    - Thailand: https://open-api.tiktokglobalshop.com (th region)
    """

    platform_name = "tiktok_shop"
    base_url = "https://open-api.tiktokglobalshop.com"

    # API version
    API_VERSION = "202309"

    # Auth endpoints
    TOKEN_PATH = "/api/v2/token/get"
    TOKEN_REFRESH_PATH = "/api/v2/token/refresh"

    # API endpoints (v2)
    ORDER_LIST_PATH = "/order/202309/orders/search"
    ORDER_DETAIL_PATH = "/order/202309/orders"
    PRODUCT_LIST_PATH = "/product/202309/products/search"
    PRODUCT_DETAIL_PATH = "/product/202309/products"
    SHOP_INFO_PATH = "/seller/202309/shops"

    def __init__(self, shop_cipher: str | None = None):
        """Initialize TikTok Shop extractor.

        Args:
            shop_cipher: Shop cipher for multi-shop access (optional)
        """
        super().__init__()
        settings = get_settings()

        # Credentials
        self.app_key = settings.tiktok_shop_app_key
        self.app_secret = settings.tiktok_shop_app_secret

        # Token from settings
        self._access_token = settings.tiktok_shop_access_token or None
        self._refresh_token: str | None = None

        # Shop context
        self.shop_cipher = shop_cipher

    def _generate_signature(
        self,
        path: str,
        params: dict[str, Any],
        body: str | None = None,
    ) -> str:
        """Generate HMAC-SHA256 signature for TikTok Shop API.

        The signature is calculated as:
        1. Exclude 'sign' and 'access_token' from params
        2. Sort all parameters alphabetically by key
        3. Concatenate: path + key1value1 + key2value2 + ... + body
        4. Wrap with app_secret on both sides
        5. Apply HMAC-SHA256 with app_secret as key
        6. Return lowercase hex digest

        Args:
            path: API endpoint path (e.g., /order/202309/orders/search)
            params: Request parameters (excluding 'sign' and 'access_token')
            body: Request body as string (for POST requests)

        Returns:
            Lowercase hexadecimal signature string
        """
        # Remove sign and access_token from params
        sign_params = {
            k: v for k, v in params.items()
            if k not in ("sign", "access_token")
        }

        # Sort parameters by key
        sorted_params = sorted(sign_params.items(), key=lambda x: x[0])

        # Build base string: path + sorted key-value pairs
        base_string = path
        for key, value in sorted_params:
            base_string += f"{key}{value}"

        # Append body if present
        if body:
            base_string += body

        # Wrap with app_secret
        base_string = f"{self.app_secret}{base_string}{self.app_secret}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _get_timestamp(self) -> int:
        """Get current Unix timestamp in seconds."""
        return int(time.time())

    def _build_common_params(self) -> dict[str, Any]:
        """Build common parameters for API requests.

        Returns:
            Dictionary with common parameters
        """
        params = {
            "app_key": self.app_key,
            "timestamp": str(self._get_timestamp()),
        }

        if self.shop_cipher:
            params["shop_cipher"] = self.shop_cipher

        return params

    def _make_request(
        self,
        path: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a signed request to TikTok Shop API.

        Args:
            path: API endpoint path
            method: HTTP method (GET or POST)
            params: Query parameters
            body: Request body (for POST)

        Returns:
            API response data

        Raises:
            APIError: If API returns an error
        """
        # Build parameters
        all_params = self._build_common_params()
        if params:
            all_params.update(params)

        # Add access token
        if self._access_token:
            all_params["access_token"] = self._access_token

        # Prepare body string for signature
        body_str = None
        if body:
            import json
            body_str = json.dumps(body, separators=(",", ":"))

        # Generate signature
        signature = self._generate_signature(path, all_params, body_str)
        all_params["sign"] = signature

        # Apply rate limiting
        self.rate_limiter.wait()

        # Make request
        self.logger.debug(
            "Making TikTok Shop API request",
            path=path,
            method=method,
        )

        url = f"{self.base_url}{path}"

        if method == "GET":
            response = self.client.get(url, params=all_params)
        else:
            response = self.client.post(url, params=all_params, json=body)

        data = response.json()

        # Check for errors
        if data.get("code") != 0:
            raise APIError(
                message=f"TikTok Shop API error: {data.get('message', 'Unknown error')}",
                platform=self.platform_name,
                details={
                    "code": data.get("code"),
                    "message": data.get("message"),
                    "request_id": data.get("request_id"),
                },
            )

        return data

    def authenticate(self) -> bool:
        """Authenticate using existing token.

        Note: TikTok Shop requires OAuth flow for initial token.
        This method verifies an existing token works.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.app_key or not self.app_secret:
            raise AuthenticationError(
                message="Missing TikTok Shop credentials (app_key or app_secret)",
                platform=self.platform_name,
            )

        if not self._access_token:
            raise AuthenticationError(
                message="No access_token available. "
                "Please complete OAuth authorization flow first.",
                platform=self.platform_name,
            )

        # Verify token by getting shop info
        try:
            self._get_shop_info()
            self._authenticated = True
            self.logger.info("Authenticated with existing access token")
            return True
        except APIError as e:
            if "expired" in str(e).lower() or "invalid" in str(e).lower():
                if self._refresh_token:
                    return self._refresh_access_token()
            raise AuthenticationError(
                message=f"Authentication failed: {e}",
                platform=self.platform_name,
            ) from e

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token.

        Returns:
            True if refresh successful

        Raises:
            AuthenticationError: If refresh fails
        """
        params = self._build_common_params()
        params["refresh_token"] = self._refresh_token
        params["grant_type"] = "refresh_token"

        # Generate signature without access_token
        signature = self._generate_signature(self.TOKEN_REFRESH_PATH, params)
        params["sign"] = signature

        try:
            response = self.client.get(
                f"{self.base_url}{self.TOKEN_REFRESH_PATH}",
                params=params,
            )
            data = response.json()

            if data.get("code") != 0:
                raise AuthenticationError(
                    message=f"Token refresh failed: {data.get('message')}",
                    platform=self.platform_name,
                    details=data,
                )

            token_data = data.get("data", {})
            self._access_token = token_data.get("access_token")
            self._refresh_token = token_data.get("refresh_token")

            expire_in = token_data.get("access_token_expire_in", 86400)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expire_in
            )

            self._authenticated = True
            self.logger.info(
                "Access token refreshed",
                expires_at=self._token_expires_at.isoformat(),
            )
            return True

        except Exception as e:
            raise AuthenticationError(
                message=f"Failed to refresh access token: {e}",
                platform=self.platform_name,
            ) from e

    def _get_shop_info(self) -> dict[str, Any]:
        """Get shop information to verify authentication.

        Returns:
            Shop information dictionary
        """
        data = self._make_request(self.SHOP_INFO_PATH)
        return data.get("data", {})

    def get_authorization_url(self, redirect_url: str, state: str = "") -> str:
        """Generate OAuth authorization URL.

        Args:
            redirect_url: URL to redirect after authorization
            state: Optional state parameter for security

        Returns:
            Authorization URL for seller to visit
        """
        from urllib.parse import quote

        encoded_redirect = quote(redirect_url, safe="")

        auth_url = (
            f"https://services.tiktokshop.com/open/authorize"
            f"?app_key={self.app_key}"
            f"&redirect_url={encoded_redirect}"
        )

        if state:
            auth_url += f"&state={state}"

        return auth_url

    def exchange_code_for_token(self, auth_code: str) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            auth_code: Authorization code from OAuth callback

        Returns:
            Token response with access_token and refresh_token
        """
        params = self._build_common_params()
        params["auth_code"] = auth_code
        params["grant_type"] = "authorized_code"

        signature = self._generate_signature(self.TOKEN_PATH, params)
        params["sign"] = signature

        response = self.client.get(
            f"{self.base_url}{self.TOKEN_PATH}",
            params=params,
        )
        data = response.json()

        if data.get("code") != 0:
            raise AuthenticationError(
                message=f"Token exchange failed: {data.get('message')}",
                platform=self.platform_name,
                details=data,
            )

        token_data = data.get("data", {})
        self._access_token = token_data.get("access_token")
        self._refresh_token = token_data.get("refresh_token")

        expire_in = token_data.get("access_token_expire_in", 86400)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expire_in
        )

        return token_data

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract orders and products from TikTok Shop.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - data_type: "orders" | "products" | "all" (default: "all")

        Yields:
            Order or product records
        """
        self._ensure_authenticated()

        data_type = kwargs.get("data_type", "all")

        if data_type in ("orders", "all"):
            yield from self.extract_orders(start_date, end_date)

        if data_type in ("products", "all"):
            yield from self.extract_products()

    def extract_orders(
        self,
        start_date: datetime,
        end_date: datetime,
        order_status: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract orders within date range.

        Args:
            start_date: Start date for orders
            end_date: End date for orders
            order_status: Filter by status (optional)

        Yields:
            Order detail records
        """
        self._ensure_authenticated()

        # Convert to Unix timestamps
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())

        self.logger.info(
            "Extracting orders",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            status=order_status,
        )

        # Paginate through order list
        page_size = 100
        page_token = None
        total_orders = 0

        while True:
            body = {
                "create_time_ge": start_ts,
                "create_time_lt": end_ts,
                "page_size": page_size,
            }

            if order_status:
                body["order_status"] = order_status

            if page_token:
                body["page_token"] = page_token

            data = self._make_request(
                self.ORDER_LIST_PATH,
                method="POST",
                body=body,
            )

            response_data = data.get("data", {})
            orders = response_data.get("orders", [])

            if not orders:
                break

            # Get order details
            for order in orders:
                order_id = order.get("id")
                if order_id:
                    detail = self._get_order_detail(order_id)
                    if detail:
                        yield {
                            "type": "order",
                            "platform": self.platform_name,
                            "shop_cipher": self.shop_cipher,
                            "data": detail,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                        }
                        total_orders += 1

            # Check for more pages
            page_token = response_data.get("next_page_token")
            if not page_token:
                break

        self.logger.info("Orders extraction complete", total_orders=total_orders)

    def _get_order_detail(self, order_id: str) -> dict[str, Any] | None:
        """Get detailed information for an order.

        Args:
            order_id: Order ID

        Returns:
            Order detail dictionary or None if failed
        """
        path = f"{self.ORDER_DETAIL_PATH}/{order_id}"

        try:
            data = self._make_request(path)
            return data.get("data", {})
        except APIError as e:
            self.logger.warning(
                "Failed to get order detail",
                order_id=order_id,
                error=str(e),
            )
            return None

    def extract_products(
        self,
        status: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract all products from the shop.

        Args:
            status: Filter by status (DRAFT, PENDING, LIVE, etc.)

        Yields:
            Product detail records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting products", status=status)

        page_size = 100
        page_token = None
        total_products = 0

        while True:
            body = {
                "page_size": page_size,
            }

            if status:
                body["status"] = status

            if page_token:
                body["page_token"] = page_token

            data = self._make_request(
                self.PRODUCT_LIST_PATH,
                method="POST",
                body=body,
            )

            response_data = data.get("data", {})
            products = response_data.get("products", [])

            if not products:
                break

            for product in products:
                product_id = product.get("id")
                if product_id:
                    detail = self._get_product_detail(product_id)
                    if detail:
                        yield {
                            "type": "product",
                            "platform": self.platform_name,
                            "shop_cipher": self.shop_cipher,
                            "data": detail,
                            "extracted_at": datetime.now(timezone.utc).isoformat(),
                        }
                        total_products += 1

            # Check for more pages
            page_token = response_data.get("next_page_token")
            if not page_token:
                break

        self.logger.info("Products extraction complete", total_products=total_products)

    def _get_product_detail(self, product_id: str) -> dict[str, Any] | None:
        """Get detailed information for a product.

        Args:
            product_id: Product ID

        Returns:
            Product detail dictionary or None if failed
        """
        path = f"{self.PRODUCT_DETAIL_PATH}/{product_id}"

        try:
            data = self._make_request(path)
            return data.get("data", {})
        except APIError as e:
            self.logger.warning(
                "Failed to get product detail",
                product_id=product_id,
                error=str(e),
            )
            return None
