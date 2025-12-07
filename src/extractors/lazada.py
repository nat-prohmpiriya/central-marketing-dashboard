"""Lazada Open Platform API extractor.

Lazada API documentation:
- Authentication: HMAC-SHA256 signature
- Rate limit: 50 requests per minute (varies by endpoint)
- Token expiry: Access token validity varies by region
"""

import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Generator
from urllib.parse import quote

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class LazadaExtractor(BaseExtractor):
    """Extractor for Lazada Open Platform API.

    Implements Lazada's signature-based authentication and provides
    methods for extracting orders and products data.

    Regional endpoints:
    - Thailand: https://api.lazada.co.th/rest
    - Singapore: https://api.lazada.sg/rest
    - Malaysia: https://api.lazada.com.my/rest
    - Vietnam: https://api.lazada.vn/rest
    - Philippines: https://api.lazada.com.ph/rest
    - Indonesia: https://api.lazada.co.id/rest
    """

    platform_name = "lazada"

    # Regional API endpoints
    REGIONAL_ENDPOINTS = {
        "TH": "https://api.lazada.co.th/rest",
        "SG": "https://api.lazada.sg/rest",
        "MY": "https://api.lazada.com.my/rest",
        "VN": "https://api.lazada.vn/rest",
        "PH": "https://api.lazada.com.ph/rest",
        "ID": "https://api.lazada.co.id/rest",
    }

    # Default to Thailand
    base_url = "https://api.lazada.co.th/rest"

    # Auth endpoints (global)
    AUTH_URL = "https://auth.lazada.com/rest"
    TOKEN_CREATE_PATH = "/auth/token/create"
    TOKEN_REFRESH_PATH = "/auth/token/refresh"

    # API endpoints
    ORDER_LIST_PATH = "/orders/get"
    ORDER_DETAIL_PATH = "/order/get"
    ORDER_ITEMS_PATH = "/order/items/get"
    PRODUCT_LIST_PATH = "/products/get"
    PRODUCT_DETAIL_PATH = "/product/item/get"
    SELLER_INFO_PATH = "/seller/get"

    def __init__(self, region: str = "TH"):
        """Initialize Lazada extractor.

        Args:
            region: Country code (TH, SG, MY, VN, PH, ID)
        """
        super().__init__()
        settings = get_settings()

        # Set regional endpoint
        self.region = region.upper()
        self.base_url = self.REGIONAL_ENDPOINTS.get(
            self.region, self.REGIONAL_ENDPOINTS["TH"]
        )

        # Credentials
        self.app_key = settings.lazada_app_key
        self.app_secret = settings.lazada_app_secret

        # Tokens from settings (can be refreshed)
        self._access_token = settings.lazada_access_token or None
        self._refresh_token = settings.lazada_refresh_token or None

    def _generate_signature(
        self,
        api_path: str,
        params: dict[str, Any],
    ) -> str:
        """Generate HMAC-SHA256 signature for Lazada API.

        The signature is calculated as:
        1. Sort all parameters alphabetically by key
        2. Concatenate: api_path + key1 + value1 + key2 + value2 + ...
        3. Apply HMAC-SHA256 with app_secret as key
        4. Return uppercase hex digest

        Args:
            api_path: API endpoint path (e.g., /orders/get)
            params: Request parameters (excluding 'sign')

        Returns:
            Uppercase hexadecimal signature string
        """
        # Sort parameters by key
        sorted_params = sorted(params.items(), key=lambda x: x[0])

        # Build base string: path + sorted key-value pairs
        base_string = api_path
        for key, value in sorted_params:
            base_string += f"{key}{value}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.app_secret.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature.upper()

    def _get_timestamp(self) -> int:
        """Get current timestamp in milliseconds."""
        return int(time.time() * 1000)

    def _build_common_params(self) -> dict[str, Any]:
        """Build common parameters for API requests.

        Returns:
            Dictionary with common parameters
        """
        return {
            "app_key": self.app_key,
            "timestamp": str(self._get_timestamp()),
            "sign_method": "sha256",
        }

    def _make_request(
        self,
        api_path: str,
        params: dict[str, Any] | None = None,
        method: str = "GET",
        use_auth_url: bool = False,
    ) -> dict[str, Any]:
        """Make a signed request to Lazada API.

        Args:
            api_path: API endpoint path
            params: Additional parameters
            method: HTTP method
            use_auth_url: Use auth URL instead of regional URL

        Returns:
            API response data

        Raises:
            APIError: If API returns an error
        """
        # Build parameters
        all_params = self._build_common_params()
        if params:
            all_params.update(params)

        # Add access token for non-auth endpoints
        if not use_auth_url and self._access_token:
            all_params["access_token"] = self._access_token

        # Generate signature
        signature = self._generate_signature(api_path, all_params)
        all_params["sign"] = signature

        # Select base URL
        base = self.AUTH_URL if use_auth_url else self.base_url

        # Apply rate limiting
        self.rate_limiter.wait()

        # Make request
        self.logger.debug(
            "Making Lazada API request",
            api_path=api_path,
            method=method,
        )

        if method == "GET":
            response = self.client.get(
                f"{base}{api_path}",
                params=all_params,
            )
        else:
            response = self.client.post(
                f"{base}{api_path}",
                data=all_params,
            )

        data = response.json()

        # Check for errors
        if "code" in data and data["code"] != "0":
            raise APIError(
                message=f"Lazada API error: {data.get('message', 'Unknown error')}",
                platform=self.platform_name,
                details={
                    "code": data.get("code"),
                    "type": data.get("type"),
                    "message": data.get("message"),
                    "request_id": data.get("request_id"),
                },
            )

        return data

    def authenticate(self) -> bool:
        """Authenticate using existing tokens or refresh if expired.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.app_key or not self.app_secret:
            raise AuthenticationError(
                message="Missing Lazada credentials (app_key or app_secret)",
                platform=self.platform_name,
            )

        # If we have access token, verify it's working
        if self._access_token:
            try:
                self._get_seller_info()
                self._authenticated = True
                self.logger.info("Authenticated with existing access token")
                return True
            except APIError as e:
                # Token might be expired, try to refresh
                if "expired" in str(e).lower() or "invalid" in str(e).lower():
                    self.logger.info("Access token expired, attempting refresh")
                else:
                    raise

        # Try to refresh token
        if self._refresh_token:
            return self._refresh_access_token()

        raise AuthenticationError(
            message="No valid access_token or refresh_token available. "
            "Please complete OAuth authorization flow first.",
            platform=self.platform_name,
        )

    def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token.

        Returns:
            True if refresh successful

        Raises:
            AuthenticationError: If refresh fails
        """
        params = {
            "refresh_token": self._refresh_token,
        }

        try:
            data = self._make_request(
                self.TOKEN_REFRESH_PATH,
                params=params,
                use_auth_url=True,
            )

            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")

            # Calculate expiry
            expire_in = data.get("expires_in", 604800)  # Default 7 days
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expire_in
            )

            self._authenticated = True
            self.logger.info(
                "Access token refreshed",
                expires_at=self._token_expires_at.isoformat(),
            )
            return True

        except APIError as e:
            raise AuthenticationError(
                message=f"Failed to refresh access token: {e}",
                platform=self.platform_name,
            ) from e

    def _get_seller_info(self) -> dict[str, Any]:
        """Get seller information to verify authentication.

        Returns:
            Seller information dictionary
        """
        data = self._make_request(self.SELLER_INFO_PATH)
        return data.get("data", {})

    def get_authorization_url(self, redirect_url: str) -> str:
        """Generate OAuth authorization URL.

        Args:
            redirect_url: URL to redirect after authorization

        Returns:
            Authorization URL for seller to visit
        """
        # URL encode the redirect URL
        encoded_redirect = quote(redirect_url, safe="")

        auth_url = (
            f"https://auth.lazada.com/oauth/authorize"
            f"?response_type=code"
            f"&force_auth=true"
            f"&redirect_uri={encoded_redirect}"
            f"&client_id={self.app_key}"
        )

        return auth_url

    def exchange_code_for_token(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response with access_token and refresh_token
        """
        params = {
            "code": code,
        }

        data = self._make_request(
            self.TOKEN_CREATE_PATH,
            params=params,
            use_auth_url=True,
        )

        # Store tokens
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")

        expire_in = data.get("expires_in", 604800)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expire_in
        )

        return data

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract orders and products from Lazada.

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
        status: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract orders within date range.

        Args:
            start_date: Start date for orders
            end_date: End date for orders
            status: Filter by status (pending, shipped, delivered, etc.)

        Yields:
            Order detail records with items
        """
        self._ensure_authenticated()

        # Format dates as ISO string
        start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S%z")
        end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S%z")

        self.logger.info(
            "Extracting orders",
            start_date=start_str,
            end_date=end_str,
            status=status,
        )

        # Paginate through order list
        offset = 0
        limit = 100
        total_orders = 0

        while True:
            params = {
                "created_after": start_str,
                "created_before": end_str,
                "offset": str(offset),
                "limit": str(limit),
                "sort_direction": "ASC",
                "sort_by": "created_at",
            }

            if status:
                params["status"] = status

            data = self._make_request(self.ORDER_LIST_PATH, params=params)

            orders = data.get("data", {}).get("orders", [])

            if not orders:
                break

            # Get order details with items
            for order in orders:
                order_id = order.get("order_id")
                if order_id:
                    # Get order items
                    items = self._get_order_items(order_id)
                    order["items"] = items

                    yield {
                        "type": "order",
                        "platform": self.platform_name,
                        "region": self.region,
                        "data": order,
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    }

                    total_orders += 1

            # Check for more pages
            count_total = data.get("data", {}).get("countTotal", 0)
            offset += limit

            if offset >= count_total:
                break

        self.logger.info("Orders extraction complete", total_orders=total_orders)

    def _get_order_items(self, order_id: int | str) -> list[dict[str, Any]]:
        """Get items for a specific order.

        Args:
            order_id: Order ID

        Returns:
            List of order items
        """
        params = {
            "order_id": str(order_id),
        }

        try:
            data = self._make_request(self.ORDER_ITEMS_PATH, params=params)
            return data.get("data", [])
        except APIError as e:
            self.logger.warning(
                "Failed to get order items",
                order_id=order_id,
                error=str(e),
            )
            return []

    def extract_products(
        self,
        filter_type: str = "all",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract all products from the store.

        Args:
            filter_type: Filter type (live, inactive, deleted, image-missing, etc.)

        Yields:
            Product detail records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting products", filter_type=filter_type)

        offset = 0
        limit = 100
        total_products = 0

        while True:
            params = {
                "filter": filter_type,
                "offset": str(offset),
                "limit": str(limit),
            }

            data = self._make_request(self.PRODUCT_LIST_PATH, params=params)

            products = data.get("data", {}).get("products", [])

            if not products:
                break

            for product in products:
                yield {
                    "type": "product",
                    "platform": self.platform_name,
                    "region": self.region,
                    "data": product,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }

                total_products += 1

            # Check for more pages
            total_count = data.get("data", {}).get("total_products", 0)
            offset += limit

            if offset >= total_count:
                break

        self.logger.info("Products extraction complete", total_products=total_products)

    def get_product_detail(self, item_id: int | str) -> dict[str, Any]:
        """Get detailed information for a specific product.

        Args:
            item_id: Product item ID

        Returns:
            Product detail dictionary
        """
        self._ensure_authenticated()

        params = {
            "item_id": str(item_id),
        }

        data = self._make_request(self.PRODUCT_DETAIL_PATH, params=params)
        return data.get("data", {})
