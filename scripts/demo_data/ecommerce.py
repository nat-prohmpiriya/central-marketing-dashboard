"""
E-commerce Demo Data Generator (DEMO-002)

Generates realistic e-commerce orders for Shopee, Lazada, and TikTok Shop.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from .generator import (
    METRIC_RANGES,
    PLATFORMS,
    THAI_PRODUCT_CATEGORIES,
    THAI_SHOP_NAMES,
    BaseGenerator,
    GeneratorConfig,
    create_default_config,
)


class EcommerceGenerator(BaseGenerator):
    """Generate e-commerce orders and products."""

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.shops = self._create_shops()
        self.products = self._create_products()

    def _create_shops(self) -> list[dict]:
        """Create shop data."""
        shops = []
        for i, platform in enumerate(PLATFORMS["ecommerce"]):
            for j, name in enumerate(THAI_SHOP_NAMES[:3]):  # 3 shops per platform
                shop_id = f"{platform.upper()[:3]}-SHOP-{i*10+j+1:03d}"
                shops.append(
                    {
                        "shop_id": shop_id,
                        "shop_name": f"{name} ({platform.capitalize()})",
                        "platform": platform,
                        "created_at": self.config.start_date - timedelta(days=365),
                        "status": "active",
                    }
                )
        return shops

    def _create_products(self) -> list[dict]:
        """Create product catalog."""
        products = []
        product_id = 1

        for category in THAI_PRODUCT_CATEGORIES:
            # 10 products per category
            for i in range(10):
                base_price = np.random.uniform(100, 3000)
                sku = f"SKU-{product_id:05d}"

                # Create product for each platform
                for platform in PLATFORMS["ecommerce"]:
                    platform_sku = f"{platform.upper()[:3]}-{sku}"
                    products.append(
                        {
                            "product_id": f"PROD-{product_id:05d}-{platform[:3].upper()}",
                            "sku": platform_sku,
                            "master_sku": sku,
                            "name": f"{category} รุ่น {i+1}",
                            "category": category,
                            "platform": platform,
                            "price": round(base_price * np.random.uniform(0.9, 1.1), 2),
                            "cost": round(base_price * 0.6, 2),
                            "stock": np.random.randint(10, 500),
                            "status": "active",
                        }
                    )
                product_id += 1

        return products

    def generate(self) -> dict[str, list[dict[str, Any]]]:
        """Generate all e-commerce data."""
        return {
            "shops": self.shops,
            "products": self.products,
            "orders": self._generate_orders(),
            "order_items": self._generate_order_items(),
        }

    def _generate_orders(self) -> list[dict]:
        """Generate order data."""
        orders = []
        order_items_map = {}  # Will store items for each order

        # Calculate days in range
        days = (self.config.end_date - self.config.start_date).days

        for day_offset in range(days):
            current_date = self.config.start_date + timedelta(days=day_offset)

            for shop in self.shops:
                # Base orders per day with seasonality
                base_orders = METRIC_RANGES["orders_per_day"]["mean"] * self.config.scale
                daily_orders = int(self._apply_seasonality(base_orders, current_date))

                # Reduce for smaller shops
                daily_orders = max(5, daily_orders // len(self.shops))

                for _ in range(daily_orders):
                    order_id = f"ORD-{uuid.uuid4().hex[:12].upper()}"
                    order_time = self._random_date(
                        current_date,
                        current_date + timedelta(hours=23, minutes=59),
                    )

                    # Generate order value
                    base_value = METRIC_RANGES["order_value"]["mean"]
                    order_value = max(
                        METRIC_RANGES["order_value"]["min"],
                        np.random.normal(base_value, base_value * 0.5),
                    )

                    # Status distribution
                    status = self._weighted_choice(
                        ["completed", "shipped", "pending", "cancelled", "refunded"],
                        [0.7, 0.15, 0.05, 0.05, 0.05],
                    )

                    # Payment method
                    payment = self._weighted_choice(
                        ["credit_card", "bank_transfer", "cod", "wallet", "installment"],
                        [0.3, 0.25, 0.2, 0.15, 0.1],
                    )

                    orders.append(
                        {
                            "order_id": order_id,
                            "shop_id": shop["shop_id"],
                            "platform": shop["platform"],
                            "customer_id": f"CUST-{uuid.uuid4().hex[:8].upper()}",
                            "order_date": order_time.isoformat(),
                            "status": status,
                            "payment_method": payment,
                            "subtotal": round(order_value, 2),
                            "shipping_fee": round(np.random.uniform(0, 50), 2),
                            "discount": round(order_value * np.random.uniform(0, 0.15), 2),
                            "total": round(order_value * np.random.uniform(0.9, 1.05), 2),
                            "currency": self.config.currency,
                            "shipping_province": self._weighted_choice(
                                ["กรุงเทพ", "นนทบุรี", "ปทุมธานี", "ชลบุรี", "เชียงใหม่", "ภูเก็ต", "ขอนแก่น", "อื่นๆ"],
                                [0.35, 0.1, 0.1, 0.08, 0.08, 0.05, 0.05, 0.19],
                            ),
                        }
                    )

                    # Store for order items generation
                    order_items_map[order_id] = {
                        "shop_id": shop["shop_id"],
                        "platform": shop["platform"],
                        "order_value": order_value,
                    }

        self._order_items_map = order_items_map
        return orders

    def _generate_order_items(self) -> list[dict]:
        """Generate order items."""
        items = []

        for order_id, order_info in self._order_items_map.items():
            # Filter products by platform
            platform_products = [
                p for p in self.products if p["platform"] == order_info["platform"]
            ]

            # Number of items in order
            num_items = max(
                1,
                int(np.random.normal(METRIC_RANGES["items_per_order"]["mean"], 1)),
            )
            num_items = min(num_items, 5)

            # Select random products
            selected_products = np.random.choice(
                platform_products,
                size=min(num_items, len(platform_products)),
                replace=False,
            )

            remaining_value = order_info["order_value"]
            for i, product in enumerate(selected_products):
                # Distribute order value among items
                if i == len(selected_products) - 1:
                    item_total = remaining_value
                else:
                    item_total = remaining_value * np.random.uniform(0.2, 0.6)
                    remaining_value -= item_total

                quantity = max(1, int(item_total / product["price"]))
                unit_price = product["price"]

                items.append(
                    {
                        "order_item_id": f"ITEM-{uuid.uuid4().hex[:10].upper()}",
                        "order_id": order_id,
                        "product_id": product["product_id"],
                        "sku": product["sku"],
                        "product_name": product["name"],
                        "quantity": quantity,
                        "unit_price": round(unit_price, 2),
                        "subtotal": round(unit_price * quantity, 2),
                        "discount": round(unit_price * quantity * np.random.uniform(0, 0.1), 2),
                    }
                )

        return items

    def get_daily_summary(self) -> list[dict]:
        """Generate daily summary for mart layer."""
        orders = self._generate_orders() if not hasattr(self, "_orders") else self._orders

        # Group by date, platform, shop
        daily_data = {}
        for order in orders:
            date = order["order_date"][:10]
            key = (date, order["platform"], order["shop_id"])

            if key not in daily_data:
                daily_data[key] = {
                    "date": date,
                    "platform": order["platform"],
                    "shop_id": order["shop_id"],
                    "orders": 0,
                    "revenue": 0,
                    "items_sold": 0,
                }

            daily_data[key]["orders"] += 1
            daily_data[key]["revenue"] += order["total"]

        return list(daily_data.values())


def generate_ecommerce_data(days_back: int = 90, seed: int = 42) -> dict:
    """Main function to generate e-commerce demo data."""
    config = create_default_config(days_back=days_back)
    config.seed = seed

    generator = EcommerceGenerator(config)
    return generator.generate()


if __name__ == "__main__":
    data = generate_ecommerce_data(days_back=90)
    print(f"Generated {len(data['shops'])} shops")
    print(f"Generated {len(data['products'])} products")
    print(f"Generated {len(data['orders'])} orders")
    print(f"Generated {len(data['order_items'])} order items")
