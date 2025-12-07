"""Shopee Open Platform API extractor.

Shopee API v2 documentation:
- Authentication: HMAC-SHA256 signature
- Rate limit: 60 requests per minute
- Token expiry: 4 hours (access_token), 30 days (refresh_token)
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


class ShopeeExtractor(BaseExtractor):
    """Extractor for Shopee Open Platform API v2.

    Implements Shopee's signature-based authentication and provides
    methods for extracting orders and products data.

    Authentication flow:
    1. Generate authorization URL for shop owner
    2. Shop owner grants permission, receives auth code
    3. Exchange auth code for access_token and refresh_token
    4. Use access_token for API calls (4 hour expiry)
    5. Use refresh_token to get new access_token (30 day expiry)
    """

    platform_name = "shopee"
    base_url = "https://partner.shopeemobile.com"

    # API endpoints
    AUTH_PATH = "/api/v2/auth/token/get"
    REFRESH_PATH = "/api/v2/auth/access_token/get"
    ORDER_LIST_PATH = "/api/v2/order/get_order_list"
    ORDER_DETAIL_PATH = "/api/v2/order/get_order_detail"
    PRODUCT_LIST_PATH = "/api/v2/product/get_item_list"
    PRODUCT_DETAIL_PATH = "/api/v2/product/get_item_base_info"
    SHOP_INFO_PATH = "/api/v2/shop/get_shop_info"

    def __init__(self):
        super().__init__()
        settings = get_settings()

        # Credentials
        self.partner_id = int(settings.shopee_partner_id) if settings.shopee_partner_id else 0
        self.partner_key = settings.shopee_partner_key
        self.shop_id = int(settings.shopee_shop_id) if settings.shopee_shop_id else 0

        # Tokens from settings (can be refreshed)
        self._access_token = settings.shopee_access_token or None
        self._refresh_token = settings.shopee_refresh_token or None

    def _generate_signature(
        self,
        path: str,
        timestamp: int,
        access_token: str | None = None,
        shop_id: int | None = None,
    ) -> str:
        """Generate HMAC-SHA256 signature for Shopee API v2.

        Args:
            path: API endpoint path (e.g., /api/v2/shop/get_shop_info)
            timestamp: Unix timestamp in seconds
            access_token: Access token (required for shop APIs)
            shop_id: Shop ID (required for shop APIs)

        Returns:
            Hexadecimal signature string
        """
        # Base string depends on API type
        # Public APIs: partner_id + path + timestamp
        # Shop APIs: partner_id + path + timestamp + access_token + shop_id
        base_string = f"{self.partner_id}{path}{timestamp}"

        if access_token:
            base_string += access_token
        if shop_id:
            base_string += str(shop_id)

        signature = hmac.new(
            self.partner_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def _get_timestamp(self) -> int:
        """Get current Unix timestamp."""
        return int(time.time())

    def _build_common_params(
        self,
        path: str,
        include_shop: bool = True,
    ) -> dict[str, Any]:
        """Build common parameters for API requests.

        Args:
            path: API endpoint path
            include_shop: Whether to include shop_id and access_token

        Returns:
            Dictionary with common parameters
        """
        timestamp = self._get_timestamp()

        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
        }

        if include_shop:
            params["shop_id"] = self.shop_id
            params["access_token"] = self._access_token
            params["sign"] = self._generate_signature(
                path, timestamp, self._access_token, self.shop_id
            )
        else:
            params["sign"] = self._generate_signature(path, timestamp)

        return params

    def authenticate(self) -> bool:
        """Authenticate using existing tokens or refresh if expired.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.partner_id or not self.partner_key:
            raise AuthenticationError(
                message="Missing Shopee credentials (partner_id or partner_key)",
                platform=self.platform_name,
            )

        if not self.shop_id:
            raise AuthenticationError(
                message="Missing Shopee shop_id",
                platform=self.platform_name,
            )

        # If we have access token, verify it's working
        if self._access_token:
            try:
                self._get_shop_info()
                self._authenticated = True
                self.logger.info("Authenticated with existing access token")
                return True
            except APIError as e:
                # Token might be expired, try to refresh
                if "invalid" in str(e).lower() or "expired" in str(e).lower():
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
        timestamp = self._get_timestamp()
        path = self.REFRESH_PATH

        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": self._generate_signature(path, timestamp),
            "shop_id": self.shop_id,
            "refresh_token": self._refresh_token,
        }

        try:
            response = self.client.get(path, params=params)
            data = response.json()

            if "error" in data and data["error"]:
                raise AuthenticationError(
                    message=f"Token refresh failed: {data.get('message', data.get('error'))}",
                    platform=self.platform_name,
                    details=data,
                )

            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token")

            # Calculate expiry (default 4 hours)
            expire_in = data.get("expire_in", 14400)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expire_in)

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
        path = self.SHOP_INFO_PATH
        params = self._build_common_params(path)

        response = self.client.get(path, params=params)
        data = response.json()

        if "error" in data and data["error"]:
            raise APIError(
                message=f"Failed to get shop info: {data.get('message', data.get('error'))}",
                platform=self.platform_name,
                details=data,
            )

        return data.get("response", {})

    def get_authorization_url(self, redirect_url: str) -> str:
        """Generate OAuth authorization URL for shop owner.

        Args:
            redirect_url: URL to redirect after authorization

        Returns:
            Authorization URL for shop owner to visit
        """
        timestamp = self._get_timestamp()
        path = "/api/v2/shop/auth_partner"

        sign = self._generate_signature(path, timestamp)

        auth_url = (
            f"{self.base_url}{path}"
            f"?partner_id={self.partner_id}"
            f"&timestamp={timestamp}"
            f"&sign={sign}"
            f"&redirect={redirect_url}"
        )

        return auth_url

    def exchange_code_for_token(self, code: str, shop_id: int) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from OAuth callback
            shop_id: Shop ID from OAuth callback

        Returns:
            Token response with access_token and refresh_token
        """
        timestamp = self._get_timestamp()
        path = self.AUTH_PATH

        body = {
            "code": code,
            "partner_id": self.partner_id,
            "shop_id": shop_id,
        }

        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "sign": self._generate_signature(path, timestamp),
        }

        response = self.client.post(path, params=params, json=body)
        data = response.json()

        if "error" in data and data["error"]:
            raise AuthenticationError(
                message=f"Token exchange failed: {data.get('message', data.get('error'))}",
                platform=self.platform_name,
                details=data,
            )

        # Store tokens
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        self.shop_id = shop_id

        expire_in = data.get("expire_in", 14400)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expire_in)

        return data

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract orders and products from Shopee.

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
        order_status: str = "ALL",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract orders within date range.

        Args:
            start_date: Start date for orders
            end_date: End date for orders
            order_status: Filter by status (UNPAID, READY_TO_SHIP, etc.)

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
        cursor = ""
        page_size = 100
        total_orders = 0

        while True:
            path = self.ORDER_LIST_PATH
            params = self._build_common_params(path)
            params.update(
                {
                    "time_range_field": "create_time",
                    "time_from": start_ts,
                    "time_to": end_ts,
                    "page_size": page_size,
                    "order_status": order_status,
                }
            )

            if cursor:
                params["cursor"] = cursor

            # Rate limit
            self.rate_limiter.wait()

            response = self.client.get(path, params=params)
            data = response.json()

            if "error" in data and data["error"]:
                raise APIError(
                    message=f"Failed to get order list: {data.get('message')}",
                    platform=self.platform_name,
                    details=data,
                )

            order_list = data.get("response", {}).get("order_list", [])

            if not order_list:
                break

            # Get order details in batches
            order_sns = [order["order_sn"] for order in order_list]
            yield from self._get_order_details(order_sns)

            total_orders += len(order_list)

            # Check for more pages
            if not data.get("response", {}).get("more"):
                break

            cursor = data.get("response", {}).get("next_cursor", "")

        self.logger.info("Orders extraction complete", total_orders=total_orders)

    def _get_order_details(
        self,
        order_sns: list[str],
    ) -> Generator[dict[str, Any], None, None]:
        """Get detailed information for orders.

        Args:
            order_sns: List of order serial numbers

        Yields:
            Order detail records
        """
        # Shopee allows max 50 orders per request
        batch_size = 50

        for i in range(0, len(order_sns), batch_size):
            batch = order_sns[i : i + batch_size]

            path = self.ORDER_DETAIL_PATH
            params = self._build_common_params(path)
            params["order_sn_list"] = ",".join(batch)

            # Request optional fields
            params["response_optional_fields"] = ",".join(
                [
                    "buyer_user_id",
                    "buyer_username",
                    "estimated_shipping_fee",
                    "recipient_address",
                    "actual_shipping_fee",
                    "goods_to_declare",
                    "note",
                    "note_update_time",
                    "item_list",
                    "pay_time",
                    "dropshipper",
                    "dropshipper_phone",
                    "split_up",
                    "buyer_cancel_reason",
                    "cancel_by",
                    "cancel_reason",
                    "actual_shipping_fee_confirmed",
                    "buyer_cpf_id",
                    "fulfillment_flag",
                    "pickup_done_time",
                    "package_list",
                    "shipping_carrier",
                    "payment_method",
                    "total_amount",
                    "invoice_data",
                    "checkout_shipping_carrier",
                    "reverse_shipping_fee",
                    "order_chargeable_weight_gram",
                ]
            )

            self.rate_limiter.wait()

            response = self.client.get(path, params=params)
            data = response.json()

            if "error" in data and data["error"]:
                self.logger.warning(
                    "Failed to get order details",
                    error=data.get("message"),
                    order_sns=batch,
                )
                continue

            for order in data.get("response", {}).get("order_list", []):
                yield {
                    "type": "order",
                    "platform": self.platform_name,
                    "shop_id": self.shop_id,
                    "data": order,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }

    def extract_products(
        self,
        item_status: str = "NORMAL",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract all products from the shop.

        Args:
            item_status: Filter by status (NORMAL, BANNED, DELETED, etc.)

        Yields:
            Product detail records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting products", status=item_status)

        offset = 0
        page_size = 100
        total_products = 0

        while True:
            path = self.PRODUCT_LIST_PATH
            params = self._build_common_params(path)
            params.update(
                {
                    "offset": offset,
                    "page_size": page_size,
                    "item_status": item_status,
                }
            )

            self.rate_limiter.wait()

            response = self.client.get(path, params=params)
            data = response.json()

            if "error" in data and data["error"]:
                raise APIError(
                    message=f"Failed to get product list: {data.get('message')}",
                    platform=self.platform_name,
                    details=data,
                )

            item_list = data.get("response", {}).get("item", [])

            if not item_list:
                break

            # Get product details
            item_ids = [item["item_id"] for item in item_list]
            yield from self._get_product_details(item_ids)

            total_products += len(item_list)

            # Check for more pages
            if not data.get("response", {}).get("has_next_page"):
                break

            offset += page_size

        self.logger.info("Products extraction complete", total_products=total_products)

    def _get_product_details(
        self,
        item_ids: list[int],
    ) -> Generator[dict[str, Any], None, None]:
        """Get detailed information for products.

        Args:
            item_ids: List of item IDs

        Yields:
            Product detail records
        """
        # Shopee allows max 50 items per request
        batch_size = 50

        for i in range(0, len(item_ids), batch_size):
            batch = item_ids[i : i + batch_size]

            path = self.PRODUCT_DETAIL_PATH
            params = self._build_common_params(path)
            params["item_id_list"] = ",".join(str(id) for id in batch)

            self.rate_limiter.wait()

            response = self.client.get(path, params=params)
            data = response.json()

            if "error" in data and data["error"]:
                self.logger.warning(
                    "Failed to get product details",
                    error=data.get("message"),
                    item_ids=batch,
                )
                continue

            for item in data.get("response", {}).get("item_list", []):
                yield {
                    "type": "product",
                    "platform": self.platform_name,
                    "shop_id": self.shop_id,
                    "data": item,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
