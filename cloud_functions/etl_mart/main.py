"""Cloud Function for Mart ETL pipeline.

Triggered by Cloud Scheduler or HTTP request.
Refreshes BigQuery mart tables from staging data.
"""

import json
import os
import sys
from datetime import datetime, timezone

import functions_framework
from flask import Request

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.pipelines import MartPipeline, MartTable
from src.utils.logging import get_logger

logger = get_logger("cloud_function.etl_mart")


@functions_framework.http
def etl_mart(request: Request) -> tuple[str, int, dict]:
    """HTTP Cloud Function for Mart ETL.

    Args:
        request: HTTP request object.

    Returns:
        Tuple of (response_body, status_code, headers).
    """
    logger.info("Mart ETL function triggered")

    try:
        # Parse request parameters
        request_json = request.get_json(silent=True) or {}

        # Tables to refresh (default: all)
        table_names = request_json.get("tables", None)
        tables = None

        if table_names:
            tables = []
            for name in table_names:
                try:
                    tables.append(MartTable(name))
                except ValueError:
                    logger.warning(f"Unknown table: {name}")

        # Run in parallel (default: False for safety)
        parallel = request_json.get("parallel", False)

        # Force refresh even if recently updated
        force = request_json.get("force", False)

        logger.info(
            "Starting Mart ETL",
            tables=[t.value for t in tables] if tables else "all",
            parallel=parallel,
            force=force,
        )

        # Run pipeline
        pipeline = MartPipeline()

        if tables:
            result = pipeline.run(tables=tables, parallel=parallel)
        else:
            result = pipeline.run_all(parallel=parallel)

        # Prepare response
        response = {
            "success": result.success,
            "pipeline": "mart",
            "start_time": result.start_time.isoformat() if result.start_time else None,
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration_seconds": result.duration_seconds,
            "total_tables": result.total_tables,
            "tables_refreshed": [r.to_dict() for r in result.tables_refreshed],
            "tables_failed": [r.to_dict() for r in result.tables_failed],
            "tables_skipped": result.tables_skipped,
            "total_bytes_billed": result.total_bytes_billed,
        }

        if result.success:
            logger.info("Mart ETL completed successfully", **response)
            return json.dumps(response), 200, {"Content-Type": "application/json"}
        else:
            logger.error("Mart ETL completed with errors", **response)
            return json.dumps(response), 500, {"Content-Type": "application/json"}

    except Exception as e:
        logger.exception("Mart ETL failed", error=str(e))
        error_response = {
            "success": False,
            "pipeline": "mart",
            "error": str(e),
        }
        return json.dumps(error_response), 500, {"Content-Type": "application/json"}


@functions_framework.cloud_event
def etl_mart_pubsub(cloud_event):
    """Pub/Sub triggered Cloud Function for Mart ETL.

    Args:
        cloud_event: CloudEvent object containing Pub/Sub message.
    """
    import base64

    logger.info("Mart ETL function triggered via Pub/Sub")

    try:
        # Decode Pub/Sub message
        message_data = {}
        if cloud_event.data and "message" in cloud_event.data:
            message = cloud_event.data["message"]
            if "data" in message:
                message_data = json.loads(base64.b64decode(message["data"]).decode())

        # Tables to refresh
        table_names = message_data.get("tables", None)
        tables = None

        if table_names:
            tables = []
            for name in table_names:
                try:
                    tables.append(MartTable(name))
                except ValueError:
                    pass

        parallel = message_data.get("parallel", False)

        # Run pipeline
        pipeline = MartPipeline()

        if tables:
            result = pipeline.run(tables=tables, parallel=parallel)
        else:
            result = pipeline.run_all(parallel=parallel)

        if result.success:
            logger.info(
                "Mart ETL completed successfully",
                tables_refreshed=len(result.tables_refreshed),
            )
        else:
            logger.error(
                "Mart ETL completed with errors",
                tables_failed=[r.table.value for r in result.tables_failed],
            )

    except Exception as e:
        logger.exception("Mart ETL failed", error=str(e))
        raise
