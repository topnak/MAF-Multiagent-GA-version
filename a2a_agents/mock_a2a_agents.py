# ─────────────────────────────────────────────────────────────────────────────
# Mock A2A Agents
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementations of external agents that communicate via A2A protocol.
# These simulate real external systems for testing and development.
#
# Mock Agents:
# - PricingAgent: Provides pricing information
# - InventoryCheckAgent: Checks stock levels
# - FulfilmentAgent: Handles order fulfilment status
# ─────────────────────────────────────────────────────────────────────────────

import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from a2a_agents.a2a_client import A2AMessage, A2AResponse, A2AStatus
from a2a_agents.a2a_server import A2AHandler

# Configure module logger
logger = logging.getLogger(__name__)


class BaseA2AAgent(A2AHandler, ABC):
    """
    Base class for mock A2A agents.
    
    Provides common functionality for handling A2A messages
    and simulating agent behavior.
    """
    
    def __init__(self, agent_name: str):
        """Initialize the agent."""
        self._agent_name = agent_name
        self._request_count = 0
    
    @property
    def name(self) -> str:
        """Get agent name."""
        return self._agent_name
    
    def can_handle(self, message: A2AMessage) -> bool:
        """Check if message is for this agent."""
        return message.recipient_agent == self._agent_name
    
    async def handle(self, message: A2AMessage) -> A2AResponse:
        """Handle an incoming message."""
        self._request_count += 1
        
        logger.info(f"[{self._agent_name}] Processing message: {message.content[:50]}...")
        
        try:
            result = await self.process(message.content, message.context)
            
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.SUCCESS,
                content=result,
                metadata={
                    "processor": self._agent_name,
                    "request_count": self._request_count,
                },
            )
            
        except Exception as e:
            logger.error(f"[{self._agent_name}] Error: {e}")
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.ERROR,
                error=str(e),
            )
    
    @abstractmethod
    async def process(self, content: str, context: Optional[dict]) -> str:
        """Process the message content."""
        pass


class MockPricingAgent(BaseA2AAgent):
    """
    Mock Pricing Agent - Simulates a pricing service.
    
    Provides mock pricing information for products.
    In a real scenario, this would connect to a pricing engine.
    """
    
    # Mock pricing data
    MOCK_PRICES = {
        "paint": {"base_price": 24.99, "sale_price": 19.99, "currency": "USD"},
        "brush": {"base_price": 8.99, "sale_price": 6.99, "currency": "USD"},
        "roller": {"base_price": 12.99, "sale_price": 9.99, "currency": "USD"},
        "primer": {"base_price": 29.99, "sale_price": 24.99, "currency": "USD"},
        "tape": {"base_price": 4.99, "sale_price": 3.99, "currency": "USD"},
    }
    
    def __init__(self):
        super().__init__("PricingAgent")
        self._pricing_rules: dict[str, float] = {}  # Dynamic pricing adjustments
    
    async def process(self, content: str, context: Optional[dict]) -> str:
        """Process a pricing request."""
        content_lower = content.lower()
        
        # Check for bulk pricing request
        if "bulk" in content_lower or "wholesale" in content_lower:
            return self._get_bulk_pricing()
        
        # Check for specific product
        for product, prices in self.MOCK_PRICES.items():
            if product in content_lower:
                return self._format_price(product, prices)
        
        # Return all prices
        return self._get_all_prices()
    
    def _format_price(self, product: str, prices: dict) -> str:
        """Format a single product's pricing."""
        discount = round((1 - prices["sale_price"] / prices["base_price"]) * 100, 0)
        return (
            f"**{product.title()} Pricing**\n"
            f"- Regular Price: ${prices['base_price']:.2f} {prices['currency']}\n"
            f"- Sale Price: ${prices['sale_price']:.2f} {prices['currency']}\n"
            f"- Discount: {discount:.0f}% off\n"
            f"- Valid Until: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}"
        )
    
    def _get_all_prices(self) -> str:
        """Get all product prices."""
        lines = ["**Current Pricing**\n"]
        for product, prices in self.MOCK_PRICES.items():
            lines.append(
                f"- {product.title()}: ${prices['sale_price']:.2f} "
                f"(was ${prices['base_price']:.2f})"
            )
        return "\n".join(lines)
    
    def _get_bulk_pricing(self) -> str:
        """Get bulk pricing tiers."""
        return (
            "**Bulk Pricing Tiers**\n\n"
            "| Quantity | Discount |\n"
            "|----------|----------|\n"
            "| 10-49    | 10% off  |\n"
            "| 50-99    | 15% off  |\n"
            "| 100-499  | 20% off  |\n"
            "| 500+     | 25% off  |\n\n"
            "Contact your sales rep for custom pricing on large orders."
        )


