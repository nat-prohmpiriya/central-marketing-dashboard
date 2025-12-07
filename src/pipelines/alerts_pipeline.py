"""Alerts pipeline for generating rule-based marketing alerts.

This pipeline generates alerts based on predefined rules by:
1. Executing the alerts SQL transformation
2. Optionally running Python-based alert rules for more complex logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.models.simple_alerts import (
    Alert,
    AlertRuleEngine,
    AlertSeverity,
    AlertType,
)
from src.utils.config import get_settings
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from google.cloud import bigquery


@dataclass
class AlertsRefreshResult:
    """Result of alerts table refresh."""

    success: bool
    start_time: datetime
    end_time: datetime | None = None
    error: str | None = None
    alerts_generated: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    query_cost_bytes: int = 0

    @property
    def duration_seconds(self) -> float | None:
        """Get duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "alerts_generated": self.alerts_generated,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "query_cost_bytes": self.query_cost_bytes,
        }


@dataclass
class AlertsPipelineResult:
    """Result of alerts pipeline execution."""

    success: bool
    start_time: datetime
    end_time: datetime | None = None
    sql_result: AlertsRefreshResult | None = None
    python_alerts: list[Alert] = field(default_factory=list)
    total_alerts: int = 0
    error: str | None = None

    @property
    def duration_seconds(self) -> float | None:
        """Get duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_alerts": self.total_alerts,
            "sql_result": self.sql_result.to_dict() if self.sql_result else None,
            "python_alerts_count": len(self.python_alerts),
            "error": self.error,
        }


class AlertsPipeline:
    """Pipeline for generating marketing alerts.

    This pipeline:
    1. Executes SQL-based alert generation (mart_simple_alerts)
    2. Can optionally run Python-based alert rules for custom logic
    3. Tracks alert generation metrics

    The SQL transformation handles most alerts by querying mart tables
    and applying threshold rules directly in BigQuery.
    """

    SQL_FILE = "simple_alerts.sql"

    def __init__(
        self,
        sql_dir: str | Path | None = None,
        rule_engine: AlertRuleEngine | None = None,
    ):
        """Initialize alerts pipeline.

        Args:
            sql_dir: Directory containing SQL files. If None, uses default.
            rule_engine: Custom alert rule engine. If None, uses defaults.
        """
        self.settings = get_settings()
        self.logger = get_logger("pipeline.alerts")

        # SQL directory
        if sql_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.sql_dir = project_root / "sql" / "transformations" / "mart"
        else:
            self.sql_dir = Path(sql_dir)

        # Alert rule engine for Python-based rules
        self.rule_engine = rule_engine or AlertRuleEngine()

        # BigQuery client
        self._client: bigquery.Client | None = None

        # Track results
        self._result: AlertsPipelineResult | None = None

    @property
    def client(self) -> "bigquery.Client":
        """Get or create BigQuery client."""
        if self._client is None:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=self.settings.gcp_project_id)
        return self._client

    def close(self) -> None:
        """Close BigQuery client."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def run(
        self,
        run_sql: bool = True,
        run_python_rules: bool = False,
    ) -> AlertsPipelineResult:
        """Run the alerts pipeline.

        Args:
            run_sql: Execute SQL-based alert generation.
            run_python_rules: Also run Python-based alert rules.

        Returns:
            AlertsPipelineResult with execution details.
        """
        self._result = AlertsPipelineResult(
            success=False,
            start_time=datetime.now(timezone.utc),
        )

        try:
            self.logger.info(
                "Starting alerts pipeline",
                run_sql=run_sql,
                run_python_rules=run_python_rules,
            )

            # Run SQL-based alerts
            if run_sql:
                sql_result = self._run_sql_alerts()
                self._result.sql_result = sql_result
                self._result.total_alerts = sql_result.alerts_generated

                if not sql_result.success:
                    self._result.error = sql_result.error
                    self._result.success = False
                    return self._result

            # Run Python-based alerts (for custom logic)
            if run_python_rules:
                python_alerts = self._run_python_alerts()
                self._result.python_alerts = python_alerts
                self._result.total_alerts += len(python_alerts)

            self._result.success = True
            self.logger.info(
                "Alerts pipeline completed",
                total_alerts=self._result.total_alerts,
            )

        except Exception as e:
            self.logger.error("Alerts pipeline failed", error=str(e))
            self._result.error = str(e)
            self._result.success = False

        finally:
            self._result.end_time = datetime.now(timezone.utc)
            self.close()

        return self._result

    def _run_sql_alerts(self) -> AlertsRefreshResult:
        """Execute SQL-based alert generation.

        Returns:
            AlertsRefreshResult with execution details.
        """
        result = AlertsRefreshResult(
            success=False,
            start_time=datetime.now(timezone.utc),
        )

        try:
            # Load SQL
            sql = self._load_sql()
            if sql is None:
                result.error = f"SQL file not found: {self.SQL_FILE}"
                result.end_time = datetime.now(timezone.utc)
                return result

            # Substitute variables
            sql = self._substitute_variables(sql)

            # Execute SQL (may contain multiple statements)
            statements = self._split_statements(sql)
            total_bytes = 0

            for statement in statements:
                if not statement.strip():
                    continue

                self.logger.debug(
                    "Executing statement",
                    preview=statement[:100] + "..." if len(statement) > 100 else statement,
                )

                try:
                    job = self.client.query(statement)
                    job.result()

                    if job.total_bytes_billed:
                        total_bytes += job.total_bytes_billed

                except Exception as e:
                    result.error = f"Query failed: {str(e)}"
                    result.end_time = datetime.now(timezone.utc)
                    return result

            # Get alert counts
            counts = self._get_alert_counts()
            result.alerts_generated = counts.get("total", 0)
            result.critical_count = counts.get("critical", 0)
            result.warning_count = counts.get("warning", 0)
            result.info_count = counts.get("info", 0)
            result.query_cost_bytes = total_bytes

            result.success = True

        except Exception as e:
            result.error = str(e)

        finally:
            result.end_time = datetime.now(timezone.utc)

        return result

    def _run_python_alerts(self) -> list[Alert]:
        """Run Python-based alert rules.

        This method can be extended to query data and run custom
        Python-based alert logic that's too complex for SQL.

        Returns:
            List of generated alerts.
        """
        alerts: list[Alert] = []

        try:
            # Example: Query recent performance data and evaluate
            # This is a placeholder for custom Python-based alert logic
            # In production, this would query BigQuery and evaluate metrics

            self.logger.info("Python alert rules evaluation completed")

        except Exception as e:
            self.logger.error("Python alert rules failed", error=str(e))

        return alerts

    def _get_alert_counts(self) -> dict[str, int]:
        """Get current alert counts from the mart table.

        Returns:
            Dictionary with alert counts by severity.
        """
        try:
            query = f"""
                SELECT
                    COUNTIF(severity = 'critical') as critical,
                    COUNTIF(severity = 'warning') as warning,
                    COUNTIF(severity = 'info') as info,
                    COUNT(*) as total
                FROM `{self.settings.gcp_project_id}.{self.settings.bigquery_dataset_mart}.mart_simple_alerts`
                WHERE status = 'active'
                  AND alert_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
            """
            job = self.client.query(query)
            results = list(job.result())

            if results:
                row = results[0]
                return {
                    "critical": row.critical or 0,
                    "warning": row.warning or 0,
                    "info": row.info or 0,
                    "total": row.total or 0,
                }
        except Exception as e:
            self.logger.warning("Failed to get alert counts", error=str(e))

        return {"critical": 0, "warning": 0, "info": 0, "total": 0}

    def _load_sql(self) -> str | None:
        """Load SQL file for alerts.

        Returns:
            SQL content or None if not found.
        """
        sql_path = self.sql_dir / self.SQL_FILE
        if not sql_path.exists():
            self.logger.warning("SQL file not found", path=str(sql_path))
            return None

        return sql_path.read_text(encoding="utf-8")

    def _substitute_variables(self, sql: str) -> str:
        """Substitute template variables in SQL.

        Args:
            sql: SQL with template variables.

        Returns:
            SQL with variables substituted.
        """
        return (
            sql.replace("${project_id}", self.settings.gcp_project_id)
            .replace("${dataset_raw}", self.settings.bigquery_dataset_raw)
            .replace("${dataset_staging}", self.settings.bigquery_dataset_staging)
            .replace("${dataset_mart}", self.settings.bigquery_dataset_mart)
        )

    def _split_statements(self, sql: str) -> list[str]:
        """Split SQL into individual statements.

        Handles semicolons inside strings and comments.

        Args:
            sql: SQL content.

        Returns:
            List of individual statements.
        """
        statements = []
        current = []
        in_string = False
        string_char = None
        in_comment = False
        in_line_comment = False
        i = 0

        while i < len(sql):
            char = sql[i]
            next_char = sql[i + 1] if i + 1 < len(sql) else ""

            # Handle line comments
            if not in_string and char == "-" and next_char == "-":
                in_line_comment = True
                current.append(char)
                i += 1
                continue

            if in_line_comment:
                if char == "\n":
                    in_line_comment = False
                current.append(char)
                i += 1
                continue

            # Handle block comments
            if not in_string and char == "/" and next_char == "*":
                in_comment = True
                current.append(char)
                i += 1
                continue

            if in_comment:
                if char == "*" and next_char == "/":
                    in_comment = False
                    current.append(char)
                    current.append(next_char)
                    i += 2
                    continue
                current.append(char)
                i += 1
                continue

            # Handle strings
            if char in ("'", '"') and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None

            # Handle statement separator
            if char == ";" and not in_string and not in_comment:
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(char)

            i += 1

        # Add remaining content
        statement = "".join(current).strip()
        if statement:
            statements.append(statement)

        return statements

    def get_result(self) -> AlertsPipelineResult | None:
        """Get the pipeline result.

        Returns:
            AlertsPipelineResult if pipeline has run, None otherwise.
        """
        return self._result

    def refresh_alerts(self) -> AlertsRefreshResult:
        """Refresh alerts table directly.

        Convenience method to only run SQL alerts.

        Returns:
            AlertsRefreshResult with execution details.
        """
        result = self._run_sql_alerts()
        self.close()
        return result

    def get_active_alerts(
        self,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        platform: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get active alerts from the mart table.

        Args:
            severity: Filter by severity level.
            alert_type: Filter by alert type.
            platform: Filter by platform.
            limit: Maximum number of alerts to return.

        Returns:
            List of alert dictionaries.
        """
        try:
            conditions = ["status = 'active'"]

            if severity:
                conditions.append(f"severity = '{severity.value}'")
            if alert_type:
                conditions.append(f"alert_type = '{alert_type.value}'")
            if platform:
                conditions.append(f"platform = '{platform}'")

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT *
                FROM `{self.settings.gcp_project_id}.{self.settings.bigquery_dataset_mart}.mart_simple_alerts`
                WHERE {where_clause}
                ORDER BY
                    CASE severity
                        WHEN 'critical' THEN 1
                        WHEN 'warning' THEN 2
                        ELSE 3
                    END,
                    created_at DESC
                LIMIT {limit}
            """

            job = self.client.query(query)
            results = []

            for row in job.result():
                results.append(dict(row))

            return results

        except Exception as e:
            self.logger.error("Failed to get active alerts", error=str(e))
            return []

        finally:
            self.close()
