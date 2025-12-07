"""Google Analytics 4 (GA4) Data API extractor.

GA4 Data API documentation:
- Authentication: Service account or OAuth 2.0
- Rate limit: 60 requests per minute per project
- Uses google-analytics-data SDK

Uses the google-analytics-data SDK for API interactions.
"""

import os
from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class GA4Extractor(BaseExtractor):
    """Extractor for Google Analytics 4 Data API.

    Provides methods for extracting traffic, ecommerce, and page
    performance data from GA4 properties.

    Authentication:
    1. Create a service account in Google Cloud Console
    2. Grant service account access to GA4 property
    3. Download service account JSON key
    4. Set GOOGLE_APPLICATION_CREDENTIALS or credentials_path
    """

    platform_name = "ga4"
    base_url = "https://analyticsdata.googleapis.com"

    # Common dimensions
    COMMON_DIMENSIONS = [
        "date",
        "dateHour",
        "sessionSource",
        "sessionMedium",
        "sessionCampaignName",
        "deviceCategory",
        "country",
        "city",
        "pagePath",
        "pageTitle",
        "landingPage",
    ]

    # Common metrics
    COMMON_METRICS = [
        "sessions",
        "totalUsers",
        "newUsers",
        "activeUsers",
        "screenPageViews",
        "bounceRate",
        "averageSessionDuration",
        "engagedSessions",
        "engagementRate",
        "eventsPerSession",
    ]

    # Ecommerce metrics
    ECOMMERCE_METRICS = [
        "transactions",
        "ecommercePurchases",
        "purchaseRevenue",
        "totalRevenue",
        "averagePurchaseRevenue",
        "itemsViewed",
        "itemsAddedToCart",
        "cartToViewRate",
        "purchaseToViewRate",
    ]

    def __init__(
        self,
        property_id: str | None = None,
        credentials_path: str | None = None,
    ):
        """Initialize GA4 extractor.

        Args:
            property_id: GA4 property ID (format: properties/XXXXX)
            credentials_path: Path to service account JSON file
        """
        super().__init__()
        settings = get_settings()

        # Property ID
        self.property_id = property_id or settings.ga4_property_id
        if self.property_id and not self.property_id.startswith("properties/"):
            self.property_id = f"properties/{self.property_id}"

        # Credentials
        self.credentials_path = credentials_path or settings.ga4_credentials_path

        # SDK client (lazy loaded)
        self._analytics_client: Any = None

    def _init_client(self) -> None:
        """Initialize GA4 Data API client."""
        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient

            # Use credentials file if provided
            if self.credentials_path:
                if not os.path.exists(self.credentials_path):
                    raise AuthenticationError(
                        message=f"Credentials file not found: {self.credentials_path}",
                        platform=self.platform_name,
                    )
                self._analytics_client = BetaAnalyticsDataClient.from_service_account_file(
                    self.credentials_path
                )
            else:
                # Use default credentials (GOOGLE_APPLICATION_CREDENTIALS env var)
                self._analytics_client = BetaAnalyticsDataClient()

        except ImportError as e:
            raise AuthenticationError(
                message="google-analytics-data SDK not installed. "
                "Run: pip install google-analytics-data",
                platform=self.platform_name,
            ) from e

    def authenticate(self) -> bool:
        """Authenticate with GA4 Data API.

        Verifies credentials by making a test request.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.property_id:
            raise AuthenticationError(
                message="No property_id specified",
                platform=self.platform_name,
            )

        try:
            self._init_client()

            # Verify by making a simple request
            from google.analytics.data_v1beta.types import (
                DateRange,
                Dimension,
                Metric,
                RunReportRequest,
            )

            request = RunReportRequest(
                property=self.property_id,
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="sessions")],
                date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
                limit=1,
            )

            self.rate_limiter.wait()
            response = self._analytics_client.run_report(request)

            self._authenticated = True
            self.logger.info(
                "Authenticated with GA4",
                property_id=self.property_id,
            )
            return True

        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "403" in error_msg:
                raise AuthenticationError(
                    message=f"Access denied to property: {error_msg}",
                    platform=self.platform_name,
                ) from e
            raise AuthenticationError(
                message=f"Authentication failed: {error_msg}",
                platform=self.platform_name,
            ) from e

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract analytics data from GA4.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - report_type: "traffic" | "ecommerce" | "pages" | "custom"
                - dimensions: List of dimension names
                - metrics: List of metric names

        Yields:
            Report records
        """
        self._ensure_authenticated()

        report_type = kwargs.get("report_type", "traffic")

        if report_type == "traffic":
            yield from self.extract_traffic_report(start_date, end_date)
        elif report_type == "ecommerce":
            yield from self.extract_ecommerce_report(start_date, end_date)
        elif report_type == "pages":
            yield from self.extract_page_report(start_date, end_date)
        elif report_type == "custom":
            dimensions = kwargs.get("dimensions", ["date"])
            metrics = kwargs.get("metrics", ["sessions"])
            yield from self.extract_custom_report(
                start_date, end_date, dimensions, metrics
            )
        else:
            raise ValueError(
                f"Invalid report_type: {report_type}. "
                "Must be one of: traffic, ecommerce, pages, custom"
            )

    def extract_traffic_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract traffic acquisition report.

        Args:
            start_date: Start date for report
            end_date: End date for report

        Yields:
            Traffic report records
        """
        dimensions = [
            "date",
            "sessionSource",
            "sessionMedium",
            "sessionCampaignName",
        ]
        metrics = [
            "sessions",
            "totalUsers",
            "newUsers",
            "bounceRate",
            "averageSessionDuration",
            "engagementRate",
        ]

        yield from self.extract_custom_report(
            start_date, end_date, dimensions, metrics, report_name="traffic"
        )

    def extract_ecommerce_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ecommerce performance report.

        Args:
            start_date: Start date for report
            end_date: End date for report

        Yields:
            Ecommerce report records
        """
        dimensions = [
            "date",
            "sessionSource",
            "sessionMedium",
        ]
        metrics = [
            "sessions",
            "transactions",
            "purchaseRevenue",
            "averagePurchaseRevenue",
            "itemsViewed",
            "itemsAddedToCart",
        ]

        yield from self.extract_custom_report(
            start_date, end_date, dimensions, metrics, report_name="ecommerce"
        )

    def extract_page_report(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract page performance report.

        Args:
            start_date: Start date for report
            end_date: End date for report

        Yields:
            Page report records
        """
        dimensions = [
            "date",
            "pagePath",
            "pageTitle",
        ]
        metrics = [
            "screenPageViews",
            "sessions",
            "bounceRate",
            "averageSessionDuration",
            "engagementRate",
        ]

        yield from self.extract_custom_report(
            start_date, end_date, dimensions, metrics, report_name="pages"
        )

    def extract_custom_report(
        self,
        start_date: datetime,
        end_date: datetime,
        dimensions: list[str],
        metrics: list[str],
        report_name: str = "custom",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract a custom report with specified dimensions and metrics.

        Args:
            start_date: Start date for report
            end_date: End date for report
            dimensions: List of dimension names
            metrics: List of metric names
            report_name: Name for the report type

        Yields:
            Report records
        """
        self._ensure_authenticated()

        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        self.logger.info(
            "Extracting GA4 report",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            report_name=report_name,
            dimensions=dimensions,
            metrics=metrics,
        )

        request = RunReportRequest(
            property=self.property_id,
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[
                DateRange(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                )
            ],
            limit=100000,
        )

        try:
            self.rate_limiter.wait()
            response = self._analytics_client.run_report(request)

            total_records = 0
            for row in response.rows:
                record_data = {
                    "dimensions": {
                        dimensions[i]: row.dimension_values[i].value
                        for i in range(len(dimensions))
                    },
                    "metrics": {
                        metrics[i]: row.metric_values[i].value
                        for i in range(len(metrics))
                    },
                }

                yield {
                    "type": report_name,
                    "platform": self.platform_name,
                    "property_id": self.property_id,
                    "data": record_data,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_records += 1

            self.logger.info(
                "Report extraction complete",
                report_name=report_name,
                total_records=total_records,
            )

        except Exception as e:
            raise APIError(
                message=f"Failed to run report: {e}",
                platform=self.platform_name,
                details={
                    "report_name": report_name,
                    "dimensions": dimensions,
                    "metrics": metrics,
                },
            ) from e

    def extract_realtime(
        self,
        dimensions: list[str] | None = None,
        metrics: list[str] | None = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract realtime data.

        Args:
            dimensions: List of realtime dimension names
            metrics: List of realtime metric names

        Yields:
            Realtime records
        """
        self._ensure_authenticated()

        from google.analytics.data_v1beta.types import (
            Dimension,
            Metric,
            RunRealtimeReportRequest,
        )

        dimensions = dimensions or ["country", "city"]
        metrics = metrics or ["activeUsers"]

        self.logger.info("Extracting GA4 realtime data")

        request = RunRealtimeReportRequest(
            property=self.property_id,
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
        )

        try:
            self.rate_limiter.wait()
            response = self._analytics_client.run_realtime_report(request)

            total_records = 0
            for row in response.rows:
                record_data = {
                    "dimensions": {
                        dimensions[i]: row.dimension_values[i].value
                        for i in range(len(dimensions))
                    },
                    "metrics": {
                        metrics[i]: row.metric_values[i].value
                        for i in range(len(metrics))
                    },
                }

                yield {
                    "type": "realtime",
                    "platform": self.platform_name,
                    "property_id": self.property_id,
                    "data": record_data,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_records += 1

            self.logger.info(
                "Realtime extraction complete",
                total_records=total_records,
            )

        except Exception as e:
            raise APIError(
                message=f"Failed to run realtime report: {e}",
                platform=self.platform_name,
            ) from e

    def get_metadata(self) -> dict[str, Any]:
        """Get property metadata including available dimensions and metrics.

        Returns:
            Metadata dictionary
        """
        self._ensure_authenticated()

        from google.analytics.data_v1beta.types import GetMetadataRequest

        request = GetMetadataRequest(name=f"{self.property_id}/metadata")

        try:
            self.rate_limiter.wait()
            response = self._analytics_client.get_metadata(request)

            dimensions = [
                {"api_name": d.api_name, "ui_name": d.ui_name}
                for d in response.dimensions
            ]
            metrics = [
                {"api_name": m.api_name, "ui_name": m.ui_name}
                for m in response.metrics
            ]

            return {
                "property_id": self.property_id,
                "dimensions": dimensions,
                "metrics": metrics,
            }

        except Exception as e:
            raise APIError(
                message=f"Failed to get metadata: {e}",
                platform=self.platform_name,
            ) from e
