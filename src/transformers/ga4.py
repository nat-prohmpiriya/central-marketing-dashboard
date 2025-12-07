"""GA4 Transformers for sessions, traffic, and pages data.

Transforms raw GA4 Data API responses into normalized formats
for analytics and reporting.
"""

from datetime import datetime, timezone
from typing import Any, Generator

from pydantic import BaseModel, Field

from src.transformers.base import BaseTransformer, MappingError


# =============================================================================
# Schema Models
# =============================================================================


class GA4Session(BaseModel):
    """Unified session model for GA4 data."""

    record_id: str
    property_id: str
    date: datetime
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    channel_grouping: str | None = None

    # Session metrics
    sessions: int = 0
    engaged_sessions: int = 0
    total_users: int = 0
    new_users: int = 0
    active_users: int = 0

    # Engagement metrics
    bounce_rate: float | None = None
    engagement_rate: float | None = None
    avg_session_duration: float | None = None
    events_per_session: float | None = None
    screen_page_views: int = 0

    # Derived metrics
    returning_users: int = 0
    session_duration_total: float = 0.0

    extracted_at: datetime | None = None
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GA4Traffic(BaseModel):
    """Unified traffic model for GA4 data."""

    record_id: str
    property_id: str
    date: datetime
    source: str | None = None
    medium: str | None = None
    campaign: str | None = None
    channel_grouping: str

    # Traffic metrics
    sessions: int = 0
    total_users: int = 0
    new_users: int = 0

    # Engagement metrics
    bounce_rate: float | None = None
    engagement_rate: float | None = None
    avg_session_duration: float | None = None

    # Ecommerce metrics (optional)
    transactions: int = 0
    revenue: float = 0.0
    avg_order_value: float | None = None
    conversion_rate: float | None = None

    extracted_at: datetime | None = None
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GA4Page(BaseModel):
    """Unified page performance model for GA4 data."""

    record_id: str
    property_id: str
    date: datetime
    page_path: str
    page_title: str | None = None

    # Page metrics
    page_views: int = 0
    unique_page_views: int = 0
    sessions: int = 0

    # Engagement metrics
    bounce_rate: float | None = None
    engagement_rate: float | None = None
    avg_time_on_page: float | None = None
    exit_rate: float | None = None
    entrances: int = 0
    exits: int = 0

    extracted_at: datetime | None = None
    transformed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# Channel Grouping Mapping
# =============================================================================

# Default channel grouping rules based on source/medium
# Reference: https://support.google.com/analytics/answer/9756891
CHANNEL_GROUPING_RULES = [
    # Direct - also match "direct" as source with empty/none medium
    (
        lambda s, m: (s == "(direct)" or s == "direct")
        and m in ("(none)", "(not set)", ""),
        "Direct",
    ),
    # Organic Search
    (lambda s, m: m == "organic", "Organic Search"),
    # Paid Search
    (lambda s, m: m in ("cpc", "ppc", "paidsearch"), "Paid Search"),
    # Display
    (lambda s, m: m in ("display", "cpm", "banner"), "Display"),
    # Paid Social - must be checked before Social
    (lambda s, m: m in ("paid_social", "paidsocial", "paid-social"), "Paid Social"),
    # Social
    (
        lambda s, m: m == "social"
        or s
        in (
            "facebook",
            "instagram",
            "twitter",
            "linkedin",
            "tiktok",
            "youtube",
            "pinterest",
        ),
        "Social",
    ),
    # Email
    (lambda s, m: m == "email", "Email"),
    # Affiliates
    (lambda s, m: m == "affiliate", "Affiliates"),
    # Referral
    (lambda s, m: m == "referral", "Referral"),
    # Video
    (lambda s, m: m == "video", "Video"),
    # Audio
    (lambda s, m: m == "audio", "Audio"),
    # SMS
    (lambda s, m: m == "sms", "SMS"),
    # Mobile Push
    (lambda s, m: m in ("push", "mobile", "notification"), "Mobile Push"),
]


