# ─────────────────────────────────────────────────────────────────────────────
# Agents Module
# ─────────────────────────────────────────────────────────────────────────────
# Domain agents for the retail multi-agent system.
# Built on MAF 1.0 GA patterns with cloud-agnostic design.
# ─────────────────────────────────────────────────────────────────────────────

from .agent_factory import AgentFactory, create_chat_client
from .base_agent import BaseRetailAgent
from .merch_planner import MerchPlannerAgent
from .space_planner import SpacePlannerAgent
from .loyalty_agent import LoyaltyAgent
from .products_finder import ProductsFinderAgent
from .commercial_sales import CommercialSalesAgent
from .campaign_analyst import CampaignAnalystAgent

__all__ = [
    # Factory
    "AgentFactory",
    "create_chat_client",
    # Base
    "BaseRetailAgent",
    # Domain agents
    "MerchPlannerAgent",
    "SpacePlannerAgent",
    "LoyaltyAgent",
    "ProductsFinderAgent",
    "CommercialSalesAgent",
    "CampaignAnalystAgent",
]
