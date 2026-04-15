# ─────────────────────────────────────────────────────────────────────────────
# Localisation MCP Server (Mock)
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation for store localisation and regional data.
# ─────────────────────────────────────────────────────────────────────────────

import random

from .base_mcp_server import (
    BaseMCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    create_json_schema,
)


class LocalisationMCPServer(BaseMCPServer):
    """
    Mock Localisation MCP server for regional data.
    
    Provides:
    - Store location details
    - Regional pricing
    - Local market data
    - Competitor info
    """
    
    def __init__(self):
        super().__init__(
            name="localisation-mcp",
            version="1.0.0",
            description="Access store localisation and regional market data"
        )
    
    def _register_tools(self) -> None:
        """Register localisation MCP tools."""
        
        self.register_tool(MCPTool(
            name="get_store_details",
            description="Get detailed store information including location and facilities.",
            input_schema=create_json_schema(
                properties={
                    "store_id": {"type": "string", "description": "Store ID"},
                },
                required=["store_id"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_regional_pricing",
            description="Get regional pricing rules and adjustments.",
            input_schema=create_json_schema(
                properties={
                    "region": {"type": "string", "description": "Region or state code"},
                    "category": {"type": "string", "description": "Product category (optional)"},
                },
                required=["region"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_competitor_data",
            description="Get competitor store data for a location.",
            input_schema=create_json_schema(
                properties={
                    "store_id": {"type": "string", "description": "Store ID"},
                    "radius_km": {"type": "number", "description": "Search radius in km", "default": 10},
                },
                required=["store_id"]
            )
        ))
    
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        """Execute the requested tool."""
        
        if call.name == "get_store_details":
            return await self._get_store_details(call.arguments)
        elif call.name == "get_regional_pricing":
            return await self._get_regional_pricing(call.arguments)
        elif call.name == "get_competitor_data":
            return await self._get_competitor_data(call.arguments)
        else:
            return MCPToolResult.error(f"Unknown tool: {call.name}")
    
    async def _get_store_details(self, args: dict) -> MCPToolResult:
        """Get mock store details."""
        store_id = args.get("store_id", "STR-0001")
        
        return MCPToolResult.json_result({
            "store_id": store_id,
            "name": f"Store {store_id[-4:]}",
            "address": "123 Example Street, Melbourne VIC 3000",
            "phone": "+61 3 9999 8888",
            "coordinates": {"lat": -37.8136, "lng": 144.9631},
            "trading_hours": {
                "weekday": "6:00 AM - 9:00 PM",
                "saturday": "7:00 AM - 6:00 PM",
                "sunday": "9:00 AM - 5:00 PM",
            },
            "facilities": ["Trade Desk", "Tool Hire", "Paint Mixing", "Timber Cutting", "Drive Through"],
            "store_format": "Warehouse",
            "sqm": random.randint(10000, 25000),
            "staff_count": random.randint(50, 150),
            "catchment_population": random.randint(100000, 500000),
        })
    
    async def _get_regional_pricing(self, args: dict) -> MCPToolResult:
        """Get mock regional pricing."""
        region = args.get("region", "VIC")
        category = args.get("category")
        
        pricing_rules = [
            {"category": "Paint", "adjustment_pct": round(random.uniform(-5, 5), 1)},
            {"category": "Tools", "adjustment_pct": round(random.uniform(-3, 3), 1)},
            {"category": "Garden", "adjustment_pct": round(random.uniform(-8, 8), 1)},
            {"category": "Building Materials", "adjustment_pct": round(random.uniform(-10, 10), 1)},
        ]
        
        if category:
            pricing_rules = [p for p in pricing_rules if p["category"] == category]
        
        return MCPToolResult.json_result({
            "region": region,
            "currency": "AUD",
            "tax_rate_pct": 10.0,
            "pricing_rules": pricing_rules,
            "freight_zone": random.choice(["Metro", "Regional", "Remote"]),
        })
    
    async def _get_competitor_data(self, args: dict) -> MCPToolResult:
        """Get mock competitor data."""
        store_id = args.get("store_id")
        radius_km = args.get("radius_km", 10)
        
        competitors = ["Competitor A", "Competitor B", "Competitor C"]
        results = []
        
        for comp in competitors[:random.randint(1, 3)]:
            results.append({
                "name": comp,
                "distance_km": round(random.uniform(1, radius_km), 1),
                "store_type": random.choice(["Hardware", "Trade", "Big Box"]),
                "estimated_sqm": random.randint(5000, 20000),
                "price_position": random.choice(["Below", "Comparable", "Above"]),
            })
        
        return MCPToolResult.json_result({
            "store_id": store_id,
            "radius_km": radius_km,
            "competitor_count": len(results),
            "competitors": results,
        })