class MockInventoryCheckAgent(BaseA2AAgent):
    """
    Mock Inventory Check Agent - Simulates inventory lookup.
    
    Provides mock inventory levels across locations.
    In a real scenario, this would connect to WMS or ERP.
    """
    
    # Mock inventory data
    MOCK_INVENTORY = {
        "SKU-PAINT-001": {
            "name": "Premium Interior Paint - White",
            "locations": {
                "DC-WEST": 250,
                "DC-EAST": 180,
                "DC-CENTRAL": 320,
            },
            "reorder_point": 100,
        },
        "SKU-PAINT-002": {
            "name": "Premium Interior Paint - Beige",
            "locations": {
                "DC-WEST": 45,
                "DC-EAST": 120,
                "DC-CENTRAL": 85,
            },
            "reorder_point": 100,
        },
        "SKU-BRUSH-001": {
            "name": "Professional Paint Brush Set",
            "locations": {
                "DC-WEST": 500,
                "DC-EAST": 350,
                "DC-CENTRAL": 420,
            },
            "reorder_point": 200,
        },
    }
    
    LOCATIONS = ["DC-WEST", "DC-EAST", "DC-CENTRAL"]
    
    def __init__(self):
        super().__init__("InventoryCheckAgent")
    
    async def process(self, content: str, context: Optional[dict]) -> str:
        """Process an inventory check request."""
        content_lower = content.lower()
        
        # Check for low stock alerts
        if "low stock" in content_lower or "alerts" in content_lower:
            return self._get_low_stock_alerts()
        
        # Check for specific SKU
        for sku in self.MOCK_INVENTORY.keys():
            if sku.lower() in content_lower:
                return self._get_sku_inventory(sku)
        
        # Check for location query
        for loc in self.LOCATIONS:
            if loc.lower() in content_lower:
                return self._get_location_inventory(loc)
        
        # Return summary
        return self._get_inventory_summary()
    
    def _get_sku_inventory(self, sku: str) -> str:
        """Get inventory for a specific SKU."""
        item = self.MOCK_INVENTORY.get(sku)
        if not item:
            return f"SKU {sku} not found in inventory system."
        
        total = sum(item["locations"].values())
        status = "✅ In Stock" if total > item["reorder_point"] else "⚠️ Low Stock"
        
        lines = [
            f"**{item['name']}** ({sku})\n",
            f"Status: {status}",
            f"Total Units: {total}",
            f"Reorder Point: {item['reorder_point']}\n",
            "**By Location:**",
        ]
        
        for loc, qty in item["locations"].items():
            lines.append(f"- {loc}: {qty} units")
        
        return "\n".join(lines)
    
    def _get_location_inventory(self, location: str) -> str:
        """Get all inventory at a location."""
        lines = [f"**Inventory at {location}**\n"]
        
        total = 0
        for sku, item in self.MOCK_INVENTORY.items():
            qty = item["locations"].get(location, 0)
            total += qty
            lines.append(f"- {item['name']}: {qty} units")
        
        lines.append(f"\n**Total Units: {total}**")
        return "\n".join(lines)
    
    def _get_low_stock_alerts(self) -> str:
        """Get items below reorder point."""
        alerts = []
        
        for sku, item in self.MOCK_INVENTORY.items():
            for loc, qty in item["locations"].items():
                if qty < item["reorder_point"] / 2:  # Below 50% of reorder point
                    alerts.append((sku, item["name"], loc, qty, item["reorder_point"]))
        
        if not alerts:
            return "✅ No low stock alerts at this time."
        
        lines = ["**⚠️ Low Stock Alerts**\n"]
        for sku, name, loc, qty, reorder in alerts:
            lines.append(f"- **{name}** at {loc}: {qty} units (reorder at {reorder})")
        
        return "\n".join(lines)
    
    def _get_inventory_summary(self) -> str:
        """Get overall inventory summary."""
        total = 0
        items = len(self.MOCK_INVENTORY)
        
        for item in self.MOCK_INVENTORY.values():
            total += sum(item["locations"].values())
        
        return (
            f"**Inventory Summary**\n\n"
            f"- Total SKUs: {items}\n"
            f"- Total Units: {total}\n"
            f"- Locations: {', '.join(self.LOCATIONS)}\n\n"
            "Use 'low stock alerts' to see items needing replenishment."
        )


