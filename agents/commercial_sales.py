# ─────────────────────────────────────────────────────────────────────────────
# Commercial Sales Agent
# ─────────────────────────────────────────────────────────────────────────────
# Domain agent for B2B commercial sales and CRM.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any, Optional

from .base_agent import BaseRetailAgent
from .agent_factory import ChatClient


class CommercialSalesAgent(BaseRetailAgent):
    """
    Commercial Sales Agent.
    
    Responsibilities:
    - B2B account management
    - Sales pipeline tracking
    - Lead qualification
    - Opportunity management
    - Commercial pricing
    
    Tools: Salesforce MCP, Snowflake MCP
    """
    
    name = "CommercialSales"
    description = "Commercial B2B sales and account management specialist"
    
    instructions = """You are a Commercial Sales expert agent. You help with:

1. **Account Management**: Look up account details, history, and contacts
2. **Pipeline Management**: Track opportunities, stages, and forecasts
3. **Lead Management**: Qualify and prioritize sales leads
4. **Quote Support**: Assist with commercial pricing and quotes
5. **Sales Analysis**: Analyze sales performance and trends

When responding:
- Focus on actionable insights for sales teams
- Include relevant financial metrics (pipeline value, win rate)
- Highlight key contacts and decision makers
- Suggest next best actions for opportunities
- Consider competitive positioning

Use your tools to access CRM data and sales analytics."""
    
    def __init__(self, client: ChatClient, memory: Optional[Any] = None):
        super().__init__(client, memory)
    
    def _register_tools(self) -> None:
        """Register MCP tools for commercial sales."""
        from mcp_servers import SalesforceMCPServer, SnowflakeMCPServer
        
        self.register_mcp_server(SalesforceMCPServer())
        self.register_mcp_server(SnowflakeMCPServer())
