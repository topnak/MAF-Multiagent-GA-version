# ─────────────────────────────────────────────────────────────────────────────
# MCP Servers Module
# ─────────────────────────────────────────────────────────────────────────────
# Mock MCP (Model Context Protocol) servers for POC testing.
# Implements proper MCP protocol format for integration with MAF agents.
# ─────────────────────────────────────────────────────────────────────────────

from .base_mcp_server import BaseMCPServer, MCPTool, MCPToolCall, MCPToolResult
from .snowflake_mcp import SnowflakeMCPServer
from .personalisation_mcp import PersonalisationMCPServer
from .localisation_mcp import LocalisationMCPServer
from .items_api_mcp import ItemsAPIMCPServer
from .salesforce_mcp import SalesforceMCPServer
from .weather_mcp import WeatherMCPServer

__all__ = [
    # Base classes
    "BaseMCPServer",
    "MCPTool",
    "MCPToolCall",
    "MCPToolResult",
    # Mock servers
    "SnowflakeMCPServer",
    "PersonalisationMCPServer",
    "LocalisationMCPServer",
    "ItemsAPIMCPServer",
    "SalesforceMCPServer",
    "WeatherMCPServer",
]
