"""
Shopify Admin API & Local SQLite Orders Adapter
Connects to live Shopify Admin REST/GraphQL if token exists;
otherwise falls back to SQLite table `p03_orders` and truthfully reports sandbox mode.
"""
import json
import logging
from typing import Optional, Dict, Any, List
import httpx
from core.config import settings
from core.db import DatabaseSession

logger = logging.getLogger("p03_support.shopify")

DEFAULT_SEED_ORDERS = [
    {
        "id": "#1042",
        "customer_name": "Hamza Tariq",
        "email": "hamza.tariq@gmail.com",
        "phone": "+923001234567",
        "items": json.dumps([{"title": "Noise-Cancelling Wireless Headphones Pro", "qty": 1, "price": 85.00}]),
        "total_usd": 85.00,
        "status": "In Transit",
        "courier": "TCS Express",
        "tracking_id": "TCS-9921481"
    },
    {
        "id": "#1043",
        "customer_name": "Ayesha Khan",
        "email": "ayesha.k@yahoo.com",
        "phone": "+923219876543",
        "items": json.dumps([{"title": "Ceramic Pour-Over Coffee Dripper Set", "qty": 1, "price": 42.50}]),
        "total_usd": 42.50,
        "status": "Delivered",
        "courier": "Leopard Courier",
        "tracking_id": "LEO-5510294"
    },
    {
        "id": "#1044",
        "customer_name": "Zaid Ali",
        "email": "zaid.ali@hotmail.com",
        "phone": "+923334567890",
        "items": json.dumps([{"title": "Mechanical RGB Gaming Keyboard (Blue Switch)", "qty": 1, "price": 110.00}]),
        "total_usd": 110.00,
        "status": "Processing in Warehouse",
        "courier": "DHL Express",
        "tracking_id": "DHL-1082937"
    }
]

class ShopifyAdapter:
    def __init__(self):
        self.access_token = settings.SHOPIFY_ADMIN_ACCESS_TOKEN
        self.store_url = settings.SHOPIFY_SHOP_URL
        self.live_mode = getattr(settings, "SHOPIFY_LIVE_MODE", False)
        self._seed_orders_if_needed()

    def _seed_orders_if_needed(self):
        """Ensures SQLite has realistic sandbox orders with tenant partitioning."""
        db = DatabaseSession()
        try:
            count = db.fetchone("SELECT COUNT(*) as cnt FROM p03_orders")
            if count and count["cnt"] == 0:
                for o in DEFAULT_SEED_ORDERS:
                    db.execute(
                        """
                        INSERT INTO p03_orders 
                        (id, tenant_id, customer_name, email, phone, items, total_usd, status, courier, tracking_id, created_at)
                        VALUES (?, 'tenant_default', ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        """,
                        (
                            o["id"], o["customer_name"], o["email"], o["phone"],
                            o["items"], o["total_usd"], o["status"], o["courier"], o["tracking_id"]
                        )
                    )
                db.commit()
            else:
                # Ensure existing seed orders have tenant_id set
                db.execute("UPDATE p03_orders SET tenant_id = 'tenant_default' WHERE tenant_id IS NULL OR tenant_id = ''")
                db.commit()
        except Exception as e:
            if "no such table" not in str(e).lower():
                logger.warning(f"Could not seed orders: {e}")
        finally:
            db.close()

    def get_order_by_id(self, order_id: str, tenant_id: str = "tenant_default") -> Optional[Dict[str, Any]]:
        """Finds order by ID scoped by tenant."""
        normalized = order_id.strip()
        if not normalized.startswith("#"):
            normalized = f"#{normalized}"

        # If live Shopify token configured and live mode enabled:
        if self.live_mode and self.access_token and self.store_url:
            try:
                numeric_id = normalized.replace("#", "")
                url = f"https://{self.store_url}/admin/api/2024-01/orders/{numeric_id}.json"
                headers = {"X-Shopify-Access-Token": self.access_token}
                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        order = resp.json().get("order", {})
                        return {
                            "id": f"#{order.get('order_number')}",
                            "customer_name": f"{order.get('customer', {}).get('first_name', '')} {order.get('customer', {}).get('last_name', '')}".strip(),
                            "status": order.get("fulfillment_status", "unfulfilled").capitalize(),
                            "total_usd": float(order.get("total_price", 0.0)),
                            "courier": "Shopify Fulfillment",
                            "tracking_id": order.get("fulfillments", [{}])[0].get("tracking_number", "N/A"),
                            "source": "live_shopify",
                            "tenant_id": tenant_id
                        }
            except Exception as e:
                logger.error(f"Live Shopify query failed: {e}")

        # Persistent SQLite Multi-Tenant Sandbox
        db = DatabaseSession()
        try:
            row = db.fetchone(
                "SELECT * FROM p03_orders WHERE id = ? AND tenant_id = ?",
                (normalized, tenant_id)
            )
            if row:
                res = dict(row)
                res["source"] = "sqlite_sandbox"
                if isinstance(res.get("items"), str):
                    try:
                        res["items"] = json.loads(res["items"])
                    except Exception:
                        pass
                return res
            return None
        finally:
            db.close()

    def list_recent_orders(self, limit: int = 10, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        db = DatabaseSession()
        try:
            if tenant_id:
                rows = db.fetchall(
                    "SELECT * FROM p03_orders WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
                    (tenant_id, limit)
                )
            else:
                rows = db.fetchall("SELECT * FROM p03_orders ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in rows]
        finally:
            db.close()

    def ingest_order(self, order_dict: Dict[str, Any], tenant_id: str = "tenant_default") -> Dict[str, Any]:
        """Ingests a new order into the multi-tenant store ledger."""
        oid = order_dict["id"].strip()
        if not oid.startswith("#"):
            oid = f"#{oid}"
        items_str = json.dumps(order_dict.get("items", [])) if not isinstance(order_dict.get("items"), str) else order_dict["items"]
        
        db = DatabaseSession()
        try:
            db.execute(
                """
                INSERT OR REPLACE INTO p03_orders
                (id, tenant_id, customer_name, email, phone, items, total_usd, status, courier, tracking_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    oid,
                    tenant_id,
                    order_dict.get("customer_name", "Customer"),
                    order_dict.get("email"),
                    order_dict.get("phone"),
                    items_str,
                    float(order_dict.get("total_usd", 0.0)),
                    order_dict.get("status", "In Transit"),
                    order_dict.get("courier", "TCS Express"),
                    order_dict.get("tracking_id", "TRK-000000")
                )
            )
            db.commit()
            return {"id": oid, "tenant_id": tenant_id, "status": "INGESTED"}
        finally:
            db.close()

shopify_adapter = ShopifyAdapter()
