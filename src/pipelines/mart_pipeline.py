"""Mart layer pipeline for refreshing BigQuery mart tables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.utils.config import get_settings
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from google.cloud import bigquery


class MartTable(Enum):
    """Mart table definitions with dependencies."""

    DAILY_PERFORMANCE = "daily_performance"
    SHOP_PERFORMANCE = "shop_performance"
    ADS_CHANNEL = "ads_channel"
    CAMPAIGN = "campaign"
    PRODUCT = "product"


# Mart table dependencies (tables that must be refreshed before this one)
MART_DEPENDENCIES: dict[MartTable, list[MartTable]] = {
    MartTable.DAILY_PERFORMANCE: [],  # No dependencies, uses staging
    MartTable.SHOP_PERFORMANCE: [],  # No dependencies, uses staging
    MartTable.ADS_CHANNEL: [],  # No dependencies, uses staging
    MartTable.CAMPAIGN: [],  # No dependencies, uses staging
    MartTable.PRODUCT: [],  # No dependencies, uses staging
}

# SQL file paths relative to sql/transformations/mart/
MART_SQL_FILES: dict[MartTable, str] = {
    MartTable.DAILY_PERFORMANCE: "daily_performance.sql",
    MartTable.SHOP_PERFORMANCE: "shop_performance.sql",
    MartTable.ADS_CHANNEL: "ads_channel.sql",
    MartTable.CAMPAIGN: "campaign.sql",
    MartTable.PRODUCT: "product.sql",
}


@dataclass
class MartRefreshResult:
    """Result of mart table refresh."""

    table: MartTable
    success: bool
    start_time: datetime
    end_time: datetime | None = None
    error: str | None = None
    rows_affected: int = 0
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
            "table": self.table.value,
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "error": self.error,
            "rows_affected": self.rows_affected,
            "query_cost_bytes": self.query_cost_bytes,
        }


@dataclass
class MartPipelineResult:
    """Result of mart pipeline execution."""

    success: bool
    start_time: datetime
    end_time: datetime | None = None
    tables_refreshed: list[MartRefreshResult] = field(default_factory=list)
    tables_failed: list[MartRefreshResult] = field(default_factory=list)
    tables_skipped: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float | None:
        """Get duration in seconds."""
        if self.end_time is None:
            return None
        return (self.end_time - self.start_time).total_seconds()

    @property
    def total_tables(self) -> int:
        """Get total number of tables processed."""
        return len(self.tables_refreshed) + len(self.tables_failed)

    @property
    def total_rows_affected(self) -> int:
        """Get total rows affected across all tables."""
        return sum(r.rows_affected for r in self.tables_refreshed)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            "total_tables": self.total_tables,
            "tables_succeeded": len(self.tables_refreshed),
            "tables_failed": len(self.tables_failed),
            "tables_skipped": len(self.tables_skipped),
            "total_rows_affected": self.total_rows_affected,
            "refreshed": [r.to_dict() for r in self.tables_refreshed],
            "failed": [r.to_dict() for r in self.tables_failed],
            "skipped": self.tables_skipped,
        }


class MartPipeline:
    """Pipeline for refreshing BigQuery mart layer.

    Features:
    - Execute mart SQL transformations
    - Handle dependencies between mart tables
    - Support selective refresh (specific tables only)
    - Track execution metrics
    """

    def __init__(
        self,
        tables: list[MartTable] | None = None,
        sql_dir: str | Path | None = None,
    ):
        """Initialize mart pipeline.

        Args:
            tables: List of tables to refresh. If None, all tables.
            sql_dir: Directory containing SQL files. If None, uses default.
        """
        self.settings = get_settings()
        self.logger = get_logger("pipeline.mart")

        # Determine tables to refresh
        self.tables = tables or list(MartTable)

        # SQL directory
        if sql_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.sql_dir = project_root / "sql" / "transformations" / "mart"
        else:
            self.sql_dir = Path(sql_dir)

        # BigQuery client
        self._client: bigquery.Client | None = None

        # Track results
        self._result: MartPipelineResult | None = None

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

    def run(self, continue_on_error: bool = True) -> MartPipelineResult:
        """Run the mart pipeline.

        Args:
            continue_on_error: Continue processing if a table fails.

        Returns:
            MartPipelineResult with execution details.
        """
        self._result = MartPipelineResult(
            success=False,
            start_time=datetime.now(timezone.utc),
        )

        try:
            # Sort tables by dependencies
            ordered_tables = self._topological_sort(self.tables)
            self.logger.info(
                "Starting mart refresh",
                tables=[t.value for t in ordered_tables],
            )

            # Track completed tables for dependency checking
            completed: set[MartTable] = set()

            for table in ordered_tables:
                # Check dependencies
                deps = MART_DEPENDENCIES.get(table, [])
                missing_deps = [d for d in deps if d not in completed]

                if missing_deps:
                    self.logger.warning(
                        "Skipping table due to missing dependencies",
                        table=table.value,
                        missing=[d.value for d in missing_deps],
                    )
                    self._result.tables_skipped.append(table.value)
                    continue

                # Refresh the table
                result = self._refresh_table(table)

                if result.success:
                    self._result.tables_refreshed.append(result)
                    completed.add(table)
                    self.logger.info(
                        "Table refreshed successfully",
                        table=table.value,
                        rows=result.rows_affected,
                        duration=result.duration_seconds,
                    )
                else:
                    self._result.tables_failed.append(result)
                    self.logger.error(
                        "Table refresh failed",
                        table=table.value,
                        error=result.error,
                    )

                    if not continue_on_error:
                        break

            # Set overall success
            self._result.success = len(self._result.tables_failed) == 0

        except Exception as e:
            self.logger.error("Mart pipeline failed", error=str(e))
            self._result.success = False

        finally:
            self._result.end_time = datetime.now(timezone.utc)
            self.close()

        return self._result

    def _refresh_table(self, table: MartTable) -> MartRefreshResult:
        """Refresh a single mart table.

        Args:
            table: Table to refresh.

        Returns:
            MartRefreshResult with execution details.
        """
        result = MartRefreshResult(
            table=table,
            success=False,
            start_time=datetime.now(timezone.utc),
        )

        try:
            # Load SQL
            sql = self._load_sql(table)
            if sql is None:
                result.error = f"SQL file not found for {table.value}"
                result.end_time = datetime.now(timezone.utc)
                return result

            # Substitute variables
            sql = self._substitute_variables(sql)

            # Execute SQL (may contain multiple statements)
            statements = self._split_statements(sql)
            total_rows = 0
            total_bytes = 0

            for statement in statements:
                if not statement.strip():
                    continue

                self.logger.debug(
                    "Executing statement",
                    table=table.value,
                    preview=statement[:100] + "..." if len(statement) > 100 else statement,
                )

                try:
                    job = self.client.query(statement)
                    job_result = job.result()

                    # Track metrics
                    if job.num_dml_affected_rows:
                        total_rows += job.num_dml_affected_rows
                    if job.total_bytes_billed:
                        total_bytes += job.total_bytes_billed

                except Exception as e:
                    # Catch any BigQuery-related errors
                    result.error = f"Query failed: {str(e)}"
                    result.end_time = datetime.now(timezone.utc)
                    return result

            result.success = True
            result.rows_affected = total_rows
            result.query_cost_bytes = total_bytes

        except Exception as e:
            result.error = str(e)

        finally:
            result.end_time = datetime.now(timezone.utc)

        return result

    def _load_sql(self, table: MartTable) -> str | None:
        """Load SQL file for a mart table.

        Args:
            table: Table to load SQL for.

        Returns:
            SQL content or None if not found.
        """
        filename = MART_SQL_FILES.get(table)
        if filename is None:
            return None

        sql_path = self.sql_dir / filename
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

    def _topological_sort(self, tables: list[MartTable]) -> list[MartTable]:
        """Sort tables by dependencies (topological sort).

        Args:
            tables: Tables to sort.

        Returns:
            Sorted list of tables.
        """
        # Create dependency graph for requested tables only
        graph: dict[MartTable, list[MartTable]] = {}
        for table in tables:
            deps = MART_DEPENDENCIES.get(table, [])
            # Only include dependencies that are in the requested tables
            graph[table] = [d for d in deps if d in tables]

        # Kahn's algorithm
        in_degree: dict[MartTable, int] = {t: 0 for t in tables}
        for table in tables:
            for dep in graph.get(table, []):
                if dep in in_degree:
                    in_degree[table] += 1

        # Start with tables that have no dependencies
        queue = [t for t in tables if in_degree[t] == 0]
        result: list[MartTable] = []

        while queue:
            table = queue.pop(0)
            result.append(table)

            # Reduce in-degree for dependent tables
            for other in tables:
                if table in graph.get(other, []):
                    in_degree[other] -= 1
                    if in_degree[other] == 0:
                        queue.append(other)

        # Check for cycles
        if len(result) != len(tables):
            self.logger.warning(
                "Dependency cycle detected, using original order",
                sorted_count=len(result),
                total_count=len(tables),
            )
            return tables

        return result

    def get_result(self) -> MartPipelineResult | None:
        """Get the pipeline result.

        Returns:
            MartPipelineResult if pipeline has run, None otherwise.
        """
        return self._result

    def refresh_table(self, table: MartTable | str) -> MartRefreshResult:
        """Refresh a single table directly.

        Args:
            table: Table to refresh (MartTable or string name).

        Returns:
            MartRefreshResult with execution details.
        """
        if isinstance(table, str):
            table = MartTable(table)

        result = self._refresh_table(table)
        self.close()
        return result
