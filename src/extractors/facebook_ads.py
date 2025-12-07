"""Facebook Ads (Meta Marketing API) extractor.

Facebook Marketing API documentation:
- Authentication: OAuth 2.0 with long-lived access tokens
- Rate limit: 200 calls per hour per ad account (varies by endpoint)
- Token expiry: 60 days for long-lived tokens

Uses the facebook-business SDK for API interactions.
"""

from datetime import datetime, timezone
from typing import Any, Generator

from src.extractors.base import (
    APIError,
    AuthenticationError,
    BaseExtractor,
)
from src.utils.config import get_settings


class FacebookAdsExtractor(BaseExtractor):
    """Extractor for Facebook Ads (Meta Marketing API).

    Provides methods for extracting campaign, ad set, and ad insights.
    Uses the facebook-business SDK for API interactions.

    Authentication flow:
    1. Create a Facebook App
    2. Generate user access token via OAuth
    3. Exchange for long-lived token (60 days)
    4. Use access token for API calls
    """

    platform_name = "facebook_ads"
    base_url = "https://graph.facebook.com/v21.0"

    # Default insights fields
    DEFAULT_INSIGHTS_FIELDS = [
        "campaign_id",
        "campaign_name",
        "adset_id",
        "adset_name",
        "ad_id",
        "ad_name",
        "impressions",
        "clicks",
        "spend",
        "reach",
        "cpc",
        "cpm",
        "ctr",
        "actions",
        "conversions",
        "cost_per_action_type",
        "video_p25_watched_actions",
        "video_p50_watched_actions",
        "video_p75_watched_actions",
        "video_p100_watched_actions",
    ]

    # Breakdowns available for insights
    AVAILABLE_BREAKDOWNS = [
        "age",
        "gender",
        "country",
        "region",
        "publisher_platform",
        "platform_position",
        "device_platform",
    ]

    def __init__(self, ad_account_id: str | None = None):
        """Initialize Facebook Ads extractor.

        Args:
            ad_account_id: Facebook Ad Account ID (format: act_XXXXX)
        """
        super().__init__()
        settings = get_settings()

        # Credentials
        self.app_id = settings.facebook_app_id
        self.app_secret = settings.facebook_app_secret
        self._access_token = settings.facebook_access_token or None

        # Ad account
        self.ad_account_id = ad_account_id or settings.facebook_ad_account_id
        if self.ad_account_id and not self.ad_account_id.startswith("act_"):
            self.ad_account_id = f"act_{self.ad_account_id}"

        # SDK objects (lazy loaded)
        self._api: Any = None
        self._ad_account: Any = None

    def _init_sdk(self) -> None:
        """Initialize Facebook Business SDK."""
        try:
            from facebook_business.api import FacebookAdsApi
            from facebook_business.adobjects.adaccount import AdAccount

            FacebookAdsApi.init(
                app_id=self.app_id,
                app_secret=self.app_secret,
                access_token=self._access_token,
            )
            self._api = FacebookAdsApi.get_default_api()
            self._ad_account = AdAccount(self.ad_account_id)

        except ImportError as e:
            raise AuthenticationError(
                message="facebook-business SDK not installed. "
                "Run: pip install facebook-business",
                platform=self.platform_name,
            ) from e

    def authenticate(self) -> bool:
        """Authenticate with Facebook Marketing API.

        Verifies the access token by fetching ad account info.

        Returns:
            True if authentication successful

        Raises:
            AuthenticationError: If authentication fails
        """
        if not self.app_id or not self.app_secret:
            raise AuthenticationError(
                message="Missing Facebook credentials (app_id or app_secret)",
                platform=self.platform_name,
            )

        if not self._access_token:
            raise AuthenticationError(
                message="No access_token available. "
                "Please generate a token via Facebook OAuth flow.",
                platform=self.platform_name,
            )

        if not self.ad_account_id:
            raise AuthenticationError(
                message="No ad_account_id specified",
                platform=self.platform_name,
            )

        try:
            self._init_sdk()

            # Verify by fetching account info
            account_info = self._ad_account.api_get(
                fields=["name", "account_status", "currency"]
            )

            self._authenticated = True
            self.logger.info(
                "Authenticated with Facebook Ads",
                ad_account_id=self.ad_account_id,
                account_name=account_info.get("name"),
            )
            return True

        except Exception as e:
            error_msg = str(e)
            if "OAuthException" in error_msg or "access token" in error_msg.lower():
                raise AuthenticationError(
                    message=f"Invalid or expired access token: {error_msg}",
                    platform=self.platform_name,
                ) from e
            raise AuthenticationError(
                message=f"Authentication failed: {error_msg}",
                platform=self.platform_name,
            ) from e

    def get_long_lived_token(self, short_lived_token: str) -> dict[str, Any]:
        """Exchange short-lived token for long-lived token.

        Args:
            short_lived_token: Short-lived user access token

        Returns:
            Dictionary with access_token and expires_in
        """
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token,
        }

        self.rate_limiter.wait()
        response = self.client.get(
            f"{self.base_url}/oauth/access_token",
            params=params,
        )
        data = response.json()

        if "error" in data:
            raise APIError(
                message=f"Token exchange failed: {data['error'].get('message')}",
                platform=self.platform_name,
                details=data["error"],
            )

        return {
            "access_token": data["access_token"],
            "token_type": data.get("token_type", "bearer"),
            "expires_in": data.get("expires_in", 5184000),  # ~60 days
        }

    def extract(
        self,
        start_date: datetime,
        end_date: datetime,
        **kwargs: Any,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ads data from Facebook.

        Args:
            start_date: Start date for data extraction
            end_date: End date for data extraction
            **kwargs: Additional options:
                - level: "campaign" | "adset" | "ad" (default: "ad")
                - fields: List of insight fields to fetch
                - breakdowns: List of breakdowns to apply
                - include_deleted: Include deleted objects (default: False)

        Yields:
            Insight records
        """
        self._ensure_authenticated()

        level = kwargs.get("level", "ad")
        fields = kwargs.get("fields", self.DEFAULT_INSIGHTS_FIELDS)
        breakdowns = kwargs.get("breakdowns", [])
        include_deleted = kwargs.get("include_deleted", False)

        yield from self.extract_insights(
            start_date=start_date,
            end_date=end_date,
            level=level,
            fields=fields,
            breakdowns=breakdowns,
            include_deleted=include_deleted,
        )

    def extract_insights(
        self,
        start_date: datetime,
        end_date: datetime,
        level: str = "ad",
        fields: list[str] | None = None,
        breakdowns: list[str] | None = None,
        include_deleted: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract advertising insights.

        Args:
            start_date: Start date for insights
            end_date: End date for insights
            level: Aggregation level (campaign, adset, ad)
            fields: Fields to retrieve
            breakdowns: Breakdowns to apply
            include_deleted: Include deleted objects

        Yields:
            Insight records
        """
        self._ensure_authenticated()

        fields = fields or self.DEFAULT_INSIGHTS_FIELDS
        breakdowns = breakdowns or []

        # Validate breakdowns
        invalid_breakdowns = set(breakdowns) - set(self.AVAILABLE_BREAKDOWNS)
        if invalid_breakdowns:
            self.logger.warning(
                "Invalid breakdowns ignored",
                invalid=list(invalid_breakdowns),
                valid=self.AVAILABLE_BREAKDOWNS,
            )
            breakdowns = [b for b in breakdowns if b in self.AVAILABLE_BREAKDOWNS]

        self.logger.info(
            "Extracting Facebook Ads insights",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            level=level,
            breakdowns=breakdowns,
        )

        params = {
            "time_range": {
                "since": start_date.strftime("%Y-%m-%d"),
                "until": end_date.strftime("%Y-%m-%d"),
            },
            "level": level,
            "time_increment": 1,  # Daily breakdown
        }

        if breakdowns:
            params["breakdowns"] = breakdowns

        if include_deleted:
            params["filtering"] = [
                {
                    "field": "ad.effective_status",
                    "operator": "IN",
                    "value": [
                        "ACTIVE",
                        "PAUSED",
                        "DELETED",
                        "ARCHIVED",
                        "PENDING_REVIEW",
                        "DISAPPROVED",
                        "PREAPPROVED",
                        "PENDING_BILLING_INFO",
                        "CAMPAIGN_PAUSED",
                        "ADSET_PAUSED",
                    ],
                }
            ]

        try:
            # Use SDK to get insights with pagination
            insights = self._ad_account.get_insights(
                fields=fields,
                params=params,
            )

            total_records = 0
            for insight in insights:
                yield {
                    "type": "insight",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "level": level,
                    "data": dict(insight),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_records += 1

            self.logger.info(
                "Insights extraction complete",
                total_records=total_records,
            )

        except Exception as e:
            raise APIError(
                message=f"Failed to fetch insights: {e}",
                platform=self.platform_name,
            ) from e

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

        fields = [
            "id",
            "name",
            "status",
            "effective_status",
            "objective",
            "buying_type",
            "bid_strategy",
            "daily_budget",
            "lifetime_budget",
            "budget_remaining",
            "spend_cap",
            "start_time",
            "stop_time",
            "created_time",
            "updated_time",
        ]

        params = {}
        if include_deleted:
            params["effective_status"] = [
                "ACTIVE",
                "PAUSED",
                "DELETED",
                "ARCHIVED",
            ]

        try:
            campaigns = self._ad_account.get_campaigns(
                fields=fields,
                params=params,
            )

            total_campaigns = 0
            for campaign in campaigns:
                yield {
                    "type": "campaign",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": dict(campaign),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_campaigns += 1

            self.logger.info(
                "Campaigns extraction complete",
                total_campaigns=total_campaigns,
            )

        except Exception as e:
            raise APIError(
                message=f"Failed to fetch campaigns: {e}",
                platform=self.platform_name,
            ) from e

    def extract_adsets(
        self,
        campaign_id: str | None = None,
        include_deleted: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad set data.

        Args:
            campaign_id: Filter by campaign ID (optional)
            include_deleted: Include deleted ad sets

        Yields:
            Ad set records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting ad sets", campaign_id=campaign_id)

        fields = [
            "id",
            "name",
            "campaign_id",
            "status",
            "effective_status",
            "targeting",
            "optimization_goal",
            "billing_event",
            "bid_amount",
            "bid_strategy",
            "daily_budget",
            "lifetime_budget",
            "budget_remaining",
            "start_time",
            "end_time",
            "created_time",
            "updated_time",
        ]

        params = {}
        if include_deleted:
            params["effective_status"] = [
                "ACTIVE",
                "PAUSED",
                "DELETED",
                "ARCHIVED",
            ]

        try:
            if campaign_id:
                from facebook_business.adobjects.campaign import Campaign
                campaign = Campaign(campaign_id)
                adsets = campaign.get_ad_sets(fields=fields, params=params)
            else:
                adsets = self._ad_account.get_ad_sets(fields=fields, params=params)

            total_adsets = 0
            for adset in adsets:
                yield {
                    "type": "adset",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": dict(adset),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_adsets += 1

            self.logger.info(
                "Ad sets extraction complete",
                total_adsets=total_adsets,
            )

        except Exception as e:
            raise APIError(
                message=f"Failed to fetch ad sets: {e}",
                platform=self.platform_name,
            ) from e

    def extract_ads(
        self,
        adset_id: str | None = None,
        include_deleted: bool = False,
    ) -> Generator[dict[str, Any], None, None]:
        """Extract ad data.

        Args:
            adset_id: Filter by ad set ID (optional)
            include_deleted: Include deleted ads

        Yields:
            Ad records
        """
        self._ensure_authenticated()

        self.logger.info("Extracting ads", adset_id=adset_id)

        fields = [
            "id",
            "name",
            "adset_id",
            "campaign_id",
            "status",
            "effective_status",
            "creative",
            "tracking_specs",
            "conversion_specs",
            "created_time",
            "updated_time",
        ]

        params = {}
        if include_deleted:
            params["effective_status"] = [
                "ACTIVE",
                "PAUSED",
                "DELETED",
                "ARCHIVED",
            ]

        try:
            if adset_id:
                from facebook_business.adobjects.adset import AdSet
                adset = AdSet(adset_id)
                ads = adset.get_ads(fields=fields, params=params)
            else:
                ads = self._ad_account.get_ads(fields=fields, params=params)

            total_ads = 0
            for ad in ads:
                yield {
                    "type": "ad",
                    "platform": self.platform_name,
                    "ad_account_id": self.ad_account_id,
                    "data": dict(ad),
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
                total_ads += 1

            self.logger.info(
                "Ads extraction complete",
                total_ads=total_ads,
            )

        except Exception as e:
            raise APIError(
                message=f"Failed to fetch ads: {e}",
                platform=self.platform_name,
            ) from e
