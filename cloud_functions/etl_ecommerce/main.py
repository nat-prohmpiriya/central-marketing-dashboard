"""Cloud Function for E-commerce ETL pipeline.

Triggered by Cloud Scheduler or HTTP request.
Extracts orders from Shopee, Lazada, TikTok Shop and loads to BigQuery.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import functions_framework
from flask import Request

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.pipelines import EcommercePipeline
from src.utils.logging import get_logger

logger = get_logger("cloud_function.etl_ecommerce")


@functions_framework.http
def etl_ecommerce(request: Request) -> tuple[str, int, dict]:
    """HTTP Cloud Function for E-commerce ETL.

    Args:
        request: HTTP request object.

    Returns:
        Tuple of (response_body, status_code, headers).
    """
    logger.info("E-commerce ETL function triggered")

    try:
        # Parse request parameters
        request_json = request.get_json(silent=True) or {}

        # Date range (default: last 7 days)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=int(request_json.get("days_back", 7)))

        # Override with specific dates if provided
        if "start_date" in request_json:
            start_date = datetime.fromisoformat(request_json["start_date"])
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)

        if "end_date" in request_json:
            end_date = datetime.fromisoformat(request_json["end_date"])
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)

        # Platforms (default: all)
        platforms = request_json.get("platforms", ["shopee", "lazada", "tiktok_shop"])

        logger.info(
            "Starting E-commerce ETL",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            platforms=platforms,
        )

        # Run pipeline
        pipeline = EcommercePipeline(
            start_date=start_date,
            end_date=end_date,
            platforms=platforms,
        )

        result = pipeline.run()

        # Prepare response
        response = {
            "success": result.success,
            "pipeline": "ecommerce",
            "start_time": result.start_time.isoformat() if result.start_time else None,
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration_seconds": result.duration_seconds,
            "records_extracted": result.records_extracted,
            "records_transformed": result.records_transformed,
            "records_loaded_raw": result.records_loaded_raw,
            "records_loaded_staging": result.records_loaded_staging,
            "errors": result.errors if result.errors else [],
        }

        if result.success:
            logger.info("E-commerce ETL completed successfully", **response)
            return json.dumps(response), 200, {"Content-Type": "application/json"}
        else:
            logger.error("E-commerce ETL completed with errors", **response)
            return json.dumps(response), 500, {"Content-Type": "application/json"}

    except Exception as e:
        logger.exception("E-commerce ETL failed", error=str(e))
        error_response = {
            "success": False,
            "pipeline": "ecommerce",
            "error": str(e),
        }
        return json.dumps(error_response), 500, {"Content-Type": "application/json"}


@functions_framework.cloud_event
def etl_ecommerce_pubsub(cloud_event):
    """Pub/Sub triggered Cloud Function for E-commerce ETL.

    Args:
        cloud_event: CloudEvent object containing Pub/Sub message.
    """
    import base64

    logger.info("E-commerce ETL function triggered via Pub/Sub")

    try:
        # Decode Pub/Sub message
        message_data = {}
        if cloud_event.data and "message" in cloud_event.data:
            message = cloud_event.data["message"]
            if "data" in message:
                message_data = json.loads(base64.b64decode(message["data"]).decode())

        # Date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=int(message_data.get("days_back", 7)))

        platforms = message_data.get("platforms", ["shopee", "lazada", "tiktok_shop"])

        # Run pipeline
        pipeline = EcommercePipeline(
            start_date=start_date,
            end_date=end_date,
            platforms=platforms,
        )

        result = pipeline.run()

        if result.success:
            logger.info(
                "E-commerce ETL completed successfully",
                records_extracted=result.records_extracted,
                records_loaded=result.records_loaded_staging,
            )
        else:
            logger.error(
                "E-commerce ETL completed with errors",
                errors=result.errors,
            )

    except Exception as e:
        logger.exception("E-commerce ETL failed", error=str(e))
        raise
