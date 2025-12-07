"""SKU Mapper for cross-platform product mapping.

Maps platform-specific SKUs to a unified master SKU for analytics
and inventory management across Shopee, Lazada, and TikTok Shop.
"""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.utils.logging import get_logger


class SKUMapping(BaseModel):
    """SKU mapping entry."""

    master_sku: str
    platform: str
    platform_sku: str
    product_name: str | None = None
    variation: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SKUMappingNotFoundError(Exception):
    """Raised when SKU mapping is not found."""

    def __init__(self, platform: str, sku: str):
        self.platform = platform
        self.sku = sku
        super().__init__(f"SKU mapping not found: {platform}/{sku}")


class SKUMapper:
    """Map platform-specific SKUs to master SKUs.

    Supports loading mappings from CSV files and provides methods
    for mapping individual products or batches.

    CSV Format:
        master_sku,platform,platform_sku,product_name,variation,notes

    Example:
        PROD-001,shopee,SP-12345,Product Name,Size M,Main product
        PROD-001,lazada,LZ-12345,Product Name,Size M,
        PROD-001,tiktok_shop,TT-12345,Product Name,Size M,
    """

    SUPPORTED_PLATFORMS = ["shopee", "lazada", "tiktok_shop"]

    def __init__(self, mapping_file: str | Path | None = None):
        """Initialize SKU mapper.

        Args:
            mapping_file: Path to CSV mapping file. If None, starts with empty mapping.
        """
        self.logger = get_logger("sku_mapper")
        self._mappings: dict[str, dict[str, str]] = {}  # {platform: {sku: master_sku}}
        self._reverse_mappings: dict[str, list[tuple[str, str]]] = {}  # {master_sku: [(platform, sku)]}
        self._mapping_details: dict[str, SKUMapping] = {}  # {platform:sku: SKUMapping}

        if mapping_file:
            self.load_from_csv(mapping_file)

    def load_from_csv(self, file_path: str | Path) -> int:
        """Load SKU mappings from CSV file.

        Args:
            file_path: Path to CSV mapping file.

        Returns:
            Number of mappings loaded.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If CSV format is invalid.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {file_path}")

        count = 0
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Validate required columns
            required_columns = {"master_sku", "platform", "platform_sku"}
            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no headers")

            missing = required_columns - set(reader.fieldnames)
            if missing:
                raise ValueError(f"Missing required columns: {missing}")

            for row in reader:
                # Skip empty rows
                if not row.get("master_sku") or not row.get("platform_sku"):
                    continue

                platform = row["platform"].lower().strip()
                if platform not in self.SUPPORTED_PLATFORMS:
                    self.logger.warning(
                        "Unknown platform in mapping",
                        platform=platform,
                        sku=row["platform_sku"],
                    )
                    continue

                self.add_mapping(
                    master_sku=row["master_sku"].strip(),
                    platform=platform,
                    platform_sku=row["platform_sku"].strip(),
                    product_name=row.get("product_name", "").strip() or None,
                    variation=row.get("variation", "").strip() or None,
                    notes=row.get("notes", "").strip() or None,
                )
                count += 1

        self.logger.info(
            "Loaded SKU mappings",
            file=str(file_path),
            count=count,
        )
        return count

    def save_to_csv(self, file_path: str | Path) -> int:
        """Save current mappings to CSV file.

        Args:
            file_path: Path to save CSV file.

        Returns:
            Number of mappings saved.
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "master_sku",
                    "platform",
                    "platform_sku",
                    "product_name",
                    "variation",
                    "notes",
                ],
            )
            writer.writeheader()

            for key, mapping in self._mapping_details.items():
                writer.writerow({
                    "master_sku": mapping.master_sku,
                    "platform": mapping.platform,
                    "platform_sku": mapping.platform_sku,
                    "product_name": mapping.product_name or "",
                    "variation": mapping.variation or "",
                    "notes": mapping.notes or "",
                })
                count += 1

        self.logger.info(
            "Saved SKU mappings",
            file=str(file_path),
            count=count,
        )
        return count

    def add_mapping(
        self,
        master_sku: str,
        platform: str,
        platform_sku: str,
        product_name: str | None = None,
        variation: str | None = None,
        notes: str | None = None,
    ) -> SKUMapping:
        """Add a SKU mapping.

        Args:
            master_sku: Unified master SKU.
            platform: Platform name (shopee, lazada, tiktok_shop).
            platform_sku: Platform-specific SKU.
            product_name: Optional product name.
            variation: Optional variation name.
            notes: Optional notes.

        Returns:
            Created SKU mapping.
        """
        platform = platform.lower()
        if platform not in self.SUPPORTED_PLATFORMS:
            raise ValueError(f"Unsupported platform: {platform}")

        # Add to forward mapping
        if platform not in self._mappings:
            self._mappings[platform] = {}
        self._mappings[platform][platform_sku] = master_sku

        # Add to reverse mapping
        if master_sku not in self._reverse_mappings:
            self._reverse_mappings[master_sku] = []

        # Avoid duplicates in reverse mapping
        entry = (platform, platform_sku)
        if entry not in self._reverse_mappings[master_sku]:
            self._reverse_mappings[master_sku].append(entry)

        # Store detailed mapping
        mapping = SKUMapping(
            master_sku=master_sku,
            platform=platform,
            platform_sku=platform_sku,
            product_name=product_name,
            variation=variation,
            notes=notes,
        )
        self._mapping_details[f"{platform}:{platform_sku}"] = mapping

        return mapping

    def remove_mapping(self, platform: str, platform_sku: str) -> bool:
        """Remove a SKU mapping.

        Args:
            platform: Platform name.
            platform_sku: Platform-specific SKU.

        Returns:
            True if mapping was removed, False if not found.
        """
        platform = platform.lower()
        key = f"{platform}:{platform_sku}"

        if key not in self._mapping_details:
            return False

        mapping = self._mapping_details.pop(key)

        # Remove from forward mapping
        if platform in self._mappings and platform_sku in self._mappings[platform]:
            del self._mappings[platform][platform_sku]

        # Remove from reverse mapping
        if mapping.master_sku in self._reverse_mappings:
            entry = (platform, platform_sku)
            if entry in self._reverse_mappings[mapping.master_sku]:
                self._reverse_mappings[mapping.master_sku].remove(entry)

        return True

    def get_master_sku(
        self,
        platform: str,
        platform_sku: str,
        raise_if_not_found: bool = False,
    ) -> str | None:
        """Get master SKU for a platform-specific SKU.

        Args:
            platform: Platform name.
            platform_sku: Platform-specific SKU.
            raise_if_not_found: If True, raise exception when not found.

        Returns:
            Master SKU or None if not found.

        Raises:
            SKUMappingNotFoundError: If mapping not found and raise_if_not_found is True.
        """
        platform = platform.lower()

        if platform not in self._mappings:
            if raise_if_not_found:
                raise SKUMappingNotFoundError(platform, platform_sku)
            return None

        master_sku = self._mappings[platform].get(platform_sku)

        if master_sku is None and raise_if_not_found:
            raise SKUMappingNotFoundError(platform, platform_sku)

        return master_sku

    def get_platform_skus(self, master_sku: str) -> list[tuple[str, str]]:
        """Get all platform SKUs for a master SKU.

        Args:
            master_sku: Unified master SKU.

        Returns:
            List of (platform, platform_sku) tuples.
        """
        return self._reverse_mappings.get(master_sku, [])

    def get_mapping_details(
        self,
        platform: str,
        platform_sku: str,
    ) -> SKUMapping | None:
        """Get detailed mapping information.

        Args:
            platform: Platform name.
            platform_sku: Platform-specific SKU.

        Returns:
            SKUMapping object or None if not found.
        """
        platform = platform.lower()
        key = f"{platform}:{platform_sku}"
        return self._mapping_details.get(key)

    def map_product(
        self,
        product: dict[str, Any],
        sku_field: str = "sku",
        platform_field: str = "platform",
    ) -> dict[str, Any]:
        """Add master_sku to a product record.

        Args:
            product: Product record to map.
            sku_field: Field name containing platform SKU.
            platform_field: Field name containing platform.

        Returns:
            Product with master_sku added (or None if unmapped).
        """
        platform = product.get(platform_field, "").lower()
        sku = product.get(sku_field)

        if not sku or not platform:
            return {**product, "master_sku": None, "is_mapped": False}

        master_sku = self.get_master_sku(platform, sku)

        return {
            **product,
            "master_sku": master_sku,
            "is_mapped": master_sku is not None,
        }

    def map_products(
        self,
        products: list[dict[str, Any]],
        sku_field: str = "sku",
        platform_field: str = "platform",
    ) -> list[dict[str, Any]]:
        """Add master_sku to multiple product records.

        Args:
            products: List of product records.
            sku_field: Field name containing platform SKU.
            platform_field: Field name containing platform.

        Returns:
            List of products with master_sku added.
        """
        return [
            self.map_product(p, sku_field, platform_field)
            for p in products
        ]

    def get_unmapped_skus(
        self,
        products: list[dict[str, Any]],
        sku_field: str = "sku",
        platform_field: str = "platform",
    ) -> list[dict[str, str]]:
        """Find SKUs that are not mapped.

        Args:
            products: List of product records.
            sku_field: Field name containing platform SKU.
            platform_field: Field name containing platform.

        Returns:
            List of unmapped SKUs with platform info.
        """
        unmapped = []
        seen: set[str] = set()

        for product in products:
            platform = product.get(platform_field, "").lower()
            sku = product.get(sku_field)

            if not sku or not platform:
                continue

            key = f"{platform}:{sku}"
            if key in seen:
                continue
            seen.add(key)

            if self.get_master_sku(platform, sku) is None:
                unmapped.append({
                    "platform": platform,
                    "sku": sku,
                    "name": product.get("name", ""),
                    "variation": product.get("variation", ""),
                })

        return unmapped

    def generate_unmapped_csv(
        self,
        products: list[dict[str, Any]],
        file_path: str | Path,
        sku_field: str = "sku",
        platform_field: str = "platform",
    ) -> int:
        """Generate CSV file with unmapped SKUs for manual mapping.

        Args:
            products: List of product records.
            file_path: Path to save CSV file.
            sku_field: Field name containing platform SKU.
            platform_field: Field name containing platform.

        Returns:
            Number of unmapped SKUs written.
        """
        unmapped = self.get_unmapped_skus(products, sku_field, platform_field)

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "master_sku",
                    "platform",
                    "platform_sku",
                    "product_name",
                    "variation",
                    "notes",
                ],
            )
            writer.writeheader()

            for item in unmapped:
                writer.writerow({
                    "master_sku": "",  # To be filled manually
                    "platform": item["platform"],
                    "platform_sku": item["sku"],
                    "product_name": item["name"],
                    "variation": item["variation"],
                    "notes": "",
                })

        self.logger.info(
            "Generated unmapped SKUs file",
            file=str(file_path),
            count=len(unmapped),
        )
        return len(unmapped)

    def get_stats(self) -> dict[str, Any]:
        """Get mapping statistics.

        Returns:
            Dictionary with mapping counts.
        """
        platform_counts = {
            platform: len(skus)
            for platform, skus in self._mappings.items()
        }

        return {
            "total_mappings": len(self._mapping_details),
            "unique_master_skus": len(self._reverse_mappings),
            "by_platform": platform_counts,
        }

    def __len__(self) -> int:
        """Return total number of mappings."""
        return len(self._mapping_details)

    def __contains__(self, key: tuple[str, str]) -> bool:
        """Check if mapping exists for (platform, sku) tuple."""
        platform, sku = key
        return self.get_master_sku(platform, sku) is not None
