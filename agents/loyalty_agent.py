# ─────────────────────────────────────────────────────────────────────────────
# Loyalty Agent
# ─────────────────────────────────────────────────────────────────────────────
# Domain agent for loyalty programs and customer engagement.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any, Optional

from .base_agent import BaseRetailAgent
from .agent_factory import ChatClient


class LoyaltyAgent(BaseRetailAgent):
    """
    Loyalty Agent.
    
    Responsibilities:
    - Loyalty program management
    - Customer rewards and points
    - Member engagement strategies
    - Tier progression analysis
    - Personalized offers
    
    Tools: Personalisation MCP, Localisation MCP
    """
    
    name = "LoyaltyAgent"
    description = "Loyalty program and customer engagement specialist"
    
    instructions = """You are a Loyalty Program expert agent. You help with:

1. **Member Management**: Look up member details, points balance, tier status
2. **Rewards Strategy**: Recommend personalized rewards and offers
3. **Engagement Analysis**: Analyze member engagement and retention
4. **Tier Optimization**: Advise on tier benefits and progression
5. **Campaign Targeting**: Identify segments for loyalty campaigns

When responding:
- Respect customer privacy - only share relevant information
- Consider member lifetime value and engagement history
- Personalize recommendations based on preferences
- Include specific point values and tier benefits
- Suggest actionable engagement strategies

Use your tools to access customer profiles, segments, and personalization data."""
    
    def __init__(self, client: ChatClient, memory: Optional[Any] = None):
        super().__init__(client, memory)
    
    def _register_tools(self) -> None:
        """Register MCP tools for loyalty."""
        from mcp_servers import PersonalisationMCPServer, LocalisationMCPServer
        
        self.register_mcp_server(PersonalisationMCPServer())
        self.register_mcp_server(LocalisationMCPServer())
