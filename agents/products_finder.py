# ─────────────────────────────────────────────────────────────────────────────
# Products Finder Agent
# ─────────────────────────────────────────────────────────────────────────────
# Domain agent for product search and catalog management.
# ─────────────────────────────────────────────────────────────────────────────

from typing import Any, Optional

from .base_agent import BaseRetailAgent
from .agent_factory import ChatClient


class ProductsFinderAgent(BaseRetailAgent):
    """
    Products Finder Agent.
    
    Responsibilities:
    - Product search and discovery
    - Catalog navigation
    - Product comparisons
    - Alternative recommendations
    - Availability checks
    
    Tools: Items API MCP
    """
    
    name = "ProductsFinder"
    description = "Product search and catalog specialist"
    
    instructions = """You are a Product Finder expert agent. You help with:

1. **Product Search**: Find products by name, category, or attributes
2. **Product Details**: Provide detailed product information and specifications
3. **Comparisons**: Compare similar products on features and price
4. **Alternatives**: Suggest alternative products when items are unavailable
5. **Category Navigation**: Help navigate the product category hierarchy

When responding:
- Provide accurate product information including prices and SKUs
- Include relevant specifications and dimensions
- Highlight key features and benefits
- Mention availability and stock status when relevant
- Suggest complementary products when appropriate

Use your tools to search the product catalog and retrieve detailed information."""
    
    def __init__(self, client: ChatClient, memory: Optional[Any] = None):
        super().__init__(client, memory)
    
    def _register_tools(self) -> None:
        """Register MCP tools for products."""
        from mcp_servers import ItemsAPIMCPServer
        
        self.register_mcp_server(ItemsAPIMCPServer())
