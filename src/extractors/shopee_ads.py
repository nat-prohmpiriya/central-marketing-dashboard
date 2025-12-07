"""Shopee Ads API extractor.

Shopee Ads API documentation:
- Authentication: Reuses Shopee Open Platform OAuth
- Rate limit: 60 requests per minute
- Provides product ads and shop ads metrics
"""

from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.shopee import ShopeeExtractor


class ShopeeAdsExtractor(ShopeeExtractor):
    """Extractor for Shopee Ads API.

    Extends ShopeeExtractor to provide advertising-specific data extraction.
    Uses the same authentication mechanism as the main Shopee API.

    Ads types supported:
    - Product Ads (Search & Discovery Ads)
    - Shop Ads
    """

    platform_name = "shopee_ads"

    # Ads API endpoints
    ADS_CAMPAIGN_LIST_PATH = "/api/v2/ads/get_campaign_list"
    ADS_CAMPAIGN_DETAIL_PATH = "/api/v2/ads/get_campaign_detail"
    ADS_DAILY_REPORT_PATH = "/api/v2/ads/get_daily_report"
    ADS_PRODUCT_ADS_PATH = "/api/v2/ads/get_product_ads_list"
    ADS_SHOP_ADS_PATH = "/api/v2/ads/get_shop_ads_list"

    # Ad types
    AD_TYPES = [
        "product_search",
        "product_discovery",
        "shop_ads",
    ]

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ads data from Shopee.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - data_type: "campaigns" | "reports" | "all" (default: "all")
                - ad_type: Filter by ad type

        Yields:
            Ads data records
        """
        self._ensure_authenticated()

        data_type = kwargs.get("data_type", "all")
        ad_type = kwargs.get("ad_type")

        if data_type in ("campaigns", "all"):
            yield from self.extract_campaigns(ad_type=ad_type)

        if data_type in ("reports", "all"):
            yield from self.extract_daily_reports(start_date, end_date)

    def extract_campaigns(
        self,
        ad_type: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad campaigns.

        Args:
            ad_type: Filter by ad type (optional)

        Yields:
            Campaign records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting Shopee Ads campaigns", ad_type=ad_type)

        # Paginate through campaigns
        page_size = 100
        offset = 0
        total_campaigns = 0

        while True:
            timestamp = self._get_timestamp()
            sign = self._generate_signature(
                self.ADS_CAMPAIGN_LIST_PATH,
                timestamp,
                self._access_token,
                self.shop_id,
            )

            params = {
                "partner_id": self.partner_id,
                "timestamp": timestamp,
                "access_token": self._access_token,
                "shop_id": self.shop_id,
                "sign": sign,
                "page_size": page_size,
                "offset": offset,
            }

            if ad_type:
                params["ad_type"] = ad_type

            self.rate_limiter.wait()
            response = self.client.get(
                f"{self.base_url}{self.ADS_CAMPAIGN_LIST_PATH}",
                params=params,
            )
            data = response.json()

            if data.get("error"):
                self.logger.warning(
                    "Failed to get campaigns",
                    error=data.get("error"),
                    message=data.get("message"),
                )
                break

            campaigns = data.get("response", {}).get("campaign_list", [])
            if not campaigns:
                break

            for campaign in campaigns:
                yield {
                    "type": "campaign",
                    "platform": self.platform_name,
                    "shop_id": self.shop_id,
                    "data": campaign,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_campaigns += 1

            # Check for more pages
            has_more = data.get("response", {}).get("more", False)
            if not has_more:
                break

            offset += page_size

        self.logger.info(
            "Campaigns extraction complete",
            total_campaigns=total_campaigns,
        )

    def extract_daily_reports(
        self,
        start_date: datetime,
        end_date: datetime,
        campaign_id: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract daily advertising reports.

        Args:
            start_date: Start date for reports
            end_date: End date for reports
            campaign_id: Filter by campaign ID (optional)

        Yields:
            Daily report records
        """
        self._ensure_authenticated()

        # Convert to timestamps
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())

        self.logger.info(
            "Extracting Shopee Ads daily reports",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

        timestamp = self._get_timestamp()
        sign = self._generate_signature(
            self.ADS_DAILY_REPORT_PATH,
            timestamp,
            self._access_token,
            self.shop_id,
        )

        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self._access_token,
            "shop_id": self.shop_id,
            "sign": sign,
            "start_time": start_ts,
            "end_time": end_ts,
        }

        if campaign_id:
            params["campaign_id"] = campaign_id

        self.rate_limiter.wait()
        response = self.client.get(
            f"{self.base_url}{self.ADS_DAILY_REPORT_PATH}",
            params=params,
        )
        data = response.json()

        if data.get("error"):
            self.logger.warning(
                "Failed to get daily reports",
                error=data.get("error"),
                message=data.get("message"),
            )
            return

        reports = data.get("response", {}).get("report_list", [])
        total_reports = 0

        for report in reports:
            yield {
                "type": "daily_report",
                "platform": self.platform_name,
                "shop_id": self.shop_id,
                "data": report,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }
            total_reports += 1

        self.logger.info(
            "Daily reports extraction complete",
            total_reports=total_reports,
        )

    def extract_product_ads(
        self,
        campaign_id: int | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract product ads (Search & Discovery).

        Args:
            campaign_id: Filter by campaign ID (optional)

        Yields:
            Product ads records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting Shopee product ads", campaign_id=campaign_id)

        page_size = 100
        offset = 0
        total_ads = 0

        while True:
            timestamp = self._get_timestamp()
            sign = self._generate_signature(
                self.ADS_PRODUCT_ADS_PATH,
                timestamp,
                self._access_token,
                self.shop_id,
            )

            params = {
                "partner_id": self.partner_id,
                "timestamp": timestamp,
                "access_token": self._access_token,
                "shop_id": self.shop_id,
                "sign": sign,
                "page_size": page_size,
                "offset": offset,
            }

            if campaign_id:
                params["campaign_id"] = campaign_id

            self.rate_limiter.wait()
            response = self.client.get(
                f"{self.base_url}{self.ADS_PRODUCT_ADS_PATH}",
                params=params,
            )
            data = response.json()

            if data.get("error"):
                self.logger.warning(
                    "Failed to get product ads",
                    error=data.get("error"),
                )
                break

            ads = data.get("response", {}).get("ads_list", [])
            if not ads:
                break

            for ad in ads:
                yield {
                    "type": "product_ad",
                    "platform": self.platform_name,
                    "shop_id": self.shop_id,
                    "data": ad,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_ads += 1

            has_more = data.get("response", {}).get("more", False)
            if not has_more:
                break

            offset += page_size

        self.logger.info(
            "Product ads extraction complete",
            total_ads=total_ads,
        )

    def extract_shop_ads(self) -> Generator[dict[str, Any], None, None]:
        """Extract shop ads.

        Yields:
            Shop ads records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting Shopee shop ads")

        timestamp = self._get_timestamp()
        sign = self._generate_signature(
            self.ADS_SHOP_ADS_PATH,
            timestamp,
            self._access_token,
            self.shop_id,
        )

        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self._access_token,
            "shop_id": self.shop_id,
            "sign": sign,
        }

        self.rate_limiter.wait()
        response = self.client.get(
            f"{self.base_url}{self.ADS_SHOP_ADS_PATH}",
            params=params,
        )
        data = response.json()

        if data.get("error"):
            self.logger.warning(
                "Failed to get shop ads",
                error=data.get("error"),
            )
            return

        ads = data.get("response", {}).get("shop_ads", [])
        total_ads = 0

        for ad in ads:
            yield {
                "type": "shop_ad",
                "platform": self.platform_name,
                "shop_id": self.shop_id,
                "data": ad,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }
            total_ads += 1

        self.logger.info(
            "Shop ads extraction complete",
            total_ads=total_ads,
        )

    def get_campaign_detail(self, campaign_id: int) -> dict[str, Any] | None:
        """Get detailed information for a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Campaign detail dictionary or None if failed
        """
        self._ensure_authenticated()

        timestamp = self._get_timestamp()
        sign = self._generate_signature(
            self.ADS_CAMPAIGN_DETAIL_PATH,
            timestamp,
            self._access_token,
            self.shop_id,
        )

        params = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self._access_token,
            "shop_id": self.shop_id,
            "sign": sign,
            "campaign_id": campaign_id,
        }

        self.rate_limiter.wait()
        response = self.client.get(
            f"{self.base_url}{self.ADS_CAMPAIGN_DETAIL_PATH}",
            params=params,
        )
        data = response.json()

        if data.get("error"):
            self.logger.warning(
                "Failed to get campaign detail",
                campaign_id=campaign_id,
                error=data.get("error"),
            )
            return None

        return data.get("response")
