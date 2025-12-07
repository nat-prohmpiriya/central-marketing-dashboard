"""LINE Ads Platform Management API extractor.

LINE Ads API documentation:
- Authentication: JWS (JSON Web Signature) based authentication
- Rate limit: 60 requests per minute per ad account
- API version: v3
"""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class LINEAdsExtractor(BaseExtractor):
    """Extractor for LINE Ads Platform Management API.

    Provides methods for extracting campaign performance data
    from LINE Ads.

    Authentication:
    1. Get Access Key and Secret Key from LINE Ad Manager
    2. Generate JWS signature for each request
    """

    platform_name = "line_ads"
    base_url = "https://ads.line.me/api/v3"

    # Report levels
    REPORT_LEVELS = [
        "ACCOUNT",
        "CAMPAIGN",
        "AD_GROUP",
        "AD",
    ]

    def __init__(self, ad_account_id: str | None = None):
        """Initialize LINE Ads extractor.

        Args:
            ad_account_id: LINE Ads ad account ID
        """
        super().__init__()
        settings = get_settings()

        # Credentials
        self.access_key = settings.line_ads_access_key
        self.secret_key = settings.line_ads_secret_key

        # Ad account
        self.ad_account_id = ad_account_id or settings.line_ads_ad_account_id

    def _generate_signature(
        self,
        method: str,
        path: str,
        date: str,
        body: str | None = None,
    ) -> str:
        """Generate JWS signature for LINE Ads API.

        Args:
            method: HTTP method
            path: API endpoint path
            date: Request date in RFC 2822 format
            body: Request body (for POST/PUT)

        Returns:
            JWS signature string
        """
        # Build string to sign
        string_to_sign = f"{method}\n{path}\n{date}"
        if body:
            # Add body hash
            body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            string_to_sign += f"\n{body_hash}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        # Base64 encode
        return base64.b64encode(signature).decode("utf-8")

    def _get_date_header(self) -> str:
        """Get current date in RFC 2822 format."""
        from email.utils import formatdate
        return formatdate(timeval=None, localtime=False, usegmt=True)

    def _get_headers(self, method: str, path: str, body: str | None = None) -> dict[str, str]:
        """Get headers with JWS signature for API request."""
        date = self._get_date_header()
        signature = self._generate_signature(method, path, date, body)

        return {
            "Date": date,
            "Authorization": f"Bearer {signature}",
            "X-Line-ChannelId": self.access_key,
            "Content-Type": "application/json",
        }

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a signed request to LINE Ads API.

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

        path = endpoint
        body_str = None
        if json_body:
            body_str = json.dumps(json_body)

        headers = self._get_headers(method, path, body_str)
        url = f"{self.base_url}{endpoint}"

        self.logger.debug(
            "Making LINE Ads API request",
            method=method,
            path=path,
        )

        if method == "GET":
            response = self.client.get(url, params=params, headers=headers)
        else:
            response = self.client.post(url, params=params, json=json_body, headers=headers)

        # Check HTTP status
        if response.status_code >= 400:
            error_data = response.json() if response.text else {}
            raise APIError(
                message=f"LINE Ads API error: {response.status_code}",
                platform=self.platform_name,
                details={
                    "status_code": response.status_code,
                    "error": error_data,
                },
            )

        return response.json()

    def authenticate(self) -> bool:
        """Authenticate with LINE Ads API.

        Verifies credentials by fetching ad account info.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.access_key or not self.secret_key:
            raise AuthenticationError(
                message="Missing LINE Ads credentials (access_key or secret_key)",
                platform=self.platform_name,
            )

        if not self.ad_account_id:
            raise AuthenticationError(
                message="No ad_account_id specified",
                platform=self.platform_name,
            )

        try:
            # Verify by fetching ad account info
            data = self._make_request(
                f"/adaccounts/{self.ad_account_id}",
            )

            self._authenticated = True
            self.logger.info(
                "Authenticated with LINE Ads",
                ad_account_id=self.ad_account_id,
                account_name=data.get("name"),
            )
            return True

        except APIError as e:
            if "401" in str(e) or "403" in str(e):
                raise AuthenticationError(
                    message=f"Invalid credentials: {e}",
                    platform=self.platform_name,
                ) from e
            raise AuthenticationError(
                message=f"Authentication failed: {e}",
                platform=self.platform_name,
            ) from e

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ads data from LINE Ads.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - level: "ACCOUNT" | "CAMPAIGN" | "AD_GROUP" | "AD"
                - format: "json" | "csv"

        Yields:
            Performance records
        """
        self._ensure_authenticated()

        level = kwargs.get("level", "CAMPAIGN")

        yield from self.extract_reports(
            start_date=start_date,
            end_date=end_date,
            level=level,
        )

    def extract_reports(
        self,
        start_date: datetime,
        end_date: datetime,
        level: str = "CAMPAIGN",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract advertising reports.

        Args:
            start_date: Start date for reports
            end_date: End date for reports
            level: Report level (ACCOUNT, CAMPAIGN, AD_GROUP, AD)

        Yields:
            Report records
        """
        self._ensure_authenticated()

        if level not in self.REPORT_LEVELS:
            raise ValueError(
                f"Invalid level: {level}. Must be one of: {self.REPORT_LEVELS}"
            )

        self.logger.info(
            "Extracting LINE Ads reports",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            level=level,
        )

        # Build endpoint based on level
        endpoint = f"/adaccounts/{self.ad_account_id}/reports/online/{level}"

        params = {
            "since": start_date.strftime("%Y-%m-%d"),
            "until": end_date.strftime("%Y-%m-%d"),
        }

        try:
            data = self._make_request(endpoint, params=params)

            records = data if isinstance(data, list) else data.get("data", [])
            total_records = 0

            for record in records:
                yield {
                    "type": level.lower(),
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": record,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_records += 1

            self.logger.info(
                "Reports extraction complete",
                level=level,
                total_records=total_records,
            )

        except APIError as e:
            raise APIError(
                message=f"Failed to fetch reports: {e}",
                platform=self.platform_name,
            ) from e

    def extract_campaigns(
        self,
        status: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract campaign data.

        Args:
            status: Filter by status (optional)

        Yields:
            Campaign records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting campaigns")

        endpoint = f"/adaccounts/{self.ad_account_id}/campaigns"
        params = {}

        if status:
            params["status"] = status

        # Paginate
        page = 1
        page_size = 500
        total_campaigns = 0

        while True:
            params["page"] = page
            params["size"] = page_size

            try:
                data = self._make_request(endpoint, params=params)
            except APIError:
                break

            campaigns = data.get("content", data.get("data", []))
            if not campaigns:
                break

            for campaign in campaigns:
                yield {
                    "type": "campaign",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": campaign,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_campaigns += 1

            # Check for more pages
            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break

            page += 1

        self.logger.info(
            "Campaigns extraction complete",
            total_campaigns=total_campaigns,
        )

    def extract_adgroups(
        self,
        campaign_id: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad group data.

        Args:
            campaign_id: Filter by campaign ID (optional)

        Yields:
            Ad group records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting ad groups", campaign_id=campaign_id)

        if campaign_id:
            endpoint = f"/adaccounts/{self.ad_account_id}/campaigns/{campaign_id}/adgroups"
        else:
            endpoint = f"/adaccounts/{self.ad_account_id}/adgroups"

        page = 1
        page_size = 500
        total_adgroups = 0

        while True:
            params = {"page": page, "size": page_size}

            try:
                data = self._make_request(endpoint, params=params)
            except APIError:
                break

            adgroups = data.get("content", data.get("data", []))
            if not adgroups:
                break

            for adgroup in adgroups:
                yield {
                    "type": "adgroup",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": adgroup,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_adgroups += 1

            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break

            page += 1

        self.logger.info(
            "Ad groups extraction complete",
            total_adgroups=total_adgroups,
        )

    def extract_ads(
        self,
        adgroup_id: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad data.

        Args:
            adgroup_id: Filter by ad group ID (optional)

        Yields:
            Ad records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting ads", adgroup_id=adgroup_id)

        if adgroup_id:
            endpoint = f"/adaccounts/{self.ad_account_id}/adgroups/{adgroup_id}/ads"
        else:
            endpoint = f"/adaccounts/{self.ad_account_id}/ads"

        page = 1
        page_size = 500
        total_ads = 0

        while True:
            params = {"page": page, "size": page_size}

            try:
                data = self._make_request(endpoint, params=params)
            except APIError:
                break

            ads = data.get("content", data.get("data", []))
            if not ads:
                break

            for ad in ads:
                yield {
                    "type": "ad",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": ad,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_ads += 1

            total_pages = data.get("totalPages", 1)
            if page >= total_pages:
                break

            page += 1

        self.logger.info(
            "Ads extraction complete",
            total_ads=total_ads,
        )

    def download_report_csv(
        self,
        start_date: datetime,
        end_date: datetime,
        level: str = "CAMPAIGN",
    ) -> bytes:
        """Download report as CSV.

        Args:
            start_date: Start date for report
            end_date: End date for report
            level: Report level

        Returns:
            CSV content as bytes
        """
        self._ensure_authenticated()

        endpoint = f"/adaccounts/{self.ad_account_id}/reports/online/{level}"
        params = {
            "since": start_date.strftime("%Y-%m-%d"),
            "until": end_date.strftime("%Y-%m-%d"),
        }

        date = self._get_date_header()
        signature = self._generate_signature("GET", endpoint, date)

        headers = {
            "Date": date,
            "Authorization": f"Bearer {signature}",
            "X-Line-ChannelId": self.access_key,
            "Accept": "text/csv;charset=utf-8",
        }

        self.rate_limiter.wait()
        response = self.client.get(
            f"{self.base_url}{endpoint}",
            params=params,
            headers=headers,
        )

        if response.status_code >= 400:
            raise APIError(
                message=f"Failed to download report: {response.status_code}",
                platform=self.platform_name,
            )

        return response.content
