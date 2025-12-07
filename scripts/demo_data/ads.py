"""
Ads Performance Demo Data Generator (DEMO-003)

Generates realistic ads performance data for Facebook, Google, TikTok, and LINE.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .generator import (
    METRIC_RANGES,
    PLATFORMS,
    THAI_PRODUCT_CATEGORIES,
    BaseGenerator,
    GeneratorConfig,
    create_default_config,
)


# Campaign templates
CAMPAIGN_TEMPLATES = {
    "facebook": [
        {"type": "awareness", "objective": "BRAND_AWARENESS", "prefix": "FB-AWR"},
        {"type": "traffic", "objective": "LINK_CLICKS", "prefix": "FB-TRF"},
        {"type": "conversion", "objective": "CONVERSIONS", "prefix": "FB-CVR"},
        {"type": "retargeting", "objective": "CONVERSIONS", "prefix": "FB-RTG"},
        {"type": "lookalike", "objective": "CONVERSIONS", "prefix": "FB-LAL"},
    ],
    "google": [
        {"type": "search", "objective": "SEARCH", "prefix": "GG-SRC"},
        {"type": "display", "objective": "DISPLAY", "prefix": "GG-DSP"},
        {"type": "shopping", "objective": "SHOPPING", "prefix": "GG-SHP"},
        {"type": "performance_max", "objective": "PERFORMANCE_MAX", "prefix": "GG-PMX"},
        {"type": "youtube", "objective": "VIDEO", "prefix": "GG-YT"},
    ],
    "tiktok_ads": [
        {"type": "reach", "objective": "REACH", "prefix": "TT-RCH"},
        {"type": "traffic", "objective": "TRAFFIC", "prefix": "TT-TRF"},
        {"type": "conversion", "objective": "CONVERSIONS", "prefix": "TT-CVR"},
        {"type": "app_install", "objective": "APP_INSTALL", "prefix": "TT-APP"},
    ],
    "line": [
        {"type": "awareness", "objective": "WEBSITE_VISITS", "prefix": "LN-AWR"},
        {"type": "conversion", "objective": "WEBSITE_CONVERSIONS", "prefix": "LN-CVR"},
        {"type": "friend_add", "objective": "GAIN_FRIENDS", "prefix": "LN-FRD"},
    ],
}


class AdsGenerator(BaseGenerator):
    """Generate ads performance data."""

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.campaigns = self._create_campaigns()
        self.ad_groups = self._create_ad_groups()
        self.ads = self._create_ads()

    def _create_campaigns(self) -> list[dict]:
        """Create campaign data."""
        campaigns = []

        for platform in PLATFORMS["ads"]:
            templates = CAMPAIGN_TEMPLATES.get(platform, [])

            for i, template in enumerate(templates):
                for j, category in enumerate(THAI_PRODUCT_CATEGORIES[:3]):  # 3 categories per type
                    campaign_id = f"{template['prefix']}-{i+1:02d}-{j+1:02d}"

                    # Budget varies by campaign type
                    if template["type"] in ["conversion", "shopping", "performance_max"]:
                        daily_budget = np.random.uniform(5000, 30000)
                    elif template["type"] in ["retargeting", "lookalike"]:
                        daily_budget = np.random.uniform(3000, 15000)
                    else:
                        daily_budget = np.random.uniform(1000, 10000)

                    campaigns.append(
                        {
                            "campaign_id": campaign_id,
                            "campaign_name": f"{category} - {template['type'].replace('_', ' ').title()}",
                            "platform": platform,
                            "objective": template["objective"],
                            "campaign_type": template["type"],
                            "status": self._weighted_choice(
                                ["ACTIVE", "PAUSED", "ENDED"],
                                [0.7, 0.2, 0.1],
                            ),
                            "daily_budget": round(daily_budget, 2),
                            "currency": self.config.currency,
                            "start_date": (self.config.start_date - timedelta(days=np.random.randint(0, 30))).isoformat(),
                            "created_at": (self.config.start_date - timedelta(days=np.random.randint(30, 90))).isoformat(),
                        }
                    )

        return campaigns

    def _create_ad_groups(self) -> list[dict]:
        """Create ad group/ad set data."""
        ad_groups = []

        for campaign in self.campaigns:
            # 2-4 ad groups per campaign
            num_ad_groups = np.random.randint(2, 5)

            for i in range(num_ad_groups):
                ad_group_id = f"{campaign['campaign_id']}-AG{i+1:02d}"

                # Targeting options
                age_groups = ["18-24", "25-34", "35-44", "45-54", "55+"]
                genders = ["all", "male", "female"]

                ad_groups.append(
                    {
                        "ad_group_id": ad_group_id,
                        "ad_group_name": f"AdGroup {i+1} - {self._weighted_choice(['Broad', 'Interest', 'Lookalike', 'Retarget'], [0.3, 0.3, 0.2, 0.2])}",
                        "campaign_id": campaign["campaign_id"],
                        "platform": campaign["platform"],
                        "status": campaign["status"],
                        "targeting_age": self._weighted_choice(age_groups, [0.15, 0.35, 0.25, 0.15, 0.1]),
                        "targeting_gender": self._weighted_choice(genders, [0.5, 0.25, 0.25]),
                        "bid_strategy": self._weighted_choice(
                            ["auto", "manual_cpc", "target_cpa", "target_roas"],
                            [0.4, 0.2, 0.2, 0.2],
                        ),
                    }
                )

        return ad_groups

    def _create_ads(self) -> list[dict]:
        """Create ad creative data."""
        ads = []

        for ad_group in self.ad_groups:
            # 2-3 ads per ad group
            num_ads = np.random.randint(2, 4)

            for i in range(num_ads):
                ad_id = f"{ad_group['ad_group_id']}-AD{i+1:02d}"

                ad_formats = {
                    "facebook": ["image", "video", "carousel", "collection"],
                    "google": ["responsive_search", "responsive_display", "shopping", "video"],
                    "tiktok_ads": ["video", "spark_ads", "collection"],
                    "line": ["image", "video", "carousel"],
                }

                platform_formats = ad_formats.get(ad_group["platform"], ["image"])

                ads.append(
                    {
                        "ad_id": ad_id,
                        "ad_name": f"Creative {i+1} - {self._weighted_choice(['Promo', 'Product', 'Brand', 'Sale'], [0.3, 0.3, 0.2, 0.2])}",
                        "ad_group_id": ad_group["ad_group_id"],
                        "campaign_id": ad_group["campaign_id"],
                        "platform": ad_group["platform"],
                        "format": self._weighted_choice(platform_formats, [1/len(platform_formats)] * len(platform_formats)),
                        "status": ad_group["status"],
                    }
                )

        return ads

    def generate(self) -> dict[str, list[dict[str, Any]]]:
        """Generate all ads data."""
        return {
            "campaigns": self.campaigns,
            "ad_groups": self.ad_groups,
            "ads": self.ads,
            "daily_performance": self._generate_daily_performance(),
        }

    def _generate_daily_performance(self) -> list[dict]:
        """Generate daily performance metrics."""
        performance = []
        days = (self.config.end_date - self.config.start_date).days

        for campaign in self.campaigns:
            # Skip ended campaigns randomly
            if campaign["status"] == "ENDED" and np.random.random() > 0.3:
                continue

            # Base metrics vary by campaign type
            base_metrics = self._get_base_metrics(campaign["campaign_type"])

            for day_offset in range(days):
                current_date = self.config.start_date + timedelta(days=day_offset)

                # Skip some days for paused campaigns
                if campaign["status"] == "PAUSED" and np.random.random() > 0.3:
                    continue

                # Apply seasonality and trends
                spend = self._apply_seasonality(base_metrics["spend"], current_date)
                spend = min(spend, campaign["daily_budget"])

                impressions = int(spend / base_metrics["cpm"] * 1000)
                clicks = int(impressions * base_metrics["ctr"] / 100)
                conversions = int(clicks * base_metrics["cvr"] / 100)
                revenue = conversions * base_metrics["avg_order_value"]

                # Add realistic variance
                impressions = max(100, int(impressions * np.random.uniform(0.8, 1.2)))
                clicks = max(1, int(clicks * np.random.uniform(0.8, 1.2)))

                performance.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "campaign_id": campaign["campaign_id"],
                        "campaign_name": campaign["campaign_name"],
                        "platform": campaign["platform"],
                        "objective": campaign["objective"],
                        "impressions": impressions,
                        "clicks": clicks,
                        "spend": round(spend, 2),
                        "conversions": conversions,
                        "revenue": round(revenue, 2),
                        "ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                        "cpc": round(spend / clicks, 2) if clicks > 0 else 0,
                        "cpm": round(spend / impressions * 1000, 2) if impressions > 0 else 0,
                        "cpa": round(spend / conversions, 2) if conversions > 0 else 0,
                        "roas": round(revenue / spend, 2) if spend > 0 else 0,
                        "currency": self.config.currency,
                    }
                )

        return performance

    def _get_base_metrics(self, campaign_type: str) -> dict:
        """Get base metrics by campaign type."""
        metrics = {
            # Awareness campaigns: high reach, low conversion
            "awareness": {"spend": 5000, "cpm": 30, "ctr": 1.0, "cvr": 0.5, "avg_order_value": 800},
            "reach": {"spend": 4000, "cpm": 25, "ctr": 0.8, "cvr": 0.3, "avg_order_value": 700},
            # Traffic campaigns: medium everything
            "traffic": {"spend": 8000, "cpm": 40, "ctr": 2.0, "cvr": 1.0, "avg_order_value": 900},
            # Conversion campaigns: high spend, good conversion
            "conversion": {"spend": 15000, "cpm": 60, "ctr": 2.5, "cvr": 2.5, "avg_order_value": 1200},
            "shopping": {"spend": 12000, "cpm": 50, "ctr": 3.0, "cvr": 3.0, "avg_order_value": 1000},
            "performance_max": {"spend": 20000, "cpm": 55, "ctr": 2.8, "cvr": 2.8, "avg_order_value": 1100},
            # Retargeting: lower spend, high conversion
            "retargeting": {"spend": 6000, "cpm": 80, "ctr": 3.5, "cvr": 4.0, "avg_order_value": 1300},
            "lookalike": {"spend": 10000, "cpm": 50, "ctr": 2.2, "cvr": 2.0, "avg_order_value": 1000},
            # Other
            "search": {"spend": 15000, "cpm": 100, "ctr": 4.0, "cvr": 3.5, "avg_order_value": 1100},
            "display": {"spend": 8000, "cpm": 20, "ctr": 0.5, "cvr": 0.8, "avg_order_value": 800},
            "youtube": {"spend": 10000, "cpm": 80, "ctr": 1.5, "cvr": 1.0, "avg_order_value": 900},
            "video": {"spend": 7000, "cpm": 60, "ctr": 1.2, "cvr": 0.8, "avg_order_value": 850},
            "app_install": {"spend": 5000, "cpm": 40, "ctr": 1.8, "cvr": 5.0, "avg_order_value": 0},
            "friend_add": {"spend": 3000, "cpm": 50, "ctr": 1.5, "cvr": 8.0, "avg_order_value": 0},
        }

        return metrics.get(campaign_type, metrics["traffic"])


def generate_ads_data(days_back: int = 90, seed: int = 42) -> dict:
    """Main function to generate ads demo data."""
    config = create_default_config(days_back=days_back)
    config.seed = seed

    generator = AdsGenerator(config)
    return generator.generate()


if __name__ == "__main__":
    data = generate_ads_data(days_back=90)
    print(f"Generated {len(data['campaigns'])} campaigns")
    print(f"Generated {len(data['ad_groups'])} ad groups")
    print(f"Generated {len(data['ads'])} ads")
    print(f"Generated {len(data['daily_performance'])} daily performance records")
