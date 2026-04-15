# ─────────────────────────────────────────────────────────────────────────────
# A2A (Agent-to-Agent) Module
# ─────────────────────────────────────────────────────────────────────────────
# Mock implementation of A2A protocol for agent communication.
# Based on Google's A2A protocol specification.
# ─────────────────────────────────────────────────────────────────────────────

from a2a_agents.a2a_client import A2AClient, A2AMessage, A2AResponse
from a2a_agents.a2a_server import A2AServer, A2AHandler
from a2a_agents.mock_a2a_agents import (
    MockPricingAgent,
    MockInventoryCheckAgent,
    MockFulfilmentAgent,
)

__all__ = [
    # Client
    "A2AClient",
    "A2AMessage",
    "A2AResponse",
    # Server
    "A2AServer",
    "A2AHandler",
    # Mock Agents
    "MockPricingAgent",
    "MockInventoryCheckAgent",
    "MockFulfilmentAgent",
]