def get_channel_grouping(source: str | None, medium: str | None) -> str:
    """Determine channel grouping from source and medium.

    Args:
        source: Session source
        medium: Session medium

    Returns:
        Channel grouping name
    """
    source = (source or "").lower().strip()
    medium = (medium or "").lower().strip()

    for rule, channel in CHANNEL_GROUPING_RULES:
        if rule(source, medium):
            return channel

    # Default to "Other" if no rule matches
    return "Other"


# =============================================================================
# GA4 Sessions Transformer
# =============================================================================


class GA4SessionsTransformer(BaseTransformer):
    """Transform GA4 data to session-level aggregation.

    Aggregates events by session, calculating session duration
    and engagement metrics.
    """

    source_platform = "ga4"
    target_schema = GA4Session

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform GA4 records to session format.

        Args:
            records: Raw GA4 records from extractor

        Yields:
            Transformed session records
        """
        for record in records:
            transformed = self._transform_record(record)
            if transformed is not None:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map GA4 fields to session schema.

        Args:
            record: Raw GA4 record

        Returns:
            Mapped record
        """
        data = record.get("data", {})
        dimensions = data.get("dimensions", {})
        metrics = data.get("metrics", {})

        # Parse date
        date_str = dimensions.get("date", "")
        try:
            if len(date_str) == 8:  # YYYYMMDD format
                date = datetime.strptime(date_str, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            else:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            date = datetime.now(timezone.utc)

        # Extract source/medium
        source = dimensions.get("sessionSource") or dimensions.get("source")
        medium = dimensions.get("sessionMedium") or dimensions.get("medium")
        campaign = dimensions.get("sessionCampaignName") or dimensions.get("campaign")

        # Parse metrics (GA4 returns string values)
        sessions = self._parse_int(metrics.get("sessions", 0))
        engaged_sessions = self._parse_int(metrics.get("engagedSessions", 0))
        total_users = self._parse_int(metrics.get("totalUsers", 0))
        new_users = self._parse_int(metrics.get("newUsers", 0))
        active_users = self._parse_int(metrics.get("activeUsers", 0))
        screen_page_views = self._parse_int(metrics.get("screenPageViews", 0))

        bounce_rate = self._parse_float(metrics.get("bounceRate"))
        engagement_rate = self._parse_float(metrics.get("engagementRate"))
        avg_session_duration = self._parse_float(metrics.get("averageSessionDuration"))
        events_per_session = self._parse_float(metrics.get("eventsPerSession"))

        # Generate record ID
        property_id = record.get("property_id", "unknown")
        record_id = f"ga4_session_{property_id}_{date_str}_{source}_{medium}"

        # Parse extracted_at
        extracted_at = None
        if record.get("extracted_at"):
            try:
                extracted_at = datetime.fromisoformat(
                    record["extracted_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return {
            "record_id": record_id,
            "property_id": property_id,
            "date": date,
            "source": source if source and source != "(not set)" else None,
            "medium": medium if medium and medium != "(not set)" else None,
            "campaign": campaign if campaign and campaign != "(not set)" else None,
            "channel_grouping": get_channel_grouping(source, medium),
            "sessions": sessions,
            "engaged_sessions": engaged_sessions,
            "total_users": total_users,
            "new_users": new_users,
            "active_users": active_users,
            "bounce_rate": bounce_rate,
            "engagement_rate": engagement_rate,
            "avg_session_duration": avg_session_duration,
            "events_per_session": events_per_session,
            "screen_page_views": screen_page_views,
            "returning_users": max(0, total_users - new_users),
            "session_duration_total": (
                avg_session_duration * sessions if avg_session_duration else 0.0
            ),
            "extracted_at": extracted_at,
        }

    @staticmethod
    def _parse_int(value: Any) -> int:
        """Parse integer value from GA4 API response."""
        if value is None:
            return 0
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        """Parse float value from GA4 API response."""
        if value is None:
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None


# =============================================================================
# GA4 Traffic Transformer
# =============================================================================


class GA4TrafficTransformer(BaseTransformer):
    """Transform GA4 data to traffic summary.

    Aggregates by source/medium with channel grouping calculation.
    """

    source_platform = "ga4"
    target_schema = GA4Traffic

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform GA4 records to traffic format.

        Args:
            records: Raw GA4 records from extractor

        Yields:
            Transformed traffic records
        """
        for record in records:
            transformed = self._transform_record(record)
            if transformed is not None:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map GA4 fields to traffic schema.

        Args:
            record: Raw GA4 record

        Returns:
            Mapped record
        """
        data = record.get("data", {})
        dimensions = data.get("dimensions", {})
        metrics = data.get("metrics", {})

        # Parse date
        date_str = dimensions.get("date", "")
        try:
            if len(date_str) == 8:  # YYYYMMDD format
                date = datetime.strptime(date_str, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            else:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            date = datetime.now(timezone.utc)

        # Extract source/medium
        source = dimensions.get("sessionSource") or dimensions.get("source")
        medium = dimensions.get("sessionMedium") or dimensions.get("medium")
        campaign = dimensions.get("sessionCampaignName") or dimensions.get("campaign")

        # Parse metrics
        sessions = self._parse_int(metrics.get("sessions", 0))
        total_users = self._parse_int(metrics.get("totalUsers", 0))
        new_users = self._parse_int(metrics.get("newUsers", 0))
        transactions = self._parse_int(metrics.get("transactions", 0))
        revenue = self._parse_float(metrics.get("purchaseRevenue", 0)) or 0.0

        bounce_rate = self._parse_float(metrics.get("bounceRate"))
        engagement_rate = self._parse_float(metrics.get("engagementRate"))
        avg_session_duration = self._parse_float(metrics.get("averageSessionDuration"))

        # Calculate derived metrics
        avg_order_value = revenue / transactions if transactions > 0 else None
        conversion_rate = (
            (transactions / sessions * 100) if sessions > 0 else None
        )

        # Generate record ID
        property_id = record.get("property_id", "unknown")
        record_id = f"ga4_traffic_{property_id}_{date_str}_{source}_{medium}"

        # Parse extracted_at
        extracted_at = None
        if record.get("extracted_at"):
            try:
                extracted_at = datetime.fromisoformat(
                    record["extracted_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return {
            "record_id": record_id,
            "property_id": property_id,
            "date": date,
            "source": source if source and source != "(not set)" else None,
            "medium": medium if medium and medium != "(not set)" else None,
            "campaign": campaign if campaign and campaign != "(not set)" else None,
            "channel_grouping": get_channel_grouping(source, medium),
            "sessions": sessions,
            "total_users": total_users,
            "new_users": new_users,
            "bounce_rate": bounce_rate,
            "engagement_rate": engagement_rate,
            "avg_session_duration": avg_session_duration,
            "transactions": transactions,
            "revenue": revenue,
            "avg_order_value": avg_order_value,
            "conversion_rate": conversion_rate,
            "extracted_at": extracted_at,
        }

    @staticmethod
    def _parse_int(value: Any) -> int:
        """Parse integer value from GA4 API response."""
        if value is None:
            return 0
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        """Parse float value from GA4 API response."""
        if value is None:
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None


# =============================================================================
# GA4 Pages Transformer
# =============================================================================


class GA4PagesTransformer(BaseTransformer):
    """Transform GA4 data to page performance metrics.

    Aggregates by page path with engagement metrics.
    """

    source_platform = "ga4"
    target_schema = GA4Page

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform GA4 records to page format.

        Args:
            records: Raw GA4 records from extractor

        Yields:
            Transformed page records
        """
        for record in records:
            transformed = self._transform_record(record)
            if transformed is not None:
                yield transformed

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Map GA4 fields to page schema.

        Args:
            record: Raw GA4 record

        Returns:
            Mapped record
        """
        data = record.get("data", {})
        dimensions = data.get("dimensions", {})
        metrics = data.get("metrics", {})

        # Parse date
        date_str = dimensions.get("date", "")
        try:
            if len(date_str) == 8:  # YYYYMMDD format
                date = datetime.strptime(date_str, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            else:
                date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            date = datetime.now(timezone.utc)

        # Extract page dimensions
        page_path = dimensions.get("pagePath", "/")
        page_title = dimensions.get("pageTitle")

        # Parse metrics
        page_views = self._parse_int(metrics.get("screenPageViews", 0))
        sessions = self._parse_int(metrics.get("sessions", 0))
        entrances = self._parse_int(metrics.get("entrances", 0))
        exits = self._parse_int(metrics.get("exits", 0))

        bounce_rate = self._parse_float(metrics.get("bounceRate"))
        engagement_rate = self._parse_float(metrics.get("engagementRate"))
        avg_time_on_page = self._parse_float(metrics.get("averageSessionDuration"))

        # Calculate exit rate
        exit_rate = (exits / page_views * 100) if page_views > 0 else None

        # Estimate unique page views (GA4 doesn't have this directly)
        # Using sessions as a proxy
        unique_page_views = sessions

        # Generate record ID
        property_id = record.get("property_id", "unknown")
        # Clean page path for ID (remove special characters)
        clean_path = page_path.replace("/", "_").replace("?", "_").replace("&", "_")
        record_id = f"ga4_page_{property_id}_{date_str}_{clean_path}"

        # Parse extracted_at
        extracted_at = None
        if record.get("extracted_at"):
            try:
                extracted_at = datetime.fromisoformat(
                    record["extracted_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass

        return {
            "record_id": record_id,
            "property_id": property_id,
            "date": date,
            "page_path": page_path,
            "page_title": page_title if page_title and page_title != "(not set)" else None,
            "page_views": page_views,
            "unique_page_views": unique_page_views,
            "sessions": sessions,
            "bounce_rate": bounce_rate,
            "engagement_rate": engagement_rate,
            "avg_time_on_page": avg_time_on_page,
            "exit_rate": exit_rate,
            "entrances": entrances,
            "exits": exits,
            "extracted_at": extracted_at,
        }

    @staticmethod
    def _parse_int(value: Any) -> int:
        """Parse integer value from GA4 API response."""
        if value is None:
            return 0
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _parse_float(value: Any) -> float | None:
        """Parse float value from GA4 API response."""
        if value is None:
            return None
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return None


# =============================================================================
# Unified GA4 Transformer
# =============================================================================


class UnifiedGA4Transformer(BaseTransformer):
    """Unified transformer that routes to appropriate GA4 transformer.

    Auto-detects report type and applies the correct transformation.
    """

    source_platform = "ga4"
    target_schema = None  # Dynamic based on report type

    def __init__(self):
        super().__init__()
        self._sessions_transformer = GA4SessionsTransformer()
        self._traffic_transformer = GA4TrafficTransformer()
        self._pages_transformer = GA4PagesTransformer()

    def transform(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> Generator[dict[str, Any], None, None]:
        """Transform GA4 records based on their report type.

        Args:
            records: Raw GA4 records from extractor

        Yields:
            Transformed records
        """
        for record in records:
            report_type = self._detect_report_type(record)

            if report_type == "sessions":
                transformer = self._sessions_transformer
            elif report_type == "traffic":
                transformer = self._traffic_transformer
            elif report_type == "pages":
                transformer = self._pages_transformer
            else:
                # Default to sessions
                transformer = self._sessions_transformer

            # Transform using appropriate transformer
            result = transformer._transform_record(record)
            if result is not None:
                yield result
            else:
                # Collect errors from sub-transformer
                self._error_records.extend(transformer.get_error_records())
                transformer.clear_error_records()

    def _map_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Not used directly - delegated to sub-transformers."""
        return record

    def _detect_report_type(self, record: dict[str, Any]) -> str:
        """Detect report type from record structure.

        Args:
            record: Raw GA4 record

        Returns:
            Report type: "sessions", "traffic", "pages", or "unknown"
        """
        # Check explicit type field
        record_type = record.get("type", "")
        if record_type in ("traffic", "sessions"):
            return "traffic"
        if record_type == "pages":
            return "pages"
        if record_type == "ecommerce":
            return "traffic"

        # Detect from dimensions
        data = record.get("data", {})
        dimensions = data.get("dimensions", {})

        if "pagePath" in dimensions or "pageTitle" in dimensions:
            return "pages"
        if "sessionSource" in dimensions or "sessionMedium" in dimensions:
            return "traffic"

        return "sessions"
