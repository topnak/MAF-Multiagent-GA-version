# ─────────────────────────────────────────────────────────────────────────────
# Snowflake MCP Server (Mock)
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation of Snowflake data warehouse access via MCP.
# Provides simulated retail/merchandising data for POC testing.
# ─────────────────────────────────────────────────────────────────────────────

import json
import random
from datetime import datetime, timedelta

from .base_mcp_server import (
    BaseMCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    create_json_schema,
)


class SnowflakeMCPServer(BaseMCPServer):
    """
    Mock Snowflake MCP server for retail data access.
    
    Provides simulated access to:
    - Sales data
    - Inventory data
    - Store performance
    - Product analytics
    
    In production, this would connect to actual Snowflake and execute queries.
    """
    
    def __init__(self):
        super().__init__(
            name="snowflake-mcp",
            version="1.0.0",
            description="Access retail data warehouse via Snowflake"
        )
        
        # Mock data stores
        self._mock_stores = self._generate_mock_stores()
        self._mock_products = self._generate_mock_products()
    
    def _register_tools(self) -> None:
        """Register Snowflake MCP tools."""
        
        # Execute SQL query tool
        self.register_tool(MCPTool(
            name="execute_query",
            description="Execute a SQL query against the Snowflake data warehouse. Returns tabular results.",
            input_schema=create_json_schema(
                properties={
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute. Use standard SQL syntax."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of rows to return",
                        "default": 100
                    },
                },
                required=["query"]
            )
        ))
        
        # Get sales data tool
        self.register_tool(MCPTool(
            name="get_sales_data",
            description="Get sales performance data for stores, categories, or products.",
            input_schema=create_json_schema(
                properties={
                    "store_id": {
                        "type": "string",
                        "description": "Store ID (optional, omit for all stores)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category (optional)"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)"
                    },
                },
                required=[]
            )
        ))
        
        # Get inventory data tool
        self.register_tool(MCPTool(
            name="get_inventory",
            description="Get current inventory levels by store and product.",
            input_schema=create_json_schema(
                properties={
                    "store_id": {
                        "type": "string",
                        "description": "Store ID (optional)"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "Product ID (optional)"
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category (optional)"
                    },
                    "low_stock_only": {
                        "type": "boolean",
                        "description": "Only return items below reorder point",
                        "default": False
                    },
                },
                required=[]
            )
        ))
        
        # Get store performance tool
        self.register_tool(MCPTool(
            name="get_store_performance",
            description="Get store performance metrics including sales, traffic, conversion.",
            input_schema=create_json_schema(
                properties={
                    "store_id": {
                        "type": "string",
                        "description": "Store ID (optional for all stores)"
                    },
                    "metric": {
                        "type": "string",
                        "description": "Metric to retrieve: sales, traffic, conversion, basket_size",
                        "enum": ["sales", "traffic", "conversion", "basket_size", "all"]
                    },
                    "period": {
                        "type": "string",
                        "description": "Time period: today, week, month, quarter, year",
                        "default": "month"
                    },
                },
                required=["metric"]
            )
        ))
    
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        """Execute the requested Snowflake tool."""
        
        if call.name == "execute_query":
            return await self._execute_query(call.arguments)
        elif call.name == "get_sales_data":
            return await self._get_sales_data(call.arguments)
        elif call.name == "get_inventory":
            return await self._get_inventory(call.arguments)
        elif call.name == "get_store_performance":
            return await self._get_store_performance(call.arguments)
        else:
            return MCPToolResult.error(f"Unknown tool: {call.name}")
    
    async def _execute_query(self, args: dict) -> MCPToolResult:
        """Execute a mock SQL query."""
        query = args.get("query", "").lower()
        limit = args.get("limit", 100)
        
        # Parse simple queries and return mock data
        if "select" in query:
            if "sales" in query:
                return await self._get_sales_data({})
            elif "inventory" in query or "stock" in query:
                return await self._get_inventory({})
            elif "store" in query:
                return await self._get_store_performance({"metric": "all"})
        
        # Default response
        return MCPToolResult.json_result({
            "query": args.get("query"),
            "rows_affected": 0,
            "message": "Query executed successfully (mock)",
            "columns": ["id", "name", "value"],
            "data": [
                [1, "Sample", 100],
                [2, "Data", 200],
            ]
        })
    
    async def _get_sales_data(self, args: dict) -> MCPToolResult:
        """Get mock sales data."""
        store_id = args.get("store_id")
        category = args.get("category")
        
        # Generate mock sales data
        sales_data = []
        categories = ["Paint", "Tools", "Garden", "Electrical", "Plumbing", "Building Materials"]
        
        if category:
            categories = [category]
        
        stores = self._mock_stores if not store_id else [s for s in self._mock_stores if s["store_id"] == store_id]
        
        for store in stores[:5]:  # Limit stores
            for cat in categories:
                sales_data.append({
                    "store_id": store["store_id"],
                    "store_name": store["name"],
                    "category": cat,
                    "total_sales": round(random.uniform(50000, 500000), 2),
                    "units_sold": random.randint(500, 5000),
                    "gross_margin_pct": round(random.uniform(25, 45), 1),
                    "yoy_growth_pct": round(random.uniform(-5, 15), 1),
                    "period": "Last 30 days",
                })
        
        return MCPToolResult.json_result({
            "query_type": "sales_data",
            "record_count": len(sales_data),
            "data": sales_data,
        })
    
    async def _get_inventory(self, args: dict) -> MCPToolResult:
        """Get mock inventory data."""
        store_id = args.get("store_id")
        low_stock_only = args.get("low_stock_only", False)
        category = args.get("category")
        
        inventory_data = []
        
        products = self._mock_products
        if category:
            products = [p for p in products if p["category"] == category]
        
        stores = self._mock_stores if not store_id else [s for s in self._mock_stores if s["store_id"] == store_id]
        
        for store in stores[:3]:
            for product in products[:10]:
                stock = random.randint(0, 200)
                reorder_point = 50
                
                if low_stock_only and stock >= reorder_point:
                    continue
                
                inventory_data.append({
                    "store_id": store["store_id"],
                    "store_name": store["name"],
                    "product_id": product["product_id"],
                    "product_name": product["name"],
                    "category": product["category"],
                    "current_stock": stock,
                    "reorder_point": reorder_point,
                    "stock_status": "Low" if stock < reorder_point else "OK",
                    "days_of_cover": round(stock / max(product["daily_sales"], 1), 1),
                    "last_restock_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                })
        
        return MCPToolResult.json_result({
            "query_type": "inventory",
            "record_count": len(inventory_data),
            "low_stock_count": len([i for i in inventory_data if i["stock_status"] == "Low"]),
            "data": inventory_data,
        })
    
    async def _get_store_performance(self, args: dict) -> MCPToolResult:
        """Get mock store performance metrics."""
        store_id = args.get("store_id")
        metric = args.get("metric", "all")
        period = args.get("period", "month")
        
        stores = self._mock_stores if not store_id else [s for s in self._mock_stores if s["store_id"] == store_id]
        
        performance_data = []
        for store in stores[:10]:
            data = {
                "store_id": store["store_id"],
                "store_name": store["name"],
                "state": store["state"],
                "period": period,
            }
            
            if metric in ["sales", "all"]:
                data["total_sales"] = round(random.uniform(500000, 2000000), 2)
                data["sales_vs_target_pct"] = round(random.uniform(90, 115), 1)
            
            if metric in ["traffic", "all"]:
                data["customer_count"] = random.randint(10000, 50000)
                data["traffic_vs_last_year_pct"] = round(random.uniform(-10, 20), 1)
            
            if metric in ["conversion", "all"]:
                data["conversion_rate_pct"] = round(random.uniform(20, 40), 1)
            
            if metric in ["basket_size", "all"]:
                data["avg_basket_size"] = round(random.uniform(45, 120), 2)
                data["items_per_transaction"] = round(random.uniform(3, 8), 1)
            
            performance_data.append(data)
        
        return MCPToolResult.json_result({
            "query_type": "store_performance",
            "metric": metric,
            "period": period,
            "record_count": len(performance_data),
            "data": performance_data,
        })
    
    def _generate_mock_stores(self) -> list[dict]:
        """Generate mock store data."""
        states = ["VIC", "NSW", "QLD", "WA", "SA", "TAS", "NT", "ACT"]
        store_types = ["Warehouse", "Trade Centre", "Small Format"]
        
        stores = []
        for i in range(1, 21):
            stores.append({
                "store_id": f"STR-{i:04d}",
                "name": f"Store {random.choice(['North', 'South', 'East', 'West', 'Central'])} {random.choice(['Melbourne', 'Sydney', 'Brisbane', 'Perth', 'Adelaide'])} {i}",
                "state": random.choice(states),
                "store_type": random.choice(store_types),
                "sqm": random.randint(5000, 20000),
            })
        return stores
    
    def _generate_mock_products(self) -> list[dict]:
        """Generate mock product data."""
        categories = {
            "Paint": ["Interior Paint", "Exterior Paint", "Paint Brushes", "Rollers", "Drop Cloths"],
            "Tools": ["Power Drill", "Hammer", "Screwdriver Set", "Tape Measure", "Level"],
            "Garden": ["Lawn Mower", "Garden Hose", "Shovel", "Rake", "Fertilizer"],
            "Electrical": ["LED Bulbs", "Power Strip", "Extension Cord", "Wall Socket", "Light Switch"],
            "Plumbing": ["Pipe Fittings", "Tap Set", "Toilet Seat", "Drain Cleaner", "Plunger"],
        }
        
        products = []
        for category, items in categories.items():
            for item in items:
                products.append({
                    "product_id": f"PRD-{len(products)+1:05d}",
                    "name": item,
                    "category": category,
                    "price": round(random.uniform(5, 500), 2),
                    "daily_sales": random.randint(1, 50),
                })
        return products
