# ─────────────────────────────────────────────────────────────────────────────
# Space Planner Agent
# ─────────────────────────────────────────────────────────────────────────────
# Domain agent for store space planning and planogram optimization.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any, Optional

from .base_agent import BaseRetailAgent
from .agent_factory import ChatClient


class SpacePlannerAgent(BaseRetailAgent):
    """
    Space Planner Agent.
    
    Responsibilities:
    - Planogram optimization
    - Store layout efficiency
    - Space-to-sales analysis
    - Fixture allocation
    - Category space allocation
    
    Tools: Snowflake MCP
    """
    
    name = "SpacePlanner"
    description = "Space planner for store layouts and planogram optimization"
    
    instructions = """You are a Space Planning expert agent. You help with:

1. **Planogram Analysis**: Analyze product placement effectiveness and space utilization
2. **Space-to-Sales**: Calculate and optimize space allocation based on sales performance
3. **Store Layout**: Recommend layout improvements for customer flow and sales
4. **Fixture Planning**: Advise on fixture types and configurations
5. **Category Space**: Optimize space allocation across product categories

When responding:
- Consider sales velocity, product dimensions, and margin contribution
- Analyze space productivity (sales per linear meter / sqm)
- Account for store format differences (warehouse, small format, trade)
- Include visual merchandising principles
- Provide specific recommendations with expected impact

Use your tools to query space performance data, store metrics, and sales by location."""
    
    def __init__(self, client: ChatClient, memory: Optional[Any] = None):
        super().__init__(client, memory)
    
    def _register_tools(self) -> None:
        """Register MCP tools for space planning."""
        from mcp_servers import SnowflakeMCPServer
        
        snowflake = SnowflakeMCPServer()
        self.register_mcp_server(snowflake)
