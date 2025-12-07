"""Google Ads API extractor.

Google Ads API documentation:
- Authentication: OAuth 2.0 with refresh tokens
- Rate limit: 100 requests per minute per customer ID
- Uses GAQL (Google Ads Query Language) for data retrieval

Uses the google-ads Python SDK for API interactions.
"""

from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class GoogleAdsExtractor(BaseExtractor):
    """Extractor for Google Ads API.

    Provides methods for extracting campaign, ad group, and ad performance
    data using GAQL queries.

    Authentication flow:
    1. Create OAuth credentials in Google Cloud Console
    2. Generate refresh token using OAuth flow
    3. Use refresh token to get access tokens automatically
    """

    platform_name = "google_ads"
    base_url = "https://googleads.googleapis.com"

    # GAQL query templates
    CAMPAIGN_QUERY = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign.start_date,
            campaign.end_date,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.ctr,
            metrics.average_cpc,
            metrics.average_cpm
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """

    ADGROUP_QUERY = """
        SELECT
            ad_group.id,
            ad_group.name,
            ad_group.status,
            ad_group.type,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """

    AD_QUERY = """
        SELECT
            ad_group_ad.ad.id,
            ad_group_ad.ad.name,
            ad_group_ad.ad.type,
            ad_group_ad.status,
            ad_group.id,
            ad_group.name,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """

    KEYWORD_QUERY = """
        SELECT
            ad_group_criterion.criterion_id,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.status,
            ad_group.id,
            campaign.id,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM keyword_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """

    def __init__(self, customer_id: str | None = None):
        """Initialize Google Ads extractor.

        Args:
            customer_id: Google Ads customer ID (format: XXX-XXX-XXXX)
        """
        super().__init__()
        settings = get_settings()

        # Credentials
        self.developer_token = settings.google_ads_developer_token
        self.client_id = settings.google_ads_client_id
        self.client_secret = settings.google_ads_client_secret
        self.refresh_token = settings.google_ads_refresh_token

        # Customer context
        self.customer_id = customer_id or settings.google_ads_customer_id
        if self.customer_id:
            self.customer_id = self.customer_id.replace("-", "")

        # Login customer ID for manager accounts
        self.login_customer_id = settings.google_ads_login_customer_id
        if self.login_customer_id:
            self.login_customer_id = self.login_customer_id.replace("-", "")

        # SDK client (lazy loaded)
        self._google_ads_client: Any = None

    def _init_client(self) -> None:
        """Initialize Google Ads client."""
        try:
            from google.ads.googleads.client import GoogleAdsClient

            # Build configuration dictionary
            config = {
                "developer_token": self.developer_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "use_proto_plus": True,
            }

            if self.login_customer_id:
                config["login_customer_id"] = self.login_customer_id

            self._google_ads_client = GoogleAdsClient.load_from_dict(config)

        except ImportError as e:
            raise AuthenticationError(
                message="google-ads SDK not installed. Run: pip install google-ads",
                platform=self.platform_name,
            ) from e

    def authenticate(self) -> bool:
        """Authenticate with Google Ads API.

        Verifies credentials by making a test query.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.developer_token:
            raise AuthenticationError(
                message="Missing Google Ads developer_token",
                platform=self.platform_name,
            )

        if not self.client_id or not self.client_secret:
            raise AuthenticationError(
                message="Missing Google Ads OAuth credentials (client_id or client_secret)",
                platform=self.platform_name,
            )

        if not self.refresh_token:
            raise AuthenticationError(
                message="Missing Google Ads refresh_token. "
                "Please complete OAuth authorization flow first.",
                platform=self.platform_name,
            )

        if not self.customer_id:
            raise AuthenticationError(
                message="No customer_id specified",
                platform=self.platform_name,
            )

        try:
            self._init_client()

            # Verify by fetching customer info
            ga_service = self._google_ads_client.get_service("GoogleAdsService")
            query = """
                SELECT customer.id, customer.descriptive_name
                FROM customer
                LIMIT 1
            """

            self.rate_limiter.wait()
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query,
            )

            # Consume the response
            for row in response:
                self.logger.info(
                    "Authenticated with Google Ads",
                    customer_id=self.customer_id,
                    customer_name=row.customer.descriptive_name,
                )
                break

            self._authenticated = True
            return True

        except Exception as e:
            error_msg = str(e)
            if "AUTHENTICATION_ERROR" in error_msg or "AUTHORIZATION_ERROR" in error_msg:
                raise AuthenticationError(
                    message=f"Authentication failed: {error_msg}",
                    platform=self.platform_name,
                ) from e
            raise AuthenticationError(
                message=f"Failed to connect: {error_msg}",
                platform=self.platform_name,
            ) from e

    def _execute_query(
        self,
        query: str,
    ) -> Generator[dict[str, Any], None, None]:
        """Execute a GAQL query and yield results.

        Args:
            query: GAQL query string

        Yields:
            Query result rows as dictionaries
        """
        ga_service = self._google_ads_client.get_service("GoogleAdsService")

        self.rate_limiter.wait()

        try:
            response = ga_service.search(
                customer_id=self.customer_id,
                query=query,
            )

            for row in response:
                yield self._row_to_dict(row)

        except Exception as e:
            raise APIError(
                message=f"GAQL query failed: {e}",
                platform=self.platform_name,
                details={"query": query},
            ) from e

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a Google Ads API row to a dictionary.

        Args:
            row: Google Ads API row object

        Returns:
            Dictionary representation of the row
        """
        from google.protobuf.json_format import MessageToDict

        return MessageToDict(row._pb)

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ads data from Google Ads.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - level: "campaign" | "adgroup" | "ad" | "keyword" (default: "campaign")
                - custom_query: Custom GAQL query (overrides level)

        Yields:
            Performance records
        """
        self._ensure_authenticated()

        level = kwargs.get("level", "campaign")
        custom_query = kwargs.get("custom_query")

        if custom_query:
            yield from self.extract_custom(custom_query)
        else:
            yield from self.extract_performance(start_date, end_date, level=level)

    def extract_performance(
        self,
        start_date: datetime,
        end_date: datetime,
        level: str = "campaign",
    ) -> Generator[dict[str, Any], None, None]:
        """Extract performance data at specified level.

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics
            level: Aggregation level (campaign, adgroup, ad, keyword)

        Yields:
            Performance records
        """
        self._ensure_authenticated()

        # Select query template
        query_templates = {
            "campaign": self.CAMPAIGN_QUERY,
            "adgroup": self.ADGROUP_QUERY,
            "ad": self.AD_QUERY,
            "keyword": self.KEYWORD_QUERY,
        }

        if level not in query_templates:
            raise ValueError(f"Invalid level: {level}. Must be one of: {list(query_templates.keys())}")

        query_template = query_templates[level]
        query = query_template.format(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
        )

        self.logger.info(
            "Extracting Google Ads performance",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            level=level,
        )

        total_records = 0
        for row_data in self._execute_query(query):
            yield {
                "type": level,
                "platform": self.platform_name,
                "customer_id": self.customer_id,
                "data": row_data,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }
            total_records += 1

        self.logger.info(
            "Performance extraction complete",
            level=level,
            total_records=total_records,
        )

    def extract_campaigns(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract campaign performance data.

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics

        Yields:
            Campaign performance records
        """
        yield from self.extract_performance(start_date, end_date, level="campaign")

    def extract_adgroups(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad group performance data.

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics

        Yields:
            Ad group performance records
        """
        yield from self.extract_performance(start_date, end_date, level="adgroup")

    def extract_ads(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad performance data.

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics

        Yields:
            Ad performance records
        """
        yield from self.extract_performance(start_date, end_date, level="ad")

    def extract_keywords(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract keyword performance data.

        Args:
            start_date: Start date for metrics
            end_date: End date for metrics

        Yields:
            Keyword performance records
        """
        yield from self.extract_performance(start_date, end_date, level="keyword")

    def extract_custom(
        self,
        query: str,
    ) -> Generator[dict[str, Any], None, None]:
        """Execute a custom GAQL query.

        Args:
            query: Custom GAQL query string

        Yields:
            Query result records
        """
        self._ensure_authenticated()

        self.logger.info("Executing custom GAQL query")

        total_records = 0
        for row_data in self._execute_query(query):
            yield {
                "type": "custom",
                "platform": self.platform_name,
                "customer_id": self.customer_id,
                "data": row_data,
                "extracted_at": datetime.now(timezone.utc).isoformat(),
            }
            total_records += 1

        self.logger.info(
            "Custom query extraction complete",
            total_records=total_records,
        )

    def get_accessible_customers(self) -> list[dict[str, Any]]:
        """Get list of customer accounts accessible by the authenticated user.

        Useful for manager accounts to list child accounts.

        Returns:
            List of accessible customer info dictionaries
        """
        self._ensure_authenticated()

        customer_service = self._google_ads_client.get_service("CustomerService")

        self.rate_limiter.wait()
        response = customer_service.list_accessible_customers()

        customers = []
        for resource_name in response.resource_names:
            customer_id = resource_name.split("/")[-1]
            customers.append({
                "resource_name": resource_name,
                "customer_id": customer_id,
            })

        return customers
