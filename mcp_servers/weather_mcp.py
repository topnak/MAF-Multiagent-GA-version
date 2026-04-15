# ─────────────────────────────────────────────────────────────────────────────
# Weather MCP Server (Mock)
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation for weather data access (useful for campaign planning).
# ─────────────────────────────────────────────────────────────────────────────

import random
from datetime import datetime, timedelta

from .base_mcp_server import (
    BaseMCPServer,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
    create_json_schema,
)


class WeatherMCPServer(BaseMCPServer):
    """Mock Weather MCP server for weather data access."""
    
    def __init__(self):
        super().__init__(
            name="weather-mcp",
            version="1.0.0",
            description="Access weather data and forecasts for campaign planning"
        )
    
    def _register_tools(self) -> None:
        self.register_tool(MCPTool(
            name="get_current_weather",
            description="Get current weather conditions for a location.",
            input_schema=create_json_schema(
                properties={
                    "location": {"type": "string", "description": "City or postcode"},
                },
                required=["location"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_forecast",
            description="Get weather forecast for upcoming days.",
            input_schema=create_json_schema(
                properties={
                    "location": {"type": "string", "description": "City or postcode"},
                    "days": {"type": "integer", "description": "Number of days", "default": 7},
                },
                required=["location"]
            )
        ))
        
        self.register_tool(MCPTool(
            name="get_seasonal_outlook",
            description="Get seasonal weather outlook for planning.",
            input_schema=create_json_schema(
                properties={
                    "region": {"type": "string", "description": "State or region"},
                    "season": {"type": "string", "description": "Season", "enum": ["summer", "autumn", "winter", "spring"]},
                },
                required=["region"]
            )
        ))
    
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        if call.name == "get_current_weather":
            return await self._get_current_weather(call.arguments)
        elif call.name == "get_forecast":
            return await self._get_forecast(call.arguments)
        elif call.name == "get_seasonal_outlook":
            return await self._get_seasonal_outlook(call.arguments)
        return MCPToolResult.error(f"Unknown tool: {call.name}")
    
    async def _get_current_weather(self, args: dict) -> MCPToolResult:
        location = args.get("location", "Melbourne")
        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Light Rain", "Clear"]
        
        return MCPToolResult.json_result({
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "temperature_c": random.randint(12, 35),
            "feels_like_c": random.randint(10, 38),
            "humidity_pct": random.randint(30, 80),
            "wind_speed_kmh": random.randint(5, 40),
            "wind_direction": random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"]),
            "condition": random.choice(conditions),
            "uv_index": random.randint(1, 11),
            "visibility_km": random.randint(5, 20),
        })
    
    async def _get_forecast(self, args: dict) -> MCPToolResult:
        location = args.get("location", "Melbourne")
        days = args.get("days", 7)
        conditions = ["Sunny", "Partly Cloudy", "Cloudy", "Showers", "Rain", "Clear", "Thunderstorms"]
        
        forecast = []
        for i in range(days):
            date = datetime.now() + timedelta(days=i)
            forecast.append({
                "date": date.strftime("%Y-%m-%d"),
                "day_name": date.strftime("%A"),
                "condition": random.choice(conditions),
                "temp_high_c": random.randint(18, 38),
                "temp_low_c": random.randint(8, 22),
                "chance_of_rain_pct": random.randint(0, 100),
                "rainfall_mm": round(random.uniform(0, 15), 1),
                "wind_speed_kmh": random.randint(5, 35),
            })
        
        return MCPToolResult.json_result({
            "location": location,
            "forecast_days": days,
            "forecast": forecast,
        })
    
    async def _get_seasonal_outlook(self, args: dict) -> MCPToolResult:
        region = args.get("region", "VIC")
        season = args.get("season", "summer")
        
        outlooks = {
            "summer": {
                "temp_outlook": "Above average temperatures expected",
                "rainfall_outlook": "Below average rainfall likely",
                "key_events": ["Heat waves possible", "High fire danger days", "UV extreme"],
                "retail_impact": "High demand for cooling, outdoor, summer garden products",
            },
            "autumn": {
                "temp_outlook": "Near average temperatures",
                "rainfall_outlook": "Average to above average rainfall",
                "key_events": ["Seasonal transition", "Morning fog likely"],
                "retail_impact": "Garden cleanup products, heating preparation",
            },
            "winter": {
                "temp_outlook": "Below average temperatures",
                "rainfall_outlook": "Above average rainfall expected",
                "key_events": ["Cold snaps expected", "Frost mornings"],
                "retail_impact": "High demand for heating, insulation, weather sealing",
            },
            "spring": {
                "temp_outlook": "Variable, trending warmer",
                "rainfall_outlook": "Average rainfall with storm risk",
                "key_events": ["Storm season begins", "Hay fever peak"],
                "retail_impact": "Garden revival, painting season, outdoor furniture",
            },
        }
        
        outlook = outlooks.get(season, outlooks["summer"])
        
        return MCPToolResult.json_result({
            "region": region,
            "season": season,
            **outlook,
            "confidence": random.choice(["High", "Medium", "Moderate"]),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
        })
