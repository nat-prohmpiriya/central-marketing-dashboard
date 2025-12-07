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
        loaded_at = datetime.utcnow().isoformat()
        for record in data:
            record["_loaded_at"] = loaded_at
            record["_source"] = "demo_data"

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

        # Load orders
        print("Loading orders...")
        results["orders"] = self.load_data(data["orders"], "staging", "stg_orders")

        # Load order items
        print("Loading order items...")
        results["order_items"] = self.load_data(data["order_items"], "staging", "stg_order_items")

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

        # Load daily performance
        print("Loading ads daily performance...")
        results["daily_performance"] = self.load_data(
            data["daily_performance"], "staging", "stg_ads_daily_performance"
        )

        return results

    def load_ga4_data(self, days_back: int = 90) -> dict:
        """Load GA4 demo data."""
        print("\nGenerating GA4 data...")
        data = generate_ga4_data(days_back=days_back)

        results = {}

        # Load traffic summary
        print("Loading GA4 traffic summary...")
        results["traffic_summary"] = self.load_data(
            data["traffic_summary"], "staging", "stg_ga4_traffic"
        )

        # Load page performance
        print("Loading GA4 page performance...")
        results["page_performance"] = self.load_data(
            data["page_performance"], "staging", "stg_ga4_pages"
        )

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
