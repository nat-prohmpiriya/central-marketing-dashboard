"""
BigQuery Demo Data Loader (DEMO-006)

Load generated demo data into BigQuery tables.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from google.cloud import bigquery

from scripts.demo_data.ads import generate_ads_data
from scripts.demo_data.ecommerce import generate_ecommerce_data
from scripts.demo_data.ga4 import generate_ga4_data


class BigQueryLoader:
    """Load demo data into BigQuery."""

    def __init__(self, project_id: str, location: str = "asia-southeast1"):
        self.client = bigquery.Client(project=project_id, location=location)
        self.project_id = project_id

    def load_data(
        self,
        data: list[dict],
        dataset: str,
        table: str,
        write_disposition: str = "WRITE_TRUNCATE",
    ) -> int:
        """Load data into BigQuery table."""
        table_ref = f"{self.project_id}.{dataset}.{table}"

        # Add metadata
        loaded_at = datetime.now().isoformat()
        for record in data:
            record["_loaded_at"] = loaded_at
            record["_source"] = "demo_data"
            # Convert datetime objects to strings
            for key, value in record.items():
                if isinstance(value, datetime):
                    record[key] = value.isoformat()

        job_config = bigquery.LoadJobConfig(
            write_disposition=write_disposition,
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            autodetect=True,
        )

        # Convert to newline-delimited JSON
        json_data = "\n".join(json.dumps(record, default=str) for record in data)

        job = self.client.load_table_from_json(
            data,
            table_ref,
            job_config=job_config,
        )
        job.result()  # Wait for completion

        print(f"  Loaded {len(data)} rows to {table_ref}")
        return len(data)

    def load_ecommerce_data(self, days_back: int = 90) -> dict:
        """Load e-commerce demo data."""
        print("\nGenerating e-commerce data...")
        data = generate_ecommerce_data(days_back=days_back)

        results = {}

        # Load shops
        print("Loading shops...")
        results["shops"] = self.load_data(data["shops"], "staging", "stg_shops")

        # Load products
        print("Loading products...")
        results["products"] = self.load_data(data["products"], "staging", "stg_products")

        # Load orders - add item_count for mart compatibility
        print("Loading orders...")
        orders_data = []
        for order in data["orders"]:
            order_copy = order.copy()
            # Count items for this order
            item_count = sum(1 for item in data["order_items"] if item["order_id"] == order["order_id"])
            order_copy["item_count"] = item_count
            order_copy["platform_order_id"] = order["order_id"]
            orders_data.append(order_copy)
        results["orders"] = self.load_data(orders_data, "staging", "stg_orders")

        # Load order items - add platform and order_date for mart compatibility
        print("Loading order items...")
        order_items_data = []
        # Create order->platform and order->date mapping
        order_platform_map = {o["order_id"]: o["platform"] for o in data["orders"]}
        order_date_map = {o["order_id"]: o["order_date"] for o in data["orders"]}
        for item in data["order_items"]:
            item_copy = item.copy()
            item_copy["platform"] = order_platform_map.get(item["order_id"], "unknown")
            item_copy["order_date"] = order_date_map.get(item["order_id"])
            item_copy["item_id"] = item["order_item_id"]
            item_copy["name"] = item["product_name"]
            item_copy["total_price"] = item["subtotal"]
            order_items_data.append(item_copy)
        results["order_items"] = self.load_data(order_items_data, "staging", "stg_order_items")

        # Create SKU mappings from products (for mart compatibility)
        print("Loading SKU mappings...")
        sku_mappings = []
        seen_skus = set()
        for product in data["products"]:
            if product["master_sku"] not in seen_skus:
                sku_mappings.append({
                    "master_sku": product["master_sku"],
                    "platform": product["platform"],
                    "platform_sku": product["sku"],
                    "product_name": product["name"],
                    "category": product["category"],
                })
                seen_skus.add(product["master_sku"])
        results["sku_mappings"] = self.load_data(sku_mappings, "staging", "stg_sku_mappings")

        return results

    def load_ads_data(self, days_back: int = 90) -> dict:
        """Load ads demo data."""
        print("\nGenerating ads data...")
        data = generate_ads_data(days_back=days_back)

        results = {}

        # Load campaigns
        print("Loading campaigns...")
        results["campaigns"] = self.load_data(data["campaigns"], "staging", "stg_ads_campaigns")

        # Load ad groups
        print("Loading ad groups...")
        results["ad_groups"] = self.load_data(data["ad_groups"], "staging", "stg_ads_ad_groups")

        # Load ads
        print("Loading ads...")
        results["ads"] = self.load_data(data["ads"], "staging", "stg_ads_creatives")

        # Load daily performance - also as stg_ads for mart compatibility
        print("Loading ads daily performance...")
        results["daily_performance"] = self.load_data(
            data["daily_performance"], "staging", "stg_ads_daily_performance"
        )

        # Transform for stg_ads (mart compatibility)
        print("Loading stg_ads (mart compatibility)...")
        stg_ads_data = []
        for i, record in enumerate(data["daily_performance"]):
            stg_ads_data.append({
                "record_id": f"ADS-{i+1:06d}",
                "date": record["date"],
                "platform": record["platform"],
                "account_id": f"ACC-{record['platform'][:3].upper()}",
                "campaign_id": record["campaign_id"],
                "campaign_name": record["campaign_name"],
                "campaign_type": record.get("objective", "conversion"),
                "objective": record.get("objective", "CONVERSIONS"),
                "adgroup_id": f"{record['campaign_id']}-AG01",
                "adgroup_name": "Default AdGroup",
                "ad_id": f"{record['campaign_id']}-AD01",
                "ad_name": "Default Ad",
                "spend": record["spend"],
                "impressions": record["impressions"],
                "clicks": record["clicks"],
                "reach": int(record["impressions"] * 0.7),
                "conversions": record["conversions"],
                "conversion_value": record["revenue"],
                "ctr": record["ctr"],
                "cpc": record["cpc"],
                "cpm": record["cpm"],
                "video_views": int(record["impressions"] * 0.3) if record["platform"] in ["tiktok_ads", "facebook"] else 0,
                "likes": int(record["clicks"] * 0.1),
                "comments": int(record["clicks"] * 0.02),
                "shares": int(record["clicks"] * 0.01),
                "status": "active",
                "level": "campaign",
            })
        results["stg_ads"] = self.load_data(stg_ads_data, "staging", "stg_ads")

        return results

    def load_ga4_data(self, days_back: int = 90) -> dict:
        """Load GA4 demo data."""
        print("\nGenerating GA4 data...")
        data = generate_ga4_data(days_back=days_back)

        results = {}

        # Load traffic summary with required columns
        print("Loading GA4 traffic summary...")
        traffic_data = []
        for i, record in enumerate(data["traffic_summary"]):
            traffic_data.append({
                "record_id": f"GA4-TRF-{i+1:06d}",
                "property_id": "GA4-DEMO-001",
                "date": record["date"],
                "source": record["source"],
                "medium": record["medium"],
                "campaign": f"campaign_{i % 20 + 1:02d}" if record["medium"] == "cpc" else "(not set)",
                "channel_grouping": self._get_channel_grouping(record["source"], record["medium"]),
                "sessions": record["sessions"],
                "total_users": record["users"],
                "new_users": record["new_users"],
                "bounce_rate": record["bounce_rate"],
                "engagement_rate": 100 - record["bounce_rate"],
                "avg_session_duration": record["avg_session_duration"],
                "transactions": record["conversions"],
                "revenue": record["revenue"],
                "avg_order_value": record["revenue"] / max(1, record["conversions"]),
                "conversion_rate": record["conversions"] / max(1, record["sessions"]) * 100,
            })
        results["traffic_summary"] = self.load_data(traffic_data, "staging", "stg_ga4_traffic")

        # Load GA4 sessions (for mart compatibility)
        print("Loading GA4 sessions...")
        sessions_data = []
        for i, record in enumerate(data["traffic_summary"]):
            sessions_data.append({
                "record_id": f"GA4-SES-{i+1:06d}",
                "property_id": "GA4-DEMO-001",
                "date": record["date"],
                "source": record["source"],
                "medium": record["medium"],
                "campaign": f"campaign_{i % 20 + 1:02d}" if record["medium"] == "cpc" else "(not set)",
                "channel_grouping": self._get_channel_grouping(record["source"], record["medium"]),
                "sessions": record["sessions"],
                "engaged_sessions": int(record["sessions"] * (100 - record["bounce_rate"]) / 100),
                "total_users": record["users"],
                "new_users": record["new_users"],
                "active_users": record["users"],
                "returning_users": record["users"] - record["new_users"],
                "bounce_rate": record["bounce_rate"],
                "engagement_rate": 100 - record["bounce_rate"],
                "avg_session_duration": record["avg_session_duration"],
                "events_per_session": 5.0,
                "screen_page_views": record["sessions"] * 3,
                "session_duration_total": record["sessions"] * record["avg_session_duration"],
            })
        results["sessions"] = self.load_data(sessions_data, "staging", "stg_ga4_sessions")

        # Load page performance
        print("Loading GA4 page performance...")
        pages_data = []
        for i, record in enumerate(data["page_performance"]):
            pages_data.append({
                "record_id": f"GA4-PG-{i+1:06d}",
                "property_id": "GA4-DEMO-001",
                "date": record["date"],
                "page_path": record["page_path"],
                "page_title": record["page_title"],
                "page_views": record["pageviews"],
                "unique_page_views": record["unique_pageviews"],
                "sessions": int(record["pageviews"] * 0.7),
                "bounce_rate": 50.0,
                "engagement_rate": 50.0,
                "avg_time_on_page": record["avg_time_on_page"],
                "exit_rate": record["exit_rate"],
                "entrances": record["entrances"],
                "exits": record["exits"],
            })
        results["page_performance"] = self.load_data(pages_data, "staging", "stg_ga4_pages")

        # Load device summary
        print("Loading GA4 device summary...")
        results["device_summary"] = self.load_data(
            data["device_summary"], "staging", "stg_ga4_devices"
        )

        # Load daily overview
        print("Loading GA4 daily overview...")
        results["daily_overview"] = self.load_data(
            data["daily_overview"], "staging", "stg_ga4_daily"
        )

        return results

    def _get_channel_grouping(self, source: str, medium: str) -> str:
        """Get channel grouping from source/medium."""
        source_lower = source.lower()
        medium_lower = medium.lower()

        if medium_lower in ["cpc", "ppc", "paid"]:
            return "Paid Search" if "google" in source_lower else "Paid Social"
        elif medium_lower == "organic":
            return "Organic Search"
        elif medium_lower == "social":
            return "Organic Social"
        elif medium_lower == "referral":
            return "Referral"
        elif medium_lower == "email":
            return "Email"
        elif medium_lower == "(none)" or source_lower == "(direct)":
            return "Direct"
        else:
            return "Other"

    def load_all(self, days_back: int = 90) -> dict:
        """Load all demo data."""
        print(f"Loading demo data for last {days_back} days...")
        print(f"Project: {self.project_id}")

        results = {
            "ecommerce": self.load_ecommerce_data(days_back),
            "ads": self.load_ads_data(days_back),
            "ga4": self.load_ga4_data(days_back),
        }

        # Summary
        print("\n" + "=" * 50)
        print("LOAD COMPLETE")
        print("=" * 50)

        total_rows = 0
        for category, tables in results.items():
            print(f"\n{category.upper()}:")
            for table, count in tables.items():
                print(f"  {table}: {count:,} rows")
                total_rows += count

        print(f"\nTotal rows loaded: {total_rows:,}")

        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Load demo data to BigQuery")
    parser.add_argument(
        "--project",
        "-p",
        default="marketing-dashboard-480509",
        help="GCP project ID",
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=90,
        help="Days of data to generate (default: 90)",
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=["all", "ecommerce", "ads", "ga4"],
        default="all",
        help="Type of data to load (default: all)",
    )

    args = parser.parse_args()

    loader = BigQueryLoader(project_id=args.project)

    if args.type == "all":
        loader.load_all(days_back=args.days)
    elif args.type == "ecommerce":
        loader.load_ecommerce_data(days_back=args.days)
    elif args.type == "ads":
        loader.load_ads_data(days_back=args.days)
    elif args.type == "ga4":
        loader.load_ga4_data(days_back=args.days)


if __name__ == "__main__":
    main()
