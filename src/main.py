"""Main entry point for running ETL pipelines.

Usage:
    python -m src.main [OPTIONS] COMMAND

Commands:
    ecommerce   Run e-commerce order pipeline
    ads         Run advertising data pipeline
    products    Run product catalog pipeline
    all         Run all pipelines

Examples:
    # Run e-commerce pipeline for last 7 days
    python -m src.main ecommerce --days 7

    # Run ads pipeline for specific date range
    python -m src.main ads --start-date 2024-01-01 --end-date 2024-01-31

    # Run all pipelines with specific platforms
    python -m src.main all --platforms shopee,lazada

    # Dry run (skip loading)
    python -m src.main ecommerce --dry-run
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from src.pipelines import AdsPipeline, EcommercePipeline, ProductPipeline
from src.pipelines.base import PipelineResult
from src.pipelines.mart_pipeline import MartPipeline, MartPipelineResult, MartTable
from src.utils.logging import get_logger

logger = get_logger("main")


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime.

    Args:
        date_str: Date string in YYYY-MM-DD format.

    Returns:
        datetime object.
    """
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def get_date_range(
    start_date: str | None,
    end_date: str | None,
    days: int | None,
) -> tuple[datetime, datetime]:
    """Get date range from arguments.

    Args:
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        days: Number of days to look back from today.

    Returns:
        Tuple of (start_date, end_date) as datetime objects.
    """
    now = datetime.now(timezone.utc)

    if start_date and end_date:
        return parse_date(start_date), parse_date(end_date)

    if days:
        return now - timedelta(days=days), now

    # Default: last 7 days
    return now - timedelta(days=7), now


def run_ecommerce_pipeline(
    start_date: datetime,
    end_date: datetime,
    platforms: list[str] | None = None,
    skip_raw: bool = False,
    skip_staging: bool = False,
    batch_id: str | None = None,
) -> PipelineResult:
    """Run e-commerce pipeline.

    Args:
        start_date: Start date for extraction.
        end_date: End date for extraction.
        platforms: List of platforms to process.
        skip_raw: Skip loading to raw layer.
        skip_staging: Skip loading to staging layer.
        batch_id: Optional batch identifier.

    Returns:
        PipelineResult with execution details.
    """
    logger.info(
        "Running e-commerce pipeline",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        platforms=platforms,
    )

    pipeline = EcommercePipeline(
        start_date=start_date,
        end_date=end_date,
        batch_id=batch_id,
        platforms=platforms,
    )

    return pipeline.run(skip_raw=skip_raw, skip_staging=skip_staging)


def run_ads_pipeline(
    start_date: datetime,
    end_date: datetime,
    platforms: list[str] | None = None,
    include_ga4: bool = True,
    skip_raw: bool = False,
    skip_staging: bool = False,
    batch_id: str | None = None,
) -> PipelineResult:
    """Run ads pipeline.

    Args:
        start_date: Start date for extraction.
        end_date: End date for extraction.
        platforms: List of ad platforms to process.
        include_ga4: Whether to include GA4 data.
        skip_raw: Skip loading to raw layer.
        skip_staging: Skip loading to staging layer.
        batch_id: Optional batch identifier.

    Returns:
        PipelineResult with execution details.
    """
    logger.info(
        "Running ads pipeline",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        platforms=platforms,
        include_ga4=include_ga4,
    )

    pipeline = AdsPipeline(
        start_date=start_date,
        end_date=end_date,
        batch_id=batch_id,
        platforms=platforms,
        include_ga4=include_ga4,
    )

    return pipeline.run(skip_raw=skip_raw, skip_staging=skip_staging)


def run_product_pipeline(
    start_date: datetime,
    end_date: datetime,
    platforms: list[str] | None = None,
    update_sku_mappings: bool = True,
    skip_raw: bool = False,
    skip_staging: bool = False,
    batch_id: str | None = None,
) -> PipelineResult:
    """Run product pipeline.

    Args:
        start_date: Start date for extraction.
        end_date: End date for extraction.
        platforms: List of platforms to process.
        update_sku_mappings: Whether to update SKU mappings.
        skip_raw: Skip loading to raw layer.
        skip_staging: Skip loading to staging layer.
        batch_id: Optional batch identifier.

    Returns:
        PipelineResult with execution details.
    """
    logger.info(
        "Running product pipeline",
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        platforms=platforms,
        update_sku_mappings=update_sku_mappings,
    )

    pipeline = ProductPipeline(
        start_date=start_date,
        end_date=end_date,
        batch_id=batch_id,
        platforms=platforms,
        update_sku_mappings=update_sku_mappings,
    )

    return pipeline.run(skip_raw=skip_raw, skip_staging=skip_staging)