class MockFulfilmentAgent(BaseA2AAgent):
    """
    Mock Fulfilment Agent - Simulates order fulfilment.
    
    Provides mock order tracking and fulfilment status.
    In a real scenario, this would connect to OMS/WMS.
    """
    
    # Mock order data
    MOCK_ORDERS = {
        "ORD-12345": {
            "status": "shipped",
            "carrier": "FedEx",
            "tracking": "FX123456789",
            "estimated_delivery": "2025-01-20",
            "items": ["Premium Paint x2", "Brush Set x1"],
        },
        "ORD-12346": {
            "status": "processing",
            "carrier": None,
            "tracking": None,
            "estimated_delivery": "2025-01-22",
            "items": ["Primer x3"],
        },
        "ORD-12347": {
            "status": "delivered",
            "carrier": "UPS",
            "tracking": "UPS987654321",
            "estimated_delivery": "2025-01-15",
            "items": ["Tape x10", "Drop Cloth x2"],
        },
    }
    
    def __init__(self):
        super().__init__("FulfilmentAgent")
    
    async def process(self, content: str, context: Optional[dict]) -> str:
        """Process a fulfilment request."""
        content_lower = content.lower()
        
        # Check for specific order
        for order_id in self.MOCK_ORDERS.keys():
            if order_id.lower() in content_lower:
                return self._get_order_status(order_id)
        
        # Check for status filter
        if "shipped" in content_lower:
            return self._get_orders_by_status("shipped")
        elif "processing" in content_lower or "pending" in content_lower:
            return self._get_orders_by_status("processing")
        elif "delivered" in content_lower:
            return self._get_orders_by_status("delivered")
        
        # Return all orders
        return self._get_all_orders()
    
    def _get_order_status(self, order_id: str) -> str:
        """Get status of a specific order."""
        order = self.MOCK_ORDERS.get(order_id)
        if not order:
            return f"Order {order_id} not found."
        
        status_icon = {
            "processing": "🔄",
            "shipped": "📦",
            "delivered": "✅",
        }.get(order["status"], "❓")
        
        lines = [
            f"**Order {order_id}**\n",
            f"Status: {status_icon} {order['status'].title()}",
            f"Estimated Delivery: {order['estimated_delivery']}",
        ]
        
        if order["carrier"]:
            lines.append(f"Carrier: {order['carrier']}")
        if order["tracking"]:
            lines.append(f"Tracking: {order['tracking']}")
        
        lines.append("\n**Items:**")
        for item in order["items"]:
            lines.append(f"- {item}")
        
        return "\n".join(lines)
    
    def _get_orders_by_status(self, status: str) -> str:
        """Get all orders with a specific status."""
        matching = [
            (oid, o) for oid, o in self.MOCK_ORDERS.items()
            if o["status"] == status
        ]
        
        if not matching:
            return f"No orders with status: {status}"
        
        lines = [f"**Orders - {status.title()}**\n"]
        for order_id, order in matching:
            lines.append(f"- {order_id}: Est. {order['estimated_delivery']}")
        
        return "\n".join(lines)
    
    def _get_all_orders(self) -> str:
        """Get summary of all orders."""
        status_counts = {}
        for order in self.MOCK_ORDERS.values():
            status_counts[order["status"]] = status_counts.get(order["status"], 0) + 1
        
        lines = ["**Fulfilment Summary**\n"]
        for status, count in status_counts.items():
            lines.append(f"- {status.title()}: {count} orders")
        
        lines.append(f"\n**Total Orders: {len(self.MOCK_ORDERS)}**")
        return "\n".join(lines)
