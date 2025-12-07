"""BigQuery loader implementation."""

import json
from datetime import datetime, timezone
from typing import Any, Generator

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

from src.loaders.base import BaseLoader, ConnectionError, LoaderError, WriteError
from src.utils.config import get_settings
from src.utils.logging import get_logger


# BigQuery schema definitions for each table type
BIGQUERY_SCHEMAS = {
    "raw_orders": [
        bigquery.SchemaField("_ingested_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("_source_table", "STRING"),
        bigquery.SchemaField("_batch_id", "STRING"),
        bigquery.SchemaField("platform", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("platform_order_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("raw_data", "JSON", mode="REQUIRED"),
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ],
    "raw_ads": [
        bigquery.SchemaField("_ingested_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("_source_table", "STRING"),
        bigquery.SchemaField("_batch_id", "STRING"),
        bigquery.SchemaField("platform", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("account_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("campaign_id", "STRING"),
        bigquery.SchemaField("adgroup_id", "STRING"),
        bigquery.SchemaField("ad_id", "STRING"),
        bigquery.SchemaField("report_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("level", "STRING"),
        bigquery.SchemaField("raw_data", "JSON", mode="REQUIRED"),
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ],
    "raw_ga4_sessions": [
        bigquery.SchemaField("_ingested_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("_source_table", "STRING"),
        bigquery.SchemaField("_batch_id", "STRING"),
        bigquery.SchemaField("property_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("report_type", "STRING"),
        bigquery.SchemaField("report_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("source", "STRING"),
        bigquery.SchemaField("medium", "STRING"),
        bigquery.SchemaField("raw_data", "JSON", mode="REQUIRED"),
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ],
    "raw_products": [
        bigquery.SchemaField("_ingested_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("_source_table", "STRING"),
        bigquery.SchemaField("_batch_id", "STRING"),
        bigquery.SchemaField("platform", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("platform_product_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sku", "STRING"),
        bigquery.SchemaField("raw_data", "JSON", mode="REQUIRED"),
        bigquery.SchemaField("extracted_at", "TIMESTAMP"),
    ],
}


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
        self._start_time = datetime.now(timezone.utc)

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

        self._end_time = datetime.now(timezone.utc)

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
        staging_table = f"{table_name}_staging_{int(datetime.now(timezone.utc).timestamp())}"
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

    def get_schema(self, table_name: str) -> list[bigquery.SchemaField] | None:
        """Get predefined schema for a table.

        Args:
            table_name: Table name.

        Returns:
            Schema fields list or None if not predefined.
        """
        return BIGQUERY_SCHEMAS.get(table_name)


class RawDataLoader(BigQueryLoader):
    """Loader for raw layer data.

    Handles loading raw data from extractors to BigQuery raw layer.
    - Preserves original data structure as JSON
    - Adds ingestion metadata
    - Handles deduplication at query time (not insert time)
    """

    def __init__(
        self,
        batch_size: int | None = None,
        use_streaming: bool = True,
    ):
        """Initialize raw data loader.

        Args:
            batch_size: Number of records per batch.
            use_streaming: Use streaming inserts (True) or load jobs (False).
        """
        settings = get_settings()
        super().__init__(
            dataset=settings.bigquery_dataset_raw,
            batch_size=batch_size,
            use_streaming=use_streaming,
        )
        self._batch_id: str | None = None

    def set_batch_id(self, batch_id: str) -> None:
        """Set batch ID for tracking.

        Args:
            batch_id: Unique batch identifier.
        """
        self._batch_id = batch_id

    def load_raw_orders(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load raw order data.

        Args:
            records: Raw order records from extractor.

        Returns:
            Number of records loaded.
        """
        return self._load_raw_data(
            records=records,
            table_name="raw_orders",
            extract_fields=self._extract_order_fields,
        )

    def load_raw_ads(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load raw ads data.

        Args:
            records: Raw ads records from extractor.

        Returns:
            Number of records loaded.
        """
        return self._load_raw_data(
            records=records,
            table_name="raw_ads",
            extract_fields=self._extract_ads_fields,
        )

    def load_raw_ga4(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load raw GA4 data.

        Args:
            records: Raw GA4 records from extractor.

        Returns:
            Number of records loaded.
        """
        return self._load_raw_data(
            records=records,
            table_name="raw_ga4_sessions",
            extract_fields=self._extract_ga4_fields,
        )

    def load_raw_products(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load raw product data.

        Args:
            records: Raw product records from extractor.

        Returns:
            Number of records loaded.
        """
        return self._load_raw_data(
            records=records,
            table_name="raw_products",
            extract_fields=self._extract_product_fields,
        )

    def _load_raw_data(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
        table_name: str,
        extract_fields: callable,
    ) -> int:
        """Load raw data with field extraction.

        Args:
            records: Raw records.
            table_name: Target table.
            extract_fields: Function to extract fields from record.

        Returns:
            Number of records loaded.
        """
        processed_records = []
        ingested_at = datetime.now(timezone.utc).isoformat()

        for record in records:
            try:
                # Extract specific fields and keep raw data
                fields = extract_fields(record)
                fields["_ingested_at"] = ingested_at
                fields["_source_table"] = table_name
                fields["_batch_id"] = self._batch_id
                fields["raw_data"] = json.dumps(record)

                processed_records.append(fields)
            except Exception as e:
                self.logger.warning(
                    "Failed to process record for raw load",
                    table=table_name,
                    error=str(e),
                )
                continue

        if not processed_records:
            return 0

        return self.load(processed_records, table_name, add_metadata=False)

    def _extract_order_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Extract order-specific fields for indexing."""
        data = record.get("data", record)
        platform = record.get("platform", "unknown")

        # Determine platform from record structure
        if platform == "unknown":
            if "order_sn" in data or "ordersn" in data:
                platform = "shopee"
            elif "statuses" in data or "order_items" in data:
                platform = "lazada"
            elif "buyer_uid" in data or "payment_info" in data:
                platform = "tiktok_shop"

        # Get platform order ID
        platform_order_id = (
            data.get("order_sn")
            or data.get("ordersn")
            or data.get("order_id")
            or data.get("order_number")
            or str(data.get("id", ""))
        )

        return {
            "platform": platform,
            "platform_order_id": str(platform_order_id),
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_ads_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Extract ads-specific fields for indexing."""
        data = record.get("data", record)
        platform = record.get("platform", "unknown")

        # Determine platform
        if platform == "unknown":
            if "adset_id" in data or "ad_account_id" in record:
                platform = "facebook_ads"
            elif "costMicros" in data.get("metrics", {}):
                platform = "google_ads"
            elif "advertiser_id" in record:
                platform = "tiktok_ads"

        # Extract IDs
        dimensions = data.get("dimensions", {})
        metrics = data.get("metrics", data)
        campaign = data.get("campaign", {})

        return {
            "platform": platform,
            "account_id": str(
                record.get("ad_account_id")
                or record.get("customer_id")
                or record.get("advertiser_id")
                or ""
            ),
            "campaign_id": str(
                data.get("campaign_id")
                or dimensions.get("campaign_id")
                or campaign.get("id")
                or ""
            ),
            "adgroup_id": str(
                data.get("adset_id")
                or data.get("adgroup_id")
                or dimensions.get("adgroup_id")
                or ""
            ),
            "ad_id": str(data.get("ad_id") or dimensions.get("ad_id") or ""),
            "report_date": (
                data.get("date_start")
                or dimensions.get("stat_time_day")
                or record.get("date")
                or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            ),
            "level": record.get("type") or record.get("level") or "unknown",
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_ga4_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Extract GA4-specific fields for indexing."""
        data = record.get("data", {})
        dimensions = data.get("dimensions", {})

        # Parse date
        date_str = dimensions.get("date", "")
        if len(date_str) == 8:
            report_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            report_date = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        return {
            "property_id": str(record.get("property_id", "unknown")),
            "report_type": record.get("type", "sessions"),
            "report_date": report_date,
            "source": dimensions.get("sessionSource") or dimensions.get("source"),
            "medium": dimensions.get("sessionMedium") or dimensions.get("medium"),
            "extracted_at": record.get("extracted_at"),
        }

    def _extract_product_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        """Extract product-specific fields for indexing."""
        data = record.get("data", record)
        platform = record.get("platform", "unknown")

        # Determine platform
        if platform == "unknown":
            if "item_id" in data or "model_sku" in data:
                platform = "shopee"
            elif "sku_name" in data or "product_name" in data:
                platform = "tiktok_shop"
            elif "sku_id" in data or ("name" in data and "seller_sku" in data):
                platform = "lazada"

        # Get product ID
        platform_product_id = str(
            data.get("item_id")
            or data.get("product_id")
            or data.get("sku_id")
            or ""
        )

        return {
            "platform": platform,
            "platform_product_id": platform_product_id,
            "sku": (
                data.get("model_sku")
                or data.get("item_sku")
                or data.get("sku")
                or data.get("seller_sku")
            ),
            "extracted_at": record.get("extracted_at"),
        }


class StagingDataLoader(BigQueryLoader):
    """Loader for staging layer data.

    Handles loading transformed data to BigQuery staging layer.
    - Uses MERGE/upsert for deduplication
    - Handles incremental updates
    """

    def __init__(
        self,
        batch_size: int | None = None,
    ):
        """Initialize staging data loader.

        Args:
            batch_size: Number of records per batch.
        """
        settings = get_settings()
        super().__init__(
            dataset=settings.bigquery_dataset_staging,
            batch_size=batch_size,
            use_streaming=False,  # Use load jobs for staging (better for MERGE)
        )

    def load_orders(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed order data.

        Args:
            records: Transformed order records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        # Add _updated_at timestamp
        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            # Convert datetime objects to strings
            self._convert_datetimes(record)

        return self.upsert(
            records=records_list,
            table_name="stg_orders",
            key_fields=["order_id"],
        )

    def load_order_items(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed order item data.

        Args:
            records: Transformed order item records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            self._convert_datetimes(record)

        return self.upsert(
            records=records_list,
            table_name="stg_order_items",
            key_fields=["item_id", "order_id", "platform"],
        )

    def load_ads(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed ads data.

        Args:
            records: Transformed ads records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            self._convert_datetimes(record)
            # Convert date to string if needed
            if isinstance(record.get("date"), datetime):
                record["date"] = record["date"].strftime("%Y-%m-%d")

        return self.upsert(
            records=records_list,
            table_name="stg_ads",
            key_fields=["record_id"],
        )

    def load_ga4_sessions(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed GA4 session data.

        Args:
            records: Transformed GA4 session records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            self._convert_datetimes(record)
            # Convert date to string
            if isinstance(record.get("date"), datetime):
                record["date"] = record["date"].strftime("%Y-%m-%d")

        return self.upsert(
            records=records_list,
            table_name="stg_ga4_sessions",
            key_fields=["record_id"],
        )

    def load_ga4_traffic(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed GA4 traffic data.

        Args:
            records: Transformed GA4 traffic records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            self._convert_datetimes(record)
            if isinstance(record.get("date"), datetime):
                record["date"] = record["date"].strftime("%Y-%m-%d")

        return self.upsert(
            records=records_list,
            table_name="stg_ga4_traffic",
            key_fields=["record_id"],
        )

    def load_ga4_pages(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed GA4 page data.

        Args:
            records: Transformed GA4 page records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            self._convert_datetimes(record)
            if isinstance(record.get("date"), datetime):
                record["date"] = record["date"].strftime("%Y-%m-%d")

        return self.upsert(
            records=records_list,
            table_name="stg_ga4_pages",
            key_fields=["record_id"],
        )

    def load_products(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load transformed product data.

        Args:
            records: Transformed product records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["_updated_at"] = now
            self._convert_datetimes(record)

        return self.upsert(
            records=records_list,
            table_name="stg_products",
            key_fields=["product_id"],
        )

    def load_sku_mappings(
        self,
        records: Generator[dict[str, Any], None, None] | list[dict[str, Any]],
    ) -> int:
        """Load SKU mapping data.

        Args:
            records: SKU mapping records.

        Returns:
            Number of records affected.
        """
        records_list = list(records)
        if not records_list:
            return 0

        now = datetime.now(timezone.utc).isoformat()
        for record in records_list:
            record["updated_at"] = now
            self._convert_datetimes(record)

        return self.upsert(
            records=records_list,
            table_name="stg_sku_mappings",
            key_fields=["master_sku", "platform", "platform_sku"],
        )

    def _convert_datetimes(self, record: dict[str, Any]) -> None:
        """Convert datetime objects to ISO strings in place.

        Args:
            record: Record to convert.
        """
        for key, value in list(record.items()):
            if isinstance(value, datetime):
                record[key] = value.isoformat()
            elif isinstance(value, list):
                # Handle nested lists (e.g., order items)
                record[key] = json.dumps(value)