def run_all_pipelines(
    start_date: datetime,
    end_date: datetime,
    platforms: list[str] | None = None,
    skip_raw: bool = False,
    skip_staging: bool = False,
    batch_id: str | None = None,
) -> dict[str, PipelineResult]:
    """Run all pipelines.

    Args:
        start_date: Start date for extraction.
        end_date: End date for extraction.
        platforms: List of platforms to process.
        skip_raw: Skip loading to raw layer.
        skip_staging: Skip loading to staging layer.
        batch_id: Optional batch identifier.

    Returns:
        Dictionary of pipeline name to PipelineResult.
    """
    results: dict[str, PipelineResult] = {}

    # Generate a shared batch ID for all pipelines
    batch_id = batch_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Run e-commerce pipeline
    logger.info("=" * 50)
    logger.info("Running E-commerce Pipeline")
    logger.info("=" * 50)
    results["ecommerce"] = run_ecommerce_pipeline(
        start_date=start_date,
        end_date=end_date,
        platforms=platforms,
        skip_raw=skip_raw,
        skip_staging=skip_staging,
        batch_id=batch_id,
    )

    # Run ads pipeline
    logger.info("=" * 50)
    logger.info("Running Ads Pipeline")
    logger.info("=" * 50)
    # Filter to ads platforms only
    ads_platforms = None
    if platforms:
        ads_platforms = [
            p for p in platforms
            if p in ["facebook_ads", "google_ads", "tiktok_ads", "line_ads", "shopee_ads", "lazada_ads"]
        ]
    results["ads"] = run_ads_pipeline(
        start_date=start_date,
        end_date=end_date,
        platforms=ads_platforms if ads_platforms else None,
        skip_raw=skip_raw,
        skip_staging=skip_staging,
        batch_id=batch_id,
    )

    # Run product pipeline
    logger.info("=" * 50)
    logger.info("Running Product Pipeline")
    logger.info("=" * 50)
    # Filter to e-commerce platforms for products
    product_platforms = None
    if platforms:
        product_platforms = [
            p for p in platforms
            if p in ["shopee", "lazada", "tiktok_shop"]
        ]
    results["products"] = run_product_pipeline(
        start_date=start_date,
        end_date=end_date,
        platforms=product_platforms if product_platforms else None,
        skip_raw=skip_raw,
        skip_staging=skip_staging,
        batch_id=batch_id,
    )

    return results


def run_mart_pipeline(
    tables: str | None = None,
    continue_on_error: bool = True,
) -> MartPipelineResult:
    """Run mart layer refresh pipeline.

    Args:
        tables: Comma-separated list of table names.
        continue_on_error: Continue processing on table failure.

    Returns:
        MartPipelineResult with execution details.
    """
    logger.info(
        "Running mart pipeline",
        tables=tables,
        continue_on_error=continue_on_error,
    )

    # Parse tables
    mart_tables = None
    if tables:
        mart_tables = []
        for t in tables.split(","):
            t = t.strip()
            try:
                mart_tables.append(MartTable(t))
            except ValueError:
                logger.warning(f"Unknown mart table: {t}")

    pipeline = MartPipeline(tables=mart_tables)
    return pipeline.run(continue_on_error=continue_on_error)


