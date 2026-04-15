# ─────────────────────────────────────────────────────────────────────────────
# Merchandising Planner Agent
# ─────────────────────────────────────────────────────────────────────────────
# Domain agent for merchandising and assortment planning.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any, Optional

from .base_agent import BaseRetailAgent
from .agent_factory import ChatClient


class MerchPlannerAgent(BaseRetailAgent):
    """
    Merchandising Planner Agent.
    
    Responsibilities:
    - Analyze product assortment performance
    - Range review and optimization
    - Markdown and pricing strategy
    - Category performance analysis
    - Stock allocation recommendations
    
    Tools: Snowflake MCP
    """
    
    name = "MerchPlanner"
    description = "Merchandising planner for assortment and category management"
    
    instructions = """You are a Merchandising Planner expert agent. You help with:

1. **Assortment Planning**: Analyze product range, identify gaps, and recommend additions/deletions
2. **Category Performance**: Review sales, margins, and sell-through by category
3. **Markdown Strategy**: Recommend pricing adjustments for slow-moving inventory
4. **Stock Allocation**: Advise on inventory distribution across stores
5. **Range Reviews**: Conduct product range reviews with data-driven insights

When responding:
- Always base recommendations on data from the Snowflake data warehouse
- Consider seasonality, regional differences, and customer segments
- Provide specific SKU-level insights when relevant
- Include metrics: sell-through rate, stock cover, GMROI, margin %
- Be concise but thorough in your analysis

Use your tools to query sales data, inventory levels, and store performance before making recommendations."""
    
    def __init__(self, client: ChatClient, memory: Optional[Any] = None):
        super().__init__(client, memory)
    
    def _register_tools(self) -> None:
        """Register MCP tools for merchandising."""
        from mcp_servers import SnowflakeMCPServer
        
        # Register Snowflake MCP server
        snowflake = SnowflakeMCPServer()
        self.register_mcp_server(snowflake)
