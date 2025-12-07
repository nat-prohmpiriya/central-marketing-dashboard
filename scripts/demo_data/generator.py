"""
Demo Data Generator Framework (DEMO-001)

Base framework for generating realistic demo data for the Central Marketing Dashboard.
"""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np


@dataclass
class GeneratorConfig:
    """Configuration for data generation."""

    # Date range
    start_date: datetime
    end_date: datetime

    # Random seed for reproducibility
    seed: int = 42

    # Scale factor (1.0 = normal, 2.0 = double the data)
    scale: float = 1.0

    # Business settings
    currency: str = "THB"
    timezone: str = "Asia/Bangkok"


class BaseGenerator(ABC):
    """Base class for all data generators."""

    def __init__(self, config: GeneratorConfig):
        self.config = config
        self._setup_random(config.seed)

    def _setup_random(self, seed: int) -> None:
        """Setup random seed for reproducibility."""
        random.seed(seed)
        np.random.seed(seed)

    @abstractmethod
    def generate(self) -> list[dict[str, Any]]:
        """Generate data records."""
        pass

    def _random_date(self, start: datetime, end: datetime) -> datetime:
        """Generate random datetime between start and end."""
        delta = end - start
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start + timedelta(seconds=random_seconds)

    def _weighted_choice(self, choices: list, weights: list) -> Any:
        """Make a weighted random choice."""
        return random.choices(choices, weights=weights, k=1)[0]

    def _apply_seasonality(self, base_value: float, date: datetime) -> float:
        """Apply realistic seasonality patterns."""
        # Day of week effect (weekends higher)
        dow_factor = 1.0
        if date.weekday() >= 5:  # Saturday, Sunday
            dow_factor = 1.3

        # Month effect (end of month higher)
        day_of_month = date.day
        if day_of_month >= 25:
            month_factor = 1.2
        elif day_of_month <= 5:
            month_factor = 1.1
        else:
            month_factor = 1.0

        # Holiday effect (simplified)
        month = date.month
        if month == 12:  # December
            holiday_factor = 1.5
        elif month == 11:  # November (11.11)
            holiday_factor = 1.4
        elif month == 2:  # February (Valentine)
            holiday_factor = 1.2
        else:
            holiday_factor = 1.0

        # Add some random noise
        noise = np.random.normal(1.0, 0.1)

        return base_value * dow_factor * month_factor * holiday_factor * noise

    def _generate_trend(
        self, days: int, start_value: float, growth_rate: float = 0.001
    ) -> list[float]:
        """Generate values with upward/downward trend."""
        values = []
        current = start_value
        for _ in range(days):
            # Add daily growth/decline
            current *= 1 + growth_rate + np.random.normal(0, 0.02)
            values.append(max(0, current))
        return values


# Thai product/shop names for realistic data
THAI_PRODUCT_CATEGORIES = [
    "เสื้อผ้าแฟชั่น",
    "กระเป๋า",
    "รองเท้า",
    "เครื่องสำอาง",
    "อุปกรณ์อิเล็กทรอนิกส์",
    "ของใช้ในบ้าน",
    "อาหารและเครื่องดื่ม",
    "สุขภาพและความงาม",
    "แม่และเด็ก",
    "กีฬาและกิจกรรมกลางแจ้ง",
]

THAI_SHOP_NAMES = [
    "ร้านสวยปัง",
    "แฟชั่นฮิต",
    "ของดีมีคุณภาพ",
    "ช้อปสบาย",
    "สินค้าพรีเมียม",
    "ดีลสุดคุ้ม",
    "ของแท้ 100%",
    "ราคาถูกใจ",
]

PLATFORMS = {
    "ecommerce": ["shopee", "lazada", "tiktok_shop"],
    "ads": ["facebook", "google", "tiktok_ads", "line"],
}

# Realistic metric ranges
METRIC_RANGES = {
    # E-commerce
    "order_value": {"min": 100, "max": 5000, "mean": 800},
    "items_per_order": {"min": 1, "max": 5, "mean": 2},
    "orders_per_day": {"min": 10, "max": 200, "mean": 50},
    # Ads
    "ctr": {"min": 0.5, "max": 5.0, "mean": 2.0},  # %
    "cpc": {"min": 1, "max": 20, "mean": 5},  # THB
    "conversion_rate": {"min": 0.5, "max": 5.0, "mean": 2.0},  # %
    "roas": {"min": 0.5, "max": 8.0, "mean": 3.0},
    "daily_spend": {"min": 500, "max": 50000, "mean": 10000},  # THB
    # GA4
    "sessions_per_day": {"min": 100, "max": 5000, "mean": 1000},
    "bounce_rate": {"min": 30, "max": 70, "mean": 50},  # %
    "avg_session_duration": {"min": 30, "max": 300, "mean": 120},  # seconds
}


def create_default_config(days_back: int = 90) -> GeneratorConfig:
    """Create default configuration for demo data."""
    end_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days_back)

    return GeneratorConfig(
        start_date=start_date,
        end_date=end_date,
        seed=42,
        scale=1.0,
    )


if __name__ == "__main__":
    # Test the framework
    config = create_default_config(days_back=90)
    print(f"Demo Data Generator Framework")
    print(f"Date range: {config.start_date.date()} to {config.end_date.date()}")
    print(f"Seed: {config.seed}")
    print(f"Platforms: {PLATFORMS}")
    print(f"Categories: {len(THAI_PRODUCT_CATEGORIES)}")
