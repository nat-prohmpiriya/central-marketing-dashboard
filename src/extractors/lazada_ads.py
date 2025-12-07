"""Lazada Ads (Sponsored Solutions) API extractor.

Lazada Ads API documentation:
- Authentication: Reuses Lazada Open Platform OAuth
- Rate limit: 50 requests per minute
- Provides sponsored products metrics
"""

from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.lazada import LazadaExtractor


class LazadaAdsExtractor(LazadaExtractor):
    """Extractor for Lazada Ads (Sponsored Solutions) API.

    Extends LazadaExtractor to provide advertising-specific data extraction.
    Uses the same authentication mechanism as the main Lazada API.

    Ads types supported:
    - Sponsored Products
    - Sponsored Discovery
    """

    platform_name = "lazada_ads"

    # Ads API endpoints
    ADS_CAMPAIGN_LIST_PATH = "/ads/campaigns"
    ADS_CAMPAIGN_DETAIL_PATH = "/ads/campaigns/get"
    ADS_REPORT_PATH = "/ads/reports"
    ADS_SPONSORED_PRODUCTS_PATH = "/ads/sponsored_products"

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ads data from Lazada.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - data_type: "campaigns" | "reports" | "all" (default: "all")

        Yields:
            Ads data records
        """
        self._ensure_authenticated()

        data_type = kwargs.get("data_type", "all")

        if data_type in ("campaigns", "all"):
            yield from self.extract_campaigns()

        if data_type in ("reports", "all"):
            yield from self.extract_reports(start_date, end_date)

    def extract_campaigns(
        self,
        status: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad campaigns.

        Args:
            status: Filter by status (optional)

        Yields:
            Campaign records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting Lazada Ads campaigns", status=status)

        # Paginate through campaigns
        page_size = 100
        offset = 0
        total_campaigns = 0

        while True:
            params = {
                "offset": offset,
                "limit": page_size,
            }

            if status:
                params["status"] = status

            try:
                data = self._make_request(
                    self.ADS_CAMPAIGN_LIST_PATH,
                    params=params,
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to get campaigns",
                    error=str(e),
                )
                break

            campaigns = data.get("campaigns", data.get("data", []))
            if not campaigns:
                break

            for campaign in campaigns:
                yield {
                    "type": "campaign",
                    "platform": self.platform_name,
                    "data": campaign,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_campaigns += 1

            # Check for more pages
            total = data.get("total", 0)
            if offset + page_size >= total:
                break

            offset += page_size

        self.logger.info(
            "Campaigns extraction complete",
            total_campaigns=total_campaigns,
        )

    def extract_reports(
        self,
        start_date: datetime,
        end_date: datetime,
        campaign_id: str | None = None,
        report_type: str = "daily",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract advertising reports.

        Args:
            start_date: Start date for reports
            end_date: End date for reports
            campaign_id: Filter by campaign ID (optional)
            report_type: Report type (daily, summary)

        Yields:
            Report records
        """
        self._ensure_authenticated()

        self.logger.info(
            "Extracting Lazada Ads reports",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            report_type=report_type,
        )

        params = {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "report_type": report_type,
        }

        if campaign_id:
            params["campaign_id"] = campaign_id

        try:
            data = self._make_request(
                self.ADS_REPORT_PATH,
                params=params,
            )
        except Exception as e:
            self.logger.warning(
                "Failed to get reports",
                error=str(e),
            )
            return

        reports = data.get("reports", data.get("data", []))
        total_reports = 0

        for report in reports:
            yield {
                "type": "report",
                "platform": self.platform_name,
                "report_type": report_type,
                "data": report,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }
            total_reports += 1

        self.logger.info(
            "Reports extraction complete",
            total_reports=total_reports,
        )

    def extract_sponsored_products(
        self,
        campaign_id: str | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract sponsored products data.

        Args:
            campaign_id: Filter by campaign ID (optional)

        Yields:
            Sponsored product records
        """
        self._ensure_authenticated()

        self.logger.info(
            "Extracting Lazada sponsored products",
            campaign_id=campaign_id,
        )

        page_size = 100
        offset = 0
        total_products = 0

        while True:
            params = {
                "offset": offset,
                "limit": page_size,
            }

            if campaign_id:
                params["campaign_id"] = campaign_id

            try:
                data = self._make_request(
                    self.ADS_SPONSORED_PRODUCTS_PATH,
                    params=params,
                )
            except Exception as e:
                self.logger.warning(
                    "Failed to get sponsored products",
                    error=str(e),
                )
                break

            products = data.get("products", data.get("data", []))
            if not products:
                break

            for product in products:
                yield {
                    "type": "sponsored_product",
                    "platform": self.platform_name,
                    "data": product,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_products += 1

            # Check for more pages
            total = data.get("total", 0)
            if offset + page_size >= total:
                break

            offset += page_size

        self.logger.info(
            "Sponsored products extraction complete",
            total_products=total_products,
        )

    def get_campaign_detail(self, campaign_id: str) -> dict[str, Any] | None:
        """Get detailed information for a campaign.

        Args:
            campaign_id: Campaign ID

        Returns:
            Campaign detail dictionary or None if failed
        """
        self._ensure_authenticated()

        params = {"campaign_id": campaign_id}

        try:
            data = self._make_request(
                self.ADS_CAMPAIGN_DETAIL_PATH,
                params=params,
            )
            return data.get("campaign", data)
        except Exception as e:
            self.logger.warning(
                "Failed to get campaign detail",
                campaign_id=campaign_id,
                error=str(e),
            )
            return None

    def get_campaign_metrics(
        self,
        campaign_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> dict[str, Any] | None:
        """Get metrics for a specific campaign.

        Args:
            campaign_id: Campaign ID
            start_date: Start date for metrics
            end_date: End date for metrics

        Returns:
            Campaign metrics dictionary or None if failed
        """
        self._ensure_authenticated()

        params = {
            "campaign_id": campaign_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }

        try:
            data = self._make_request(
                self.ADS_REPORT_PATH,
                params=params,
            )

            # Aggregate metrics
            reports = data.get("reports", data.get("data", []))
            if not reports:
                return None

            metrics = {
                "campaign_id": campaign_id,
                "impressions": sum(r.get("impressions", 0) for r in reports),
                "clicks": sum(r.get("clicks", 0) for r in reports),
                "spend": sum(float(r.get("spend", 0)) for r in reports),
                "conversions": sum(r.get("conversions", 0) for r in reports),
            }

            if metrics["impressions"] > 0:
                metrics["ctr"] = metrics["clicks"] / metrics["impressions"]
            if metrics["clicks"] > 0:
                metrics["cpc"] = metrics["spend"] / metrics["clicks"]

            return metrics

        except Exception as e:
            self.logger.warning(
                "Failed to get campaign metrics",
                campaign_id=campaign_id,
                error=str(e),
            )
            return None
