"""TikTok Ads (Marketing API) extractor.

TikTok Marketing API documentation:
- Authentication: OAuth 2.0 with access tokens
- Rate limit: 10 requests per second, 600 per minute
- API version: 1.3

Uses the tiktok-business-api-sdk for API interactions.
"""

from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class TikTokAdsExtractor(BaseExtractor):
    """Extractor for TikTok Marketing API.

    Provides methods for extracting campaign, ad group, and ad performance
    data from TikTok Ads Manager.

    Authentication flow:
    1. Create app in TikTok for Business Developer Portal
    2. Generate access token via OAuth flow
    3. Use access token for API calls
    """

    platform_name = "tiktok_ads"
    base_url = "https://business-api.tiktok.com/open_api/v1.3"

    # Report dimensions
    AVAILABLE_DIMENSIONS = [
        "campaign_id",
        "adgroup_id",
        "ad_id",
        "stat_time_day",
        "stat_time_hour",
        "country_code",
        "gender",
        "age",
        "platform",
    ]

    # Report metrics
    AVAILABLE_METRICS = [
        "spend",
        "impressions",
        "clicks",
        "ctr",
        "cpc",
        "cpm",
        "reach",
        "cost_per_1000_reached",
        "conversion",
        "cost_per_conversion",
        "conversion_rate",
        "video_play_actions",
        "video_watched_2s",
        "video_watched_6s",
        "video_views_p25",
        "video_views_p50",
        "video_views_p75",
        "video_views_p100",
        "likes",
        "comments",
        "shares",
        "follows",
    ]

    def __init__(self, advertiser_id: str | None = None):
        """Initialize TikTok Ads extractor.

        Args:
            advertiser_id: TikTok Ads advertiser ID
        """
        super().__init__()
        settings = get_settings()

        # Credentials
        self.app_id = settings.tiktok_ads_app_id
        self.app_secret = settings.tiktok_ads_app_secret
        self._access_token = settings.tiktok_ads_access_token or None

        # Advertiser context
        self.advertiser_id = advertiser_id or settings.tiktok_ads_advertiser_id

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        return {
            "Access-Token": self._access_token or "",
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a request to TikTok Marketing API.

        Args:
            endpoint: API endpoint path
            method: HTTP method
            params: Query parameters
            json_body: JSON body for POST requests

        Returns:
            API response data

        Raises:
            APIError: If API returns an error
        """
        self.rate_limiter.wait()

        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        if method == "GET":
            response = self.client.get(url, params=params, headers=headers)
        else:
            response = self.client.post(url, params=params, json=json_body, headers=headers)

        data = response.json()

        if data.get("code") != 0:
            raise APIError(
                message=f"TikTok Ads API error: {data.get('message', 'Unknown error')}",
                platform=self.platform_name,
                details={
                    "code": data.get("code"),
                    "message": data.get("message"),
                    "request_id": data.get("request_id"),
                },
            )

        return data.get("data", {})

    def authenticate(self) -> bool:
        """Authenticate with TikTok Marketing API.

        Verifies the access token by fetching advertiser info.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.app_id or not self.app_secret:
            raise AuthenticationError(
                message="Missing TikTok Ads credentials (app_id or app_secret)",
                platform=self.platform_name,
            )

        if not self._access_token:
            raise AuthenticationError(
                message="No access_token available. "
                "Please generate a token via TikTok OAuth flow.",
                platform=self.platform_name,
            )

        if not self.advertiser_id:
            raise AuthenticationError(
                message="No advertiser_id specified",
                platform=self.platform_name,
            )

        try:
            # Verify by fetching advertiser info
            params = {"advertiser_ids": f"[{self.advertiser_id}]"}
            data = self._make_request("/advertiser/info/", params=params)

            if data.get("list"):
                advertiser_info = data["list"][0]
                self.logger.info(
                    "Authenticated with TikTok Ads",
                    advertiser_id=self.advertiser_id,
                    advertiser_name=advertiser_info.get("name"),
                )

            self._authenticated = True
            return True

        except APIError as e:
            if "unauthorized" in str(e).lower() or "token" in str(e).lower():
                raise AuthenticationError(
                    message=f"Invalid or expired access token: {e}",
                    platform=self.platform_name,
                ) from e
            raise AuthenticationError(
                message=f"Authentication failed: {e}",
                platform=self.platform_name,
            ) from e

    def get_authorization_url(self, redirect_uri: str, state: str = "") -> str:
        """Generate OAuth authorization URL.

        Args:
            redirect_uri: URL to redirect after authorization
            state: Optional state parameter for security

        Returns:
            Authorization URL for user to visit
        """
        from urllib.parse import quote

        auth_url = (
            f"https://business-api.tiktok.com/portal/auth"
            f"?app_id={self.app_id}"
            f"&redirect_uri={quote(redirect_uri, safe='')}"
        )

        if state:
            auth_url += f"&state={state}"

        return auth_url

    def exchange_code_for_token(self, auth_code: str) -> dict[str, Any]:
        """Exchange authorization code for access token.

        Args:
            auth_code: Authorization code from OAuth callback

        Returns:
            Token response with access_token
        """
        json_body = {
            "app_id": self.app_id,
            "secret": self.app_secret,
            "auth_code": auth_code,
        }

        response = self.client.post(
            f"{self.base_url}/oauth2/access_token/",
            json=json_body,
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

        return token_data

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ads data from TikTok.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - level: "campaign" | "adgroup" | "ad" (default: "ad")
                - metrics: List of metrics to fetch
                - dimensions: List of dimensions for breakdown

        Yields:
            Performance records
        """
        self._ensure_authenticated()

        level = kwargs.get("level", "ad")
        metrics = kwargs.get("metrics")
        dimensions = kwargs.get("dimensions")

        yield from self.extract_reports(
            start_date=start_date,
            end_date=end_date,
            level=level,
            metrics=metrics,
            dimensions=dimensions,
        )

    def extract_reports(
        self,
        start_date: datetime,
        end_date: datetime,
        level: str = "ad",
        metrics: list[str] | None = None,
        dimensions: list[str] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract advertising reports.

        Args:
            start_date: Start date for reports
            end_date: End date for reports
            level: Report level (campaign, adgroup, ad)
            metrics: Metrics to retrieve
            dimensions: Dimensions for breakdown

        Yields:
            Report records
        """
        self._ensure_authenticated()

        # Default metrics
        if not metrics:
            metrics = [
                "spend",
                "impressions",
                "clicks",
                "ctr",
                "cpc",
                "cpm",
                "reach",
                "conversion",
                "cost_per_conversion",
            ]

        # Build dimensions based on level
        level_dimension_map = {
            "campaign": "campaign_id",
            "adgroup": "adgroup_id",
            "ad": "ad_id",
        }

        if level not in level_dimension_map:
            raise ValueError(f"Invalid level: {level}. Must be one of: {list(level_dimension_map.keys())}")

        # Build dimensions
        report_dimensions = [level_dimension_map[level]]
        if dimensions:
            report_dimensions.extend(dimensions)

        self.logger.info(
            "Extracting TikTok Ads reports",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            level=level,
        )

        # Build report request
        json_body = {
            "advertiser_id": self.advertiser_id,
            "report_type": "BASIC",
            "dimensions": report_dimensions,
            "metrics": metrics,
            "data_level": f"AUCTION_{level.upper()}",
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "page": 1,
            "page_size": 1000,
        }

        total_records = 0

        while True:
            try:
                data = self._make_request(
                    "/report/integrated/get/",
                    method="POST",
                    json_body=json_body,
                )

                records = data.get("list", [])
                if not records:
                    break

                for record in records:
                    yield {
                        "type": level,
                        "platform": self.platform_name,
                        "advertiser_id": self.advertiser_id,
                        "data": record,
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    }
                    total_records += 1

                # Check for more pages
                page_info = data.get("page_info", {})
                total_page = page_info.get("total_page", 1)
                current_page = page_info.get("page", 1)

                if current_page >= total_page:
                    break

                json_body["page"] = current_page + 1

            except APIError as e:
                raise APIError(
                    message=f"Failed to fetch reports: {e}",
                    platform=self.platform_name,
                ) from e

        self.logger.info(
            "Reports extraction complete",
            level=level,
            total_records=total_records,
        )

    def extract_campaigns(
        self,
        include_deleted: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract campaign data.

        Args:
            include_deleted: Include deleted campaigns

        Yields:
            Campaign records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting campaigns")

        filtering = {}
        if not include_deleted:
            filtering["primary_status"] = "STATUS_ENABLE"

        json_body = {
            "advertiser_id": self.advertiser_id,
            "page": 1,
            "page_size": 1000,
        }

        if filtering:
            json_body["filtering"] = filtering

        total_campaigns = 0

        while True:
            data = self._make_request(
                "/campaign/get/",
                method="GET",
                params={
                    "advertiser_id": self.advertiser_id,
                    "page": json_body["page"],
                    "page_size": json_body["page_size"],
                },
            )

            campaigns = data.get("list", [])
            if not campaigns:
                break

            for campaign in campaigns:
                yield {
                    "type": "campaign",
                    "platform": self.platform_name,
                    "advertiser_id": self.advertiser_id,
                    "data": campaign,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_campaigns += 1

            # Check for more pages
            page_info = data.get("page_info", {})
            total_page = page_info.get("total_page", 1)

            if json_body["page"] >= total_page:
                break

            json_body["page"] += 1

        self.logger.info(
            "Campaigns extraction complete",
            total_campaigns=total_campaigns,
        )

    def extract_adgroups(
        self,
        campaign_ids: list[str] | None = None,
        include_deleted: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad group data.

        Args:
            campaign_ids: Filter by campaign IDs
            include_deleted: Include deleted ad groups

        Yields:
            Ad group records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting ad groups", campaign_ids=campaign_ids)

        params = {
            "advertiser_id": self.advertiser_id,
            "page": 1,
            "page_size": 1000,
        }

        if campaign_ids:
            params["campaign_ids"] = str(campaign_ids)

        total_adgroups = 0

        while True:
            data = self._make_request("/adgroup/get/", params=params)

            adgroups = data.get("list", [])
            if not adgroups:
                break

            for adgroup in adgroups:
                yield {
                    "type": "adgroup",
                    "platform": self.platform_name,
                    "advertiser_id": self.advertiser_id,
                    "data": adgroup,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_adgroups += 1

            # Check for more pages
            page_info = data.get("page_info", {})
            total_page = page_info.get("total_page", 1)

            if params["page"] >= total_page:
                break

            params["page"] += 1

        self.logger.info(
            "Ad groups extraction complete",
            total_adgroups=total_adgroups,
        )

    def extract_ads(
        self,
        adgroup_ids: list[str] | None = None,
        include_deleted: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad data.

        Args:
            adgroup_ids: Filter by ad group IDs
            include_deleted: Include deleted ads

        Yields:
            Ad records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting ads", adgroup_ids=adgroup_ids)

        params = {
            "advertiser_id": self.advertiser_id,
            "page": 1,
            "page_size": 1000,
        }

        if adgroup_ids:
            params["adgroup_ids"] = str(adgroup_ids)

        total_ads = 0

        while True:
            data = self._make_request("/ad/get/", params=params)

            ads = data.get("list", [])
            if not ads:
                break

            for ad in ads:
                yield {
                    "type": "ad",
                    "platform": self.platform_name,
                    "advertiser_id": self.advertiser_id,
                    "data": ad,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_ads += 1

            # Check for more pages
            page_info = data.get("page_info", {})
            total_page = page_info.get("total_page", 1)

            if params["page"] >= total_page:
                break

            params["page"] += 1

        self.logger.info(
            "Ads extraction complete",
            total_ads=total_ads,
        )

    def get_advertiser_ids(self) -> list[str]:
        """Get list of advertiser IDs accessible by the authenticated user.

        Returns:
            List of advertiser IDs
        """
        self._ensure_authenticated()

        data = self._make_request(
            "/oauth2/advertiser/get/",
            params={"app_id": self.app_id, "secret": self.app_secret},
        )

        return [adv["advertiser_id"] for adv in data.get("list", [])]
