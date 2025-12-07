"""BigQuery loader implementation."""

from datetime import datetime
from typing import Any, Generator

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

from src.loaders.base import BaseLoader, ConnectionError, LoaderError, WriteError
from src.utils.config import get_settings
from src.utils.logging import get_logger


class BigQueryLoader(BaseLoader):
    """Loader for Google BigQuery.

    Features:
    - Batch loading with streaming inserts or load jobs
    - Automatic schema detection
    - Deduplication support
    - Partition and cluster configuration
    """

    destination_name = "bigquery"
    default_batch_size = 1000

    def __init__(
        self,
        dataset: str | None = None,
        batch_size: int | None = None,
        use_streaming: bool = True,
    ):
        """Initialize BigQuery loader.

        Args:
            dataset: Target dataset name. If None, uses settings.
            batch_size: Number of records per batch.
            use_streaming: Use streaming inserts (True) or load jobs (False).
        """
        super().__init__(batch_size=batch_size)

        self.settings = get_settings()
        self.dataset = dataset or self.settings.bigquery_dataset_raw
        self.project_id = self.settings.gcp_project_id
        self.use_streaming = use_streaming

        self._client: bigquery.Client | None = None
        self.logger = get_logger("loader.bigquery")

    @property
    def client(self) -> bigquery.Client:
        """Get or create BigQuery client."""
        if self._client is None:
            self.connect()
        return self._client  # type: ignore

    def connect(self) -> bool:
        """Connect to BigQuery.

        Returns:
            True if connection successful.

        Raises:
            ConnectionError: If connection fails.
        """
        try:
            self._client = bigquery.Client(project=self.project_id)
            # Test connection
            self._client.query("SELECT 1").result()
            self.logger.info(
                "Connected to BigQuery",
                project=self.project_id,
                dataset=self.dataset,
            )
            return True
        except GoogleCloudError as e:
            raise ConnectionError(
                message=f"Failed to connect to BigQuery: {e}",
                destination="bigquery",
                details={"project": self.project_id, "error": str(e)},
            )

    def close(self) -> None:
        """Close the BigQuery client."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self.logger.info("BigQuery connection closed")

    def load(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
        table_name: str,
        **kwargs: Any,
    ) -> int:
        """Load records to BigQuery.

        Args:
            records: Records to load.
            table_name: Target table name (without dataset prefix).
            **kwargs: Additional options:
                - add_metadata: Add ingestion metadata (default: True)
                - deduplicate_key: Field to use for deduplication

        Returns:
            Number of records successfully loaded.
        """
        add_metadata = kwargs.get("add_metadata", True)
        self._start_time = datetime.utcnow()

        total_loaded = 0

        for batch in self._batch_records(records):
            if add_metadata:
                batch = [self._add_metadata(r, table_name) for r in batch]

            try:
                loaded = self._write_batch(batch, table_name, **kwargs)
                total_loaded += loaded
                self._records_loaded += loaded
                self._batches_loaded += 1
            except WriteError as e:
                self.logger.error(
                    "Batch write failed",
                    table=table_name,
                    batch_size=len(batch),
                    error=str(e),
                )
                self._records_failed += len(batch)

        self._end_time = datetime.utcnow()

        self.logger.info(
            "Load complete",
            table=table_name,
            records_loaded=total_loaded,
            batches=self._batches_loaded,
        )

        return total_loaded

    def _write_batch(
        self,
        records: list[dict[str, Any]],
        table_name: str,
        **kwargs: Any,
    ) -> int:
        """Write a batch of records to BigQuery.

        Args:
            records: Records to write.
            table_name: Target table.
            **kwargs: Additional options.

        Returns:
            Number of records written.
        """
        if not records:
            return 0

        table_id = f"{self.project_id}.{self.dataset}.{table_name}"

        if self.use_streaming:
            return self._streaming_insert(records, table_id)
        else:
            return self._load_job(records, table_id)

    def _streaming_insert(
        self,
        records: list[dict[str, Any]],
        table_id: str,
    ) -> int:
        """Insert records using streaming API.

        Args:
            records: Records to insert.
            table_id: Full table ID.

        Returns:
            Number of records inserted.
        """
        try:
            errors = self.client.insert_rows_json(table_id, records)

            if errors:
                error_count = len(errors)
                self.logger.warning(
                    "Streaming insert had errors",
                    table=table_id,
                    error_count=error_count,
                    errors=errors[:5],  # Log first 5 errors
                )
                return len(records) - error_count

            return len(records)

        except GoogleCloudError as e:
            raise WriteError(
                message=f"Streaming insert failed: {e}",
                destination="bigquery",
                details={"table": table_id, "error": str(e)},
            )

    def _load_job(
        self,
        records: list[dict[str, Any]],
        table_id: str,
    ) -> int:
        """Load records using a load job (more reliable for large batches).

        Args:
            records: Records to load.
            table_id: Full table ID.

        Returns:
            Number of records loaded.
        """
        import json
        import tempfile

        try:
            # Write to temp file as newline-delimited JSON
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
            ) as f:
                for record in records:
                    f.write(json.dumps(record) + "\n")
                temp_path = f.name

            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                autodetect=True,
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            )

            with open(temp_path, "rb") as f:
                job = self.client.load_table_from_file(
                    f,
                    table_id,
                    job_config=job_config,
                )

            job.result()  # Wait for job to complete

            return len(records)

        except GoogleCloudError as e:
            raise WriteError(
                message=f"Load job failed: {e}",
                destination="bigquery",
                details={"table": table_id, "error": str(e)},
            )

    def ensure_table_exists(
        self,
        table_name: str,
        schema: list[bigquery.SchemaField] | None = None,
        partition_field: str | None = None,
        cluster_fields: list[str] | None = None,
    ) -> None:
        """Ensure a table exists, creating it if necessary.

        Args:
            table_name: Table name.
            schema: Table schema. If None, table must exist or autodetect is used.
            partition_field: Field to partition by (must be DATE or TIMESTAMP).
            cluster_fields: Fields to cluster by.
        """
        table_id = f"{self.project_id}.{self.dataset}.{table_name}"

        try:
            self.client.get_table(table_id)
            self.logger.debug("Table exists", table=table_id)
        except GoogleCloudError:
            # Table doesn't exist, create it
            if schema is None:
                self.logger.warning(
                    "Table doesn't exist and no schema provided",
                    table=table_id,
                )
                return

            table = bigquery.Table(table_id, schema=schema)

            if partition_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    field=partition_field
                )

            if cluster_fields:
                table.clustering_fields = cluster_fields

            self.client.create_table(table)
            self.logger.info("Table created", table=table_id)

    def upsert(
        self,
        records: list[dict[str, Any]],
        table_name: str,
        key_fields: list[str],
    ) -> int:
        """Upsert records (insert or update based on key).

        Uses MERGE statement for deduplication.

        Args:
            records: Records to upsert.
            table_name: Target table.
            key_fields: Fields that make up the primary key.

        Returns:
            Number of records affected.
        """
        if not records:
            return 0

        table_id = f"{self.project_id}.{self.dataset}.{table_name}"
        staging_table = f"{table_name}_staging_{int(datetime.utcnow().timestamp())}"
        staging_table_id = f"{self.project_id}.{self.dataset}.{staging_table}"

        try:
            # Load to staging table
            self._load_job(records, staging_table_id)

            # Build MERGE statement
            key_condition = " AND ".join(
                f"target.{k} = source.{k}" for k in key_fields
            )

            # Get field names from first record
            fields = list(records[0].keys())
            update_fields = ", ".join(f"target.{f} = source.{f}" for f in fields)
            insert_fields = ", ".join(fields)
            insert_values = ", ".join(f"source.{f}" for f in fields)

            merge_query = f"""
                MERGE `{table_id}` AS target
                USING `{staging_table_id}` AS source
                ON {key_condition}
                WHEN MATCHED THEN
                    UPDATE SET {update_fields}
                WHEN NOT MATCHED THEN
                    INSERT ({insert_fields})
                    VALUES ({insert_values})
            """

            job = self.client.query(merge_query)
            job.result()

            # Get affected rows
            affected = job.num_dml_affected_rows or len(records)

            # Clean up staging table
            self.client.delete_table(staging_table_id, not_found_ok=True)

            self.logger.info(
                "Upsert complete",
                table=table_name,
                affected_rows=affected,
            )

            return affected

        except GoogleCloudError as e:
            # Clean up staging table on error
            self.client.delete_table(staging_table_id, not_found_ok=True)
            raise LoaderError(
                message=f"Upsert failed: {e}",
                destination="bigquery",
                details={"table": table_name, "error": str(e)},
            )

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a query and return results.

        Args:
            query: SQL query to execute.

        Returns:
            List of result rows as dictionaries.
        """
        try:
            job = self.client.query(query)
            results = job.result()
            return [dict(row) for row in results]
        except GoogleCloudError as e:
            raise LoaderError(
                message=f"Query failed: {e}",
                destination="bigquery",
                details={"query": query[:500], "error": str(e)},
            )
