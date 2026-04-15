# ─────────────────────────────────────────────────────────────────────────────
# Campaign Analyst Agent
# ─────────────────────────────────────────────────────────────────────────────
# Domain agent for marketing campaigns and analytics.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any, Optional

from .base_agent import BaseRetailAgent
from .agent_factory import ChatClient


class CampaignAnalystAgent(BaseRetailAgent):
    """
    Campaign Analyst Agent.
    
    Responsibilities:
    - Campaign planning and analysis
    - Marketing effectiveness
    - Promotional performance
    - Seasonal planning
    - Weather-based recommendations
    
    Tools: Weather MCP, Snowflake MCP
    """
    
    name = "CampaignAnalyst"
    description = "Marketing campaign and promotional analyst"
    
    instructions = """You are a Campaign Analyst expert agent. You help with:

1. **Campaign Planning**: Plan marketing campaigns with timing and targeting
2. **Performance Analysis**: Analyze campaign ROI and effectiveness
3. **Promotional Strategy**: Recommend promotional tactics and offers
4. **Seasonal Planning**: Plan campaigns around seasons and events
5. **Weather Intelligence**: Use weather forecasts for campaign timing

When responding:
- Base recommendations on historical campaign performance data
- Consider weather impact on product demand
- Include target audience and channel recommendations
- Provide expected ROI or lift estimates
- Suggest measurement KPIs for campaigns

Use your tools to access sales data and weather forecasts for planning."""
    
    def __init__(self, client: ChatClient, memory: Optional[Any] = None):
        super().__init__(client, memory)
    
    def _register_tools(self) -> None:
        """Register MCP tools for campaigns."""
        from mcp_servers import WeatherMCPServer, SnowflakeMCPServer
        
        self.register_mcp_server(WeatherMCPServer())
        self.register_mcp_server(SnowflakeMCPServer())
