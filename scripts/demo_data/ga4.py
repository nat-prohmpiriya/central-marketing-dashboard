"""
GA4 Analytics Demo Data Generator (DEMO-004)

Generates realistic GA4 analytics data including sessions, traffic sources, and page performance.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .generator import (
    METRIC_RANGES,
    BaseGenerator,
    GeneratorConfig,
    create_default_config,
)


# Traffic sources configuration
TRAFFIC_SOURCES = [
    {"source": "google", "medium": "organic", "weight": 0.25},
    {"source": "google", "medium": "cpc", "weight": 0.15},
    {"source": "facebook", "medium": "cpc", "weight": 0.12},
    {"source": "facebook", "medium": "social", "weight": 0.08},
    {"source": "(direct)", "medium": "(none)", "weight": 0.15},
    {"source": "tiktok", "medium": "cpc", "weight": 0.08},
    {"source": "line", "medium": "cpc", "weight": 0.05},
    {"source": "shopee", "medium": "referral", "weight": 0.04},
    {"source": "lazada", "medium": "referral", "weight": 0.03},
    {"source": "instagram", "medium": "social", "weight": 0.03},
    {"source": "email", "medium": "email", "weight": 0.02},
]

# Page paths
PAGE_PATHS = [
    {"path": "/", "name": "Home", "weight": 0.20},
    {"path": "/products", "name": "Products", "weight": 0.15},
    {"path": "/product/detail", "name": "Product Detail", "weight": 0.18},
    {"path": "/cart", "name": "Shopping Cart", "weight": 0.10},
    {"path": "/checkout", "name": "Checkout", "weight": 0.08},
    {"path": "/checkout/success", "name": "Order Success", "weight": 0.05},
    {"path": "/category", "name": "Category", "weight": 0.10},
    {"path": "/search", "name": "Search Results", "weight": 0.06},
    {"path": "/account", "name": "My Account", "weight": 0.04},
    {"path": "/about", "name": "About Us", "weight": 0.02},
    {"path": "/contact", "name": "Contact", "weight": 0.02},
]

# Device categories
DEVICES = [
    {"category": "mobile", "weight": 0.65},
    {"category": "desktop", "weight": 0.30},
    {"category": "tablet", "weight": 0.05},
]

# Countries/Regions
COUNTRIES = [
    {"country": "Thailand", "weight": 0.92},
    {"country": "Malaysia", "weight": 0.03},
    {"country": "Singapore", "weight": 0.02},
    {"country": "Vietnam", "weight": 0.02},
    {"country": "Other", "weight": 0.01},
]


class GA4Generator(BaseGenerator):
    """Generate GA4 analytics data."""

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.property_id = "GA4-DEMO-001"

    def generate(self) -> dict[str, list[dict[str, Any]]]:
        """Generate all GA4 data."""
        return {
            "sessions": self._generate_sessions(),
            "traffic_summary": self._generate_traffic_summary(),
            "page_performance": self._generate_page_performance(),
            "device_summary": self._generate_device_summary(),
            "daily_overview": self._generate_daily_overview(),
        }

    def _generate_sessions(self) -> list[dict]:
        """Generate session-level data."""
        sessions = []
        days = (self.config.end_date - self.config.start_date).days

        for day_offset in range(days):
            current_date = self.config.start_date + timedelta(days=day_offset)

            # Base sessions with seasonality
            base_sessions = METRIC_RANGES["sessions_per_day"]["mean"] * self.config.scale
            daily_sessions = int(self._apply_seasonality(base_sessions, current_date))

            for _ in range(min(daily_sessions, 500)):  # Limit for demo
                session_id = f"sess_{uuid.uuid4().hex[:16]}"
                user_id = f"user_{uuid.uuid4().hex[:12]}"

                # Random session time
                session_start = self._random_date(
                    current_date,
                    current_date + timedelta(hours=23, minutes=59),
                )

                # Traffic source
                source_data = self._weighted_choice(
                    TRAFFIC_SOURCES,
                    [s["weight"] for s in TRAFFIC_SOURCES],
                )

                # Device
                device_data = self._weighted_choice(
                    DEVICES,
                    [d["weight"] for d in DEVICES],
                )

                # Country
                country_data = self._weighted_choice(
                    COUNTRIES,
                    [c["weight"] for c in COUNTRIES],
                )

                # Session metrics
                pageviews = max(1, int(np.random.exponential(3)))
                session_duration = max(10, int(np.random.exponential(120)))

                # Bounce (single pageview, short duration)
                is_bounce = pageviews == 1 and session_duration < 30

                # Conversion (based on pageviews and source)
                conversion_rate = 0.02
                if source_data["medium"] == "cpc":
                    conversion_rate = 0.035
                elif source_data["medium"] == "organic":
                    conversion_rate = 0.025

                is_converted = np.random.random() < conversion_rate and pageviews >= 3

                sessions.append(
                    {
                        "session_id": session_id,
                        "user_id": user_id,
                        "date": current_date.strftime("%Y-%m-%d"),
                        "session_start": session_start.isoformat(),
                        "source": source_data["source"],
                        "medium": source_data["medium"],
                        "campaign": f"campaign_{np.random.randint(1, 20):02d}" if source_data["medium"] == "cpc" else "(not set)",
                        "device_category": device_data["category"],
                        "country": country_data["country"],
                        "pageviews": pageviews,
                        "session_duration": session_duration,
                        "is_bounce": is_bounce,
                        "is_new_user": np.random.random() < 0.6,
                        "is_converted": is_converted,
                        "transaction_revenue": round(np.random.uniform(500, 3000), 2) if is_converted else 0,
                    }
                )

        return sessions

    def _generate_traffic_summary(self) -> list[dict]:
        """Generate daily traffic summary by source/medium."""
        summary = []
        days = (self.config.end_date - self.config.start_date).days

        for day_offset in range(days):
            current_date = self.config.start_date + timedelta(days=day_offset)
            base_sessions = METRIC_RANGES["sessions_per_day"]["mean"] * self.config.scale
            daily_total = int(self._apply_seasonality(base_sessions, current_date))

            for source_data in TRAFFIC_SOURCES:
                sessions = int(daily_total * source_data["weight"] * np.random.uniform(0.8, 1.2))

                if sessions < 10:
                    continue

                users = int(sessions * np.random.uniform(0.7, 0.95))
                new_users = int(users * np.random.uniform(0.5, 0.7))
                pageviews = int(sessions * np.random.uniform(2, 4))

                # Metrics vary by source
                bounce_rate = METRIC_RANGES["bounce_rate"]["mean"]
                if source_data["medium"] == "cpc":
                    bounce_rate *= 0.85
                elif source_data["medium"] == "(none)":
                    bounce_rate *= 0.9

                avg_duration = METRIC_RANGES["avg_session_duration"]["mean"]
                if source_data["medium"] == "organic":
                    avg_duration *= 1.2
                elif source_data["medium"] == "social":
                    avg_duration *= 0.8

                conversions = int(sessions * np.random.uniform(0.015, 0.04))
                revenue = conversions * np.random.uniform(800, 1500)

                summary.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "source": source_data["source"],
                        "medium": source_data["medium"],
                        "sessions": sessions,
                        "users": users,
                        "new_users": new_users,
                        "pageviews": pageviews,
                        "bounce_rate": round(bounce_rate * np.random.uniform(0.9, 1.1), 2),
                        "avg_session_duration": round(avg_duration * np.random.uniform(0.8, 1.2), 2),
                        "conversions": conversions,
                        "revenue": round(revenue, 2),
                    }
                )

        return summary

    def _generate_page_performance(self) -> list[dict]:
        """Generate daily page performance data."""
        performance = []
        days = (self.config.end_date - self.config.start_date).days

        for day_offset in range(days):
            current_date = self.config.start_date + timedelta(days=day_offset)
            base_pageviews = METRIC_RANGES["sessions_per_day"]["mean"] * 3 * self.config.scale
            daily_total = int(self._apply_seasonality(base_pageviews, current_date))

            for page_data in PAGE_PATHS:
                pageviews = int(daily_total * page_data["weight"] * np.random.uniform(0.8, 1.2))

                if pageviews < 5:
                    continue

                unique_pageviews = int(pageviews * np.random.uniform(0.6, 0.85))
                entrances = int(pageviews * np.random.uniform(0.1, 0.4))
                exits = int(pageviews * np.random.uniform(0.15, 0.5))

                # Time on page varies by page type
                avg_time = 60
                if page_data["path"] in ["/product/detail", "/checkout"]:
                    avg_time = 120
                elif page_data["path"] in ["/", "/search"]:
                    avg_time = 40

                performance.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "page_path": page_data["path"],
                        "page_title": page_data["name"],
                        "pageviews": pageviews,
                        "unique_pageviews": unique_pageviews,
                        "entrances": entrances,
                        "exits": exits,
                        "exit_rate": round(exits / pageviews * 100, 2),
                        "avg_time_on_page": round(avg_time * np.random.uniform(0.7, 1.3), 2),
                    }
                )

        return performance

    def _generate_device_summary(self) -> list[dict]:
        """Generate daily device category summary."""
        summary = []
        days = (self.config.end_date - self.config.start_date).days

        for day_offset in range(days):
            current_date = self.config.start_date + timedelta(days=day_offset)
            base_sessions = METRIC_RANGES["sessions_per_day"]["mean"] * self.config.scale
            daily_total = int(self._apply_seasonality(base_sessions, current_date))

            for device_data in DEVICES:
                sessions = int(daily_total * device_data["weight"] * np.random.uniform(0.9, 1.1))
                users = int(sessions * np.random.uniform(0.7, 0.9))

                # Desktop has better metrics
                if device_data["category"] == "desktop":
                    bounce_rate = 45
                    conversion_rate = 0.035
                elif device_data["category"] == "tablet":
                    bounce_rate = 50
                    conversion_rate = 0.025
                else:  # mobile
                    bounce_rate = 55
                    conversion_rate = 0.02

                conversions = int(sessions * conversion_rate * np.random.uniform(0.8, 1.2))
                revenue = conversions * np.random.uniform(800, 1200)

                summary.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "device_category": device_data["category"],
                        "sessions": sessions,
                        "users": users,
                        "bounce_rate": round(bounce_rate * np.random.uniform(0.9, 1.1), 2),
                        "pages_per_session": round(np.random.uniform(2.5, 4.0), 2),
                        "avg_session_duration": round(np.random.uniform(80, 150), 2),
                        "conversions": conversions,
                        "revenue": round(revenue, 2),
                    }
                )

        return summary

    def _generate_daily_overview(self) -> list[dict]:
        """Generate daily overview metrics."""
        overview = []
        days = (self.config.end_date - self.config.start_date).days

        for day_offset in range(days):
            current_date = self.config.start_date + timedelta(days=day_offset)
            base_sessions = METRIC_RANGES["sessions_per_day"]["mean"] * self.config.scale
            sessions = int(self._apply_seasonality(base_sessions, current_date))

            users = int(sessions * np.random.uniform(0.75, 0.9))
            new_users = int(users * np.random.uniform(0.55, 0.65))
            pageviews = int(sessions * np.random.uniform(2.5, 3.5))

            conversions = int(sessions * np.random.uniform(0.02, 0.035))
            revenue = conversions * np.random.uniform(900, 1300)

            overview.append(
                {
                    "date": current_date.strftime("%Y-%m-%d"),
                    "sessions": sessions,
                    "users": users,
                    "new_users": new_users,
                    "pageviews": pageviews,
                    "pages_per_session": round(pageviews / sessions, 2),
                    "avg_session_duration": round(np.random.uniform(90, 140), 2),
                    "bounce_rate": round(np.random.uniform(45, 55), 2),
                    "conversions": conversions,
                    "conversion_rate": round(conversions / sessions * 100, 2),
                    "revenue": round(revenue, 2),
                }
            )

        return overview


def generate_ga4_data(days_back: int = 90, seed: int = 42) -> dict:
    """Main function to generate GA4 demo data."""
    config = create_default_config(days_back=days_back)
    config.seed = seed

    generator = GA4Generator(config)
    return generator.generate()


if __name__ == "__main__":
    data = generate_ga4_data(days_back=90)
    print(f"Generated {len(data['sessions'])} sessions")
    print(f"Generated {len(data['traffic_summary'])} traffic summary records")
    print(f"Generated {len(data['page_performance'])} page performance records")
    print(f"Generated {len(data['device_summary'])} device summary records")
    print(f"Generated {len(data['daily_overview'])} daily overview records")
