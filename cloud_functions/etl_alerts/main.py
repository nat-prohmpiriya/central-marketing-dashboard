"""Cloud Function for Alerts ETL pipeline.

Triggered by Cloud Scheduler or HTTP request.
Generates rule-based marketing alerts from mart data.
"""

import json
import os
import sys
from datetime import datetime, timezone

import functions_framework
from flask import Request

# Add parent directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.simple_alerts import AlertSeverity, AlertType
from src.pipelines import AlertsPipeline
from src.utils.logging import get_logger

logger = get_logger("cloud_function.etl_alerts")


@functions_framework.http
def etl_alerts(request: Request) -> tuple[str, int, dict]:
    """HTTP Cloud Function for Alerts ETL.

    Args:
        request: HTTP request object.

    Returns:
        Tuple of (response_body, status_code, headers).
    """
    logger.info("Alerts ETL function triggered")

    try:
        # Parse request parameters
        request_json = request.get_json(silent=True) or {}

        # Run SQL-based alerts (default: True)
        run_sql = request_json.get("run_sql", True)

        # Run Python-based rules (default: False)
        run_python_rules = request_json.get("run_python_rules", False)

        logger.info(
            "Starting Alerts ETL",
            run_sql=run_sql,
            run_python_rules=run_python_rules,
        )

        # Run pipeline
        pipeline = AlertsPipeline()
        result = pipeline.run(run_sql=run_sql, run_python_rules=run_python_rules)

        # Prepare response
        response = {
            "success": result.success,
            "pipeline": "alerts",
            "start_time": result.start_time.isoformat() if result.start_time else None,
            "end_time": result.end_time.isoformat() if result.end_time else None,
            "duration_seconds": result.duration_seconds,
            "total_alerts": result.total_alerts,
            "sql_result": result.sql_result.to_dict() if result.sql_result else None,
            "python_alerts_count": len(result.python_alerts),
            "error": result.error,
        }

        if result.success:
            logger.info("Alerts ETL completed successfully", **response)
            return json.dumps(response), 200, {"Content-Type": "application/json"}
        else:
            logger.error("Alerts ETL completed with errors", **response)
            return json.dumps(response), 500, {"Content-Type": "application/json"}

    except Exception as e:
        logger.exception("Alerts ETL failed", error=str(e))
        error_response = {
            "success": False,
            "pipeline": "alerts",
            "error": str(e),
        }
        return json.dumps(error_response), 500, {"Content-Type": "application/json"}


@functions_framework.http
def get_alerts(request: Request) -> tuple[str, int, dict]:
    """HTTP Cloud Function to get active alerts.

    Args:
        request: HTTP request object.

    Returns:
        Tuple of (response_body, status_code, headers).
    """
    logger.info("Get alerts function triggered")

    try:
        # Parse request parameters
        request_json = request.get_json(silent=True) or {}
        request_args = request.args

        # Filter parameters
        severity_str = request_json.get("severity") or request_args.get("severity")
        alert_type_str = request_json.get("alert_type") or request_args.get("alert_type")
        platform = request_json.get("platform") or request_args.get("platform")
        limit = int(request_json.get("limit") or request_args.get("limit", 100))

        # Parse enum values
        severity = None
        if severity_str:
            try:
                severity = AlertSeverity(severity_str)
            except ValueError:
                pass

        alert_type = None
        if alert_type_str:
            try:
                alert_type = AlertType(alert_type_str)
            except ValueError:
                pass

        # Get alerts
        pipeline = AlertsPipeline()
        alerts = pipeline.get_active_alerts(
            severity=severity,
            alert_type=alert_type,
            platform=platform,
            limit=limit,
        )

        response = {
            "success": True,
            "count": len(alerts),
            "alerts": alerts,
        }

        return json.dumps(response, default=str), 200, {"Content-Type": "application/json"}

    except Exception as e:
        logger.exception("Get alerts failed", error=str(e))
        error_response = {
            "success": False,
            "error": str(e),
        }
        return json.dumps(error_response), 500, {"Content-Type": "application/json"}


@functions_framework.cloud_event
def etl_alerts_pubsub(cloud_event):
    """Pub/Sub triggered Cloud Function for Alerts ETL.

    Args:
        cloud_event: CloudEvent object containing Pub/Sub message.
    """
    import base64

    logger.info("Alerts ETL function triggered via Pub/Sub")

    try:
        # Decode Pub/Sub message
        message_data = {}
        if cloud_event.data and "message" in cloud_event.data:
            message = cloud_event.data["message"]
            if "data" in message:
                message_data = json.loads(base64.b64decode(message["data"]).decode())

        run_sql = message_data.get("run_sql", True)
        run_python_rules = message_data.get("run_python_rules", False)

        # Run pipeline
        pipeline = AlertsPipeline()
        result = pipeline.run(run_sql=run_sql, run_python_rules=run_python_rules)

        if result.success:
            logger.info(
                "Alerts ETL completed successfully",
                total_alerts=result.total_alerts,
                critical=result.sql_result.critical_count if result.sql_result else 0,
                warning=result.sql_result.warning_count if result.sql_result else 0,
            )
        else:
            logger.error(
                "Alerts ETL completed with errors",
                error=result.error,
            )

    except Exception as e:
        logger.exception("Alerts ETL failed", error=str(e))
        raise
