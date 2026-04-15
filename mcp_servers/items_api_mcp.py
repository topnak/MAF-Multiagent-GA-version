# ─────────────────────────────────────────────────────────────────────────────
# Items API MCP Server (Mock)
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation for product catalog and items data.
# ─────────────────────────────────────────────────────────────────────────────

import random

from .base_mcp_server import (
    BaseMCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    create_json_schema,
)


class ItemsAPIMCPServer(BaseMCPServer):
    """Mock Items API MCP server for product catalog access."""
    
    def __init__(self):
        super().__init__(
            name="items-api-mcp",
            version="1.0.0",
            description="Access product catalog and item details"
        )
        self._products = self._generate_products()
    
    def _register_tools(self) -> None:
        self.register_tool(MCPTool(
            name="search_products",
            description="Search products by keyword, category, or attributes.",
            input_schema=create_json_schema(
                properties={
                    "query": {"type": "string", "description": "Search query"},
                    "category": {"type": "string", "description": "Category filter"},
                    "min_price": {"type": "number", "description": "Minimum price"},
                    "max_price": {"type": "number", "description": "Maximum price"},
                    "limit": {"type": "integer", "description": "Max results", "default": 20},
                },
                required=[]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_product_details",
            description="Get detailed product information by product ID.",
            input_schema=create_json_schema(
                properties={
                    "product_id": {"type": "string", "description": "Product ID"},
                },
                required=["product_id"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_category_hierarchy",
            description="Get product category hierarchy and structure.",
            input_schema=create_json_schema(
                properties={
                    "parent_category": {"type": "string", "description": "Parent category (optional)"},
                },
                required=[]
            )
        ))
    
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        if call.name == "search_products":
            return await self._search_products(call.arguments)
        elif call.name == "get_product_details":
            return await self._get_product_details(call.arguments)
        elif call.name == "get_category_hierarchy":
            return await self._get_category_hierarchy(call.arguments)
        return MCPToolResult.error(f"Unknown tool: {call.name}")
    
    async def _search_products(self, args: dict) -> MCPToolResult:
        query = args.get("query", "").lower()
        category = args.get("category")
        min_price = args.get("min_price", 0)
        max_price = args.get("max_price", 99999)
        limit = args.get("limit", 20)
        
        results = []
        for p in self._products:
            if category and p["category"] != category:
                continue
            if query and query not in p["name"].lower():
                continue
            if not (min_price <= p["price"] <= max_price):
                continue
            results.append(p)
            if len(results) >= limit:
                break
        
        return MCPToolResult.json_result({
            "query": query,
            "result_count": len(results),
            "products": results,
        })
    
    async def _get_product_details(self, args: dict) -> MCPToolResult:
        product_id = args.get("product_id")
        
        product = next((p for p in self._products if p["product_id"] == product_id), None)
        if not product:
            return MCPToolResult.error(f"Product not found: {product_id}")
        
        # Add extra details
        detailed = {
            **product,
            "description": f"High quality {product['name']} for professional and DIY use.",
            "brand": random.choice(["Brand A", "Brand B", "Brand C", "House Brand"]),
            "supplier": f"Supplier-{random.randint(1,10):02d}",
            "dimensions": {"length": 30, "width": 20, "height": 15, "weight_kg": 2.5},
            "warranty_months": random.choice([12, 24, 36, 60]),
            "in_stock": random.choice([True, True, True, False]),
            "reviews": {"avg_rating": round(random.uniform(3.5, 5.0), 1), "count": random.randint(10, 500)},
        }
        
        return MCPToolResult.json_result(detailed)
    
    async def _get_category_hierarchy(self, args: dict) -> MCPToolResult:
        hierarchy = {
            "Paint": ["Interior Paint", "Exterior Paint", "Specialty Paint", "Paint Accessories"],
            "Tools": ["Power Tools", "Hand Tools", "Measuring", "Safety Equipment"],
            "Garden": ["Plants", "Garden Tools", "Outdoor Furniture", "Irrigation"],
            "Electrical": ["Lighting", "Wiring", "Switches & Sockets", "Smart Home"],
            "Plumbing": ["Pipes & Fittings", "Taps & Mixers", "Bathroom", "Kitchen"],
            "Building Materials": ["Timber", "Concrete", "Roofing", "Insulation"],
        }
        
        parent = args.get("parent_category")
        if parent and parent in hierarchy:
            return MCPToolResult.json_result({
                "parent": parent,
                "subcategories": hierarchy[parent],
            })
        
        return MCPToolResult.json_result({
            "categories": list(hierarchy.keys()),
            "hierarchy": hierarchy,
        })
    
    def _generate_products(self) -> list[dict]:
        products = []
        items = [
            ("Interior Paint 4L", "Paint", 65), ("Exterior Paint 4L", "Paint", 85),
            ("Cordless Drill", "Tools", 189), ("Hammer", "Tools", 35),
            ("Garden Hose 30m", "Garden", 45), ("Lawn Mower", "Garden", 399),
            ("LED Bulb Pack", "Electrical", 25), ("Power Board", "Electrical", 35),
            ("Tap Mixer", "Plumbing", 120), ("Pipe Wrench", "Plumbing", 55),
        ]
        for i, (name, cat, price) in enumerate(items):
            products.append({
                "product_id": f"PRD-{i+1:05d}",
                "name": name,
                "category": cat,
                "price": price + round(random.uniform(-10, 10), 2),
                "sku": f"SKU{i+1:06d}",
            })
        return products