def print_result(result: PipelineResult) -> None:
    """Print pipeline result summary.

    Args:
        result: PipelineResult to print.
    """
    status = "SUCCESS" if result.success else "FAILED"
    print(f"\n{'=' * 50}")
    print(f"Pipeline: {result.pipeline_name}")
    print(f"Status: {status}")
    print(f"Stage: {result.stage.value}")
    print(f"Duration: {result.duration_seconds:.2f}s" if result.duration_seconds else "Duration: N/A")
    print(f"Records extracted: {result.records_extracted}")
    print(f"Records transformed: {result.records_transformed}")
    print(f"Records loaded (raw): {result.records_loaded_raw}")
    print(f"Records loaded (staging): {result.records_loaded_staging}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for err in result.errors[:5]:  # Show first 5 errors
            print(f"  - [{err.get('stage', 'unknown')}] {err.get('message', 'Unknown error')}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more errors")

    if result.metadata:
        print(f"\nMetadata:")
        for key, value in result.metadata.items():
            print(f"  {key}: {value}")

    print("=" * 50)


def print_mart_result(result: MartPipelineResult) -> None:
    """Print mart pipeline result summary.

    Args:
        result: MartPipelineResult to print.
    """
    status = "SUCCESS" if result.success else "FAILED"
    print(f"\n{'=' * 50}")
    print(f"Mart Pipeline: {status}")
    print(f"Duration: {result.duration_seconds:.2f}s" if result.duration_seconds else "Duration: N/A")
    print(f"Tables processed: {result.total_tables}")
    print(f"Tables succeeded: {len(result.tables_refreshed)}")
    print(f"Tables failed: {len(result.tables_failed)}")
    print(f"Tables skipped: {len(result.tables_skipped)}")
    print(f"Total rows affected: {result.total_rows_affected}")

    if result.tables_refreshed:
        print(f"\nRefreshed tables:")
        for r in result.tables_refreshed:
            print(f"  - {r.table.value}: {r.rows_affected} rows ({r.duration_seconds:.2f}s)")

    if result.tables_failed:
        print(f"\nFailed tables:")
        for r in result.tables_failed:
            print(f"  - {r.table.value}: {r.error}")

    if result.tables_skipped:
        print(f"\nSkipped tables: {', '.join(result.tables_skipped)}")

    print("=" * 50)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description="Central Marketing Dashboard ETL Pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Global arguments
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        help="Comma-separated list of platforms",
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        help="Batch identifier for tracking",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip loading to BigQuery",
    )
    parser.add_argument(
        "--skip-raw",
        action="store_true",
        help="Skip loading to raw layer",
    )
    parser.add_argument(
        "--skip-staging",
        action="store_true",
        help="Skip loading to staging layer",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Pipeline to run")

    # Ecommerce command
    ecommerce_parser = subparsers.add_parser("ecommerce", help="Run e-commerce pipeline")
    ecommerce_parser.add_argument(
        "--order-status",
        type=str,
        help="Filter by order status",
    )

    # Ads command
    ads_parser = subparsers.add_parser("ads", help="Run ads pipeline")
    ads_parser.add_argument(
        "--no-ga4",
        action="store_true",
        help="Exclude GA4 data",
    )

    # Products command
    products_parser = subparsers.add_parser("products", help="Run product pipeline")
    products_parser.add_argument(
        "--no-sku-mapping",
        action="store_true",
        help="Skip SKU mapping updates",
    )

    # All command
    all_parser = subparsers.add_parser("all", help="Run all pipelines")

    # Mart command
    mart_parser = subparsers.add_parser("mart", help="Run mart layer refresh")
    mart_parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of mart tables to refresh (default: all)",
    )
    mart_parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop on first table refresh failure",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Parse date range
    start_date, end_date = get_date_range(
        args.start_date,
        args.end_date,
        args.days,
    )

    # Parse platforms
    platforms = None
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",")]

    # Determine skip flags
    skip_raw = args.dry_run or args.skip_raw
    skip_staging = args.dry_run or args.skip_staging

    try:
        if args.command == "ecommerce":
            result = run_ecommerce_pipeline(
                start_date=start_date,
                end_date=end_date,
                platforms=platforms,
                skip_raw=skip_raw,
                skip_staging=skip_staging,
                batch_id=args.batch_id,
            )
            print_result(result)
            return 0 if result.success else 1

        elif args.command == "ads":
            result = run_ads_pipeline(
                start_date=start_date,
                end_date=end_date,
                platforms=platforms,
                include_ga4=not getattr(args, "no_ga4", False),
                skip_raw=skip_raw,
                skip_staging=skip_staging,
                batch_id=args.batch_id,
            )
            print_result(result)
            return 0 if result.success else 1

        elif args.command == "products":
            result = run_product_pipeline(
                start_date=start_date,
                end_date=end_date,
                platforms=platforms,
                update_sku_mappings=not getattr(args, "no_sku_mapping", False),
                skip_raw=skip_raw,
                skip_staging=skip_staging,
                batch_id=args.batch_id,
            )
            print_result(result)
            return 0 if result.success else 1

        elif args.command == "all":
            results = run_all_pipelines(
                start_date=start_date,
                end_date=end_date,
                platforms=platforms,
                skip_raw=skip_raw,
                skip_staging=skip_staging,
                batch_id=args.batch_id,
            )

            # Print all results
            all_success = True
            for name, result in results.items():
                print_result(result)
                if not result.success:
                    all_success = False

            # Print summary
            print(f"\n{'=' * 50}")
            print("SUMMARY")
            print("=" * 50)
            for name, result in results.items():
                status = "OK" if result.success else "FAILED"
                print(f"  {name}: {status}")
            print("=" * 50)

            return 0 if all_success else 1

        elif args.command == "mart":
            result = run_mart_pipeline(
                tables=args.tables,
                continue_on_error=not getattr(args, "stop_on_error", False),
            )
            print_mart_result(result)
            return 0 if result.success else 1

    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 130

    except Exception as e:
        logger.error("Pipeline failed with unexpected error", error=str(e))
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
