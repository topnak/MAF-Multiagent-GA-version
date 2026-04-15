# ─────────────────────────────────────────────────────────────────────────────
# Personalisation MCP Server (Mock)
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation for customer personalisation data access.
# ─────────────────────────────────────────────────────────────────────────────

import random

from .base_mcp_server import (
    BaseMCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    create_json_schema,
)


class PersonalisationMCPServer(BaseMCPServer):
    """
    Mock Personalisation MCP server for customer data access.
    
    Provides simulated access to:
    - Customer profiles
    - Purchase history
    - Preferences
    - Recommendations
    """
    
    def __init__(self):
        super().__init__(
            name="personalisation-mcp",
            version="1.0.0",
            description="Access customer personalisation and profile data"
        )
    
    def _register_tools(self) -> None:
        """Register personalisation MCP tools."""
        
        self.register_tool(MCPTool(
            name="get_customer_profile",
            description="Get customer profile including demographics, preferences, and loyalty status.",
            input_schema=create_json_schema(
                properties={
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID to look up"
                    },
                    "include_history": {
                        "type": "boolean",
                        "description": "Include purchase history summary",
                        "default": False
                    },
                },
                required=["customer_id"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_recommendations",
            description="Get personalized product recommendations for a customer.",
            input_schema=create_json_schema(
                properties={
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID"
                    },
                    "category": {
                        "type": "string",
                        "description": "Product category filter (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum recommendations to return",
                        "default": 5
                    },
                },
                required=["customer_id"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_customer_segments",
            description="Get customer segment membership and characteristics.",
            input_schema=create_json_schema(
                properties={
                    "customer_id": {
                        "type": "string",
                        "description": "Customer ID (optional, for single customer)"
                    },
                    "segment_type": {
                        "type": "string",
                        "description": "Segment type: behavioral, demographic, value",
                        "enum": ["behavioral", "demographic", "value", "all"]
                    },
                },
                required=[]
            )
        ))
    
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        """Execute the requested personalisation tool."""
        
        if call.name == "get_customer_profile":
            return await self._get_customer_profile(call.arguments)
        elif call.name == "get_recommendations":
            return await self._get_recommendations(call.arguments)
        elif call.name == "get_customer_segments":
            return await self._get_customer_segments(call.arguments)
        else:
            return MCPToolResult.error(f"Unknown tool: {call.name}")
    
    async def _get_customer_profile(self, args: dict) -> MCPToolResult:
        """Get mock customer profile."""
        customer_id = args.get("customer_id", "CUST-001")
        include_history = args.get("include_history", False)
        
        loyalty_tiers = ["Bronze", "Silver", "Gold", "Platinum"]
        preferences = ["DIY Projects", "Home Renovation", "Gardening", "Professional Trade"]
        
        profile = {
            "customer_id": customer_id,
            "name": f"Customer {customer_id[-3:]}",
            "email": f"customer{customer_id[-3:]}@example.com",
            "member_since": "2021-03-15",
            "loyalty_tier": random.choice(loyalty_tiers),
            "loyalty_points": random.randint(1000, 50000),
            "lifetime_value": round(random.uniform(500, 25000), 2),
            "preferred_store": f"STR-{random.randint(1,20):04d}",
            "communication_preferences": {
                "email": True,
                "sms": random.choice([True, False]),
                "push": random.choice([True, False]),
            },
            "interests": random.sample(preferences, k=random.randint(1, 3)),
        }
        
        if include_history:
            profile["purchase_history_summary"] = {
                "total_orders": random.randint(5, 100),
                "avg_order_value": round(random.uniform(50, 300), 2),
                "last_purchase_date": "2024-01-10",
                "top_categories": random.sample(["Paint", "Tools", "Garden", "Electrical"], k=2),
            }
        
        return MCPToolResult.json_result(profile)
    
    async def _get_recommendations(self, args: dict) -> MCPToolResult:
        """Get mock product recommendations."""
        customer_id = args.get("customer_id")
        category = args.get("category")
        limit = args.get("limit", 5)
        
        products = [
            {"name": "Premium Interior Paint - White", "category": "Paint", "price": 65.00},
            {"name": "Cordless Drill 18V", "category": "Tools", "price": 189.00},
            {"name": "Garden Hose 30m", "category": "Garden", "price": 45.00},
            {"name": "LED Downlight Pack", "category": "Electrical", "price": 35.00},
            {"name": "Tap Mixer Set", "category": "Plumbing", "price": 120.00},
            {"name": "Paint Roller Kit", "category": "Paint", "price": 25.00},
            {"name": "Circular Saw", "category": "Tools", "price": 299.00},
            {"name": "Fertilizer 10kg", "category": "Garden", "price": 28.00},
        ]
        
        if category:
            products = [p for p in products if p["category"] == category]
        
        recommendations = []
        for i, product in enumerate(products[:limit]):
            recommendations.append({
                "rank": i + 1,
                "product_name": product["name"],
                "category": product["category"],
                "price": product["price"],
                "confidence_score": round(random.uniform(0.7, 0.98), 2),
                "reason": random.choice([
                    "Based on purchase history",
                    "Frequently bought together",
                    "Popular in your area",
                    "Matches your interests",
                ]),
            })
        
        return MCPToolResult.json_result({
            "customer_id": customer_id,
            "recommendation_count": len(recommendations),
            "recommendations": recommendations,
        })
    
    async def _get_customer_segments(self, args: dict) -> MCPToolResult:
        """Get mock customer segments."""
        customer_id = args.get("customer_id")
        segment_type = args.get("segment_type", "all")
        
        segments = {
            "behavioral": [
                {"name": "Weekend Warriors", "description": "Shops primarily on weekends", "size": 125000},
                {"name": "Project Planners", "description": "Large basket, infrequent purchases", "size": 45000},
                {"name": "Quick Fixers", "description": "Small urgent purchases", "size": 89000},
            ],
            "demographic": [
                {"name": "Young Homeowners", "description": "Age 25-35, first home", "size": 67000},
                {"name": "Established Renovators", "description": "Age 45-55, ongoing projects", "size": 98000},
                {"name": "Trade Professionals", "description": "Licensed tradies", "size": 23000},
            ],
            "value": [
                {"name": "High Value", "description": "Top 10% by LTV", "size": 15000},
                {"name": "Growth Potential", "description": "Increasing spend trajectory", "size": 34000},
                {"name": "At Risk", "description": "Declining engagement", "size": 28000},
            ],
        }
        
        if segment_type != "all":
            segments = {segment_type: segments.get(segment_type, [])}
        
        if customer_id:
            # Assign customer to random segments
            customer_segments = []
            for seg_type, seg_list in segments.items():
                seg = random.choice(seg_list)
                customer_segments.append({
                    "type": seg_type,
                    "segment": seg["name"],
                    "membership_score": round(random.uniform(0.6, 0.95), 2),
                })
            return MCPToolResult.json_result({
                "customer_id": customer_id,
                "segments": customer_segments,
            })
        
        return MCPToolResult.json_result({
            "segment_type": segment_type,
            "segments": segments,
        })
