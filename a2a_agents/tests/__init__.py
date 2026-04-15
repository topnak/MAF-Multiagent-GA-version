# ─────────────────────────────────────────────────────────────────────────────
# A2A Module Tests
# ─────────────────────────────────────────────────────────────────────────────
# Unit tests for A2A client, server, and mock agents.
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from a2a_agents.a2a_client import (
    A2AClient,
    A2AMessage,
    A2AResponse,
    A2AMessageType,
    A2AStatus,
)
from a2a_agents.a2a_server import (
    A2AServer,
    A2AServerConfig,
    SimpleA2AHandler,
)
from a2a_agents.mock_a2a_agents import (
    MockPricingAgent,
    MockInventoryCheckAgent,
    MockFulfilmentAgent,
)


# ─────────────────────────────────────────────────────────────────────────────
# A2AMessage Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestA2AMessage:
    """Tests for A2AMessage dataclass."""
    
    def test_create_message(self):
        """Test creating an A2A message."""
        message = A2AMessage(
            message_id="msg-123",
            conversation_id="conv-456",
            sender_agent="SenderAgent",
            recipient_agent="RecipientAgent",
            message_type=A2AMessageType.REQUEST,
            content="Hello, I need help",
        )
        
        assert message.message_id == "msg-123"
        assert message.sender_agent == "SenderAgent"
        assert message.recipient_agent == "RecipientAgent"
        assert message.message_type == A2AMessageType.REQUEST
    
    def test_to_dict(self):
        """Test converting message to dictionary."""
        message = A2AMessage(
            message_id="msg-123",
            conversation_id="conv-456",
            sender_agent="SenderAgent",
            recipient_agent="RecipientAgent",
            message_type=A2AMessageType.REQUEST,
            content="Test content",
            context={"key": "value"},
        )
        
        data = message.to_dict()
        
        assert data["message_id"] == "msg-123"
        assert data["message_type"] == "request"
        assert data["context"] == {"key": "value"}
    
    def test_from_dict(self):
        """Test creating message from dictionary."""
        data = {
            "message_id": "msg-123",
            "conversation_id": "conv-456",
            "sender_agent": "SenderAgent",
            "recipient_agent": "RecipientAgent",
            "message_type": "request",
            "content": "Test",
            "context": None,
            "metadata": {},
        }
        
        message = A2AMessage.from_dict(data)
        
        assert message.message_id == "msg-123"
        assert message.message_type == A2AMessageType.REQUEST


# ─────────────────────────────────────────────────────────────────────────────
# A2AResponse Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestA2AResponse:
    """Tests for A2AResponse dataclass."""
    
    def test_create_response(self):
        """Test creating an A2A response."""
        response = A2AResponse(
            message_id="msg-123",
            conversation_id="conv-456",
            status=A2AStatus.SUCCESS,
            content="Here's your answer",
        )
        
        assert response.status == A2AStatus.SUCCESS
        assert response.content == "Here's your answer"
        assert response.error is None
    
    def test_error_response(self):
        """Test creating an error response."""
        response = A2AResponse(
            message_id="msg-123",
            conversation_id="conv-456",
            status=A2AStatus.ERROR,
            error="Something went wrong",
        )
        
        assert response.status == A2AStatus.ERROR
        assert response.error == "Something went wrong"


# ─────────────────────────────────────────────────────────────────────────────
# A2AClient Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestA2AClient:
    """Tests for A2AClient."""
    
    def test_init(self):
        """Test client initialization."""
        client = A2AClient(
            agent_name="TestAgent",
            agent_endpoints={
                "PricingAgent": "http://localhost:8001/a2a",
                "InventoryAgent": "http://localhost:8002/a2a",
            },
        )
        
        assert client._agent_name == "TestAgent"
        assert len(client._endpoints) == 2
    
    @pytest.mark.asyncio
    async def test_send_unknown_recipient(self):
        """Test sending to unknown recipient."""
        client = A2AClient(
            agent_name="TestAgent",
            agent_endpoints={},
        )
        
        response = await client.send(
            recipient="UnknownAgent",
            content="Hello",
        )
        
        assert response.status == A2AStatus.ERROR
        assert "Unknown recipient" in response.error
    
    def test_add_endpoint(self):
        """Test adding an endpoint."""
        client = A2AClient(
            agent_name="TestAgent",
            agent_endpoints={},
        )
        
        client.add_endpoint("NewAgent", "http://new-agent:8000/a2a")
        
        assert "NewAgent" in client._endpoints
    
    def test_remove_endpoint(self):
        """Test removing an endpoint."""
        client = A2AClient(
            agent_name="TestAgent",
            agent_endpoints={"OldAgent": "http://old:8000/a2a"},
        )
        
        result = client.remove_endpoint("OldAgent")
        
        assert result is True
        assert "OldAgent" not in client._endpoints
    
    def test_get_conversation_empty(self):
        """Test getting non-existent conversation."""
        client = A2AClient(
            agent_name="TestAgent",
            agent_endpoints={},
        )
        
        messages = client.get_conversation("non-existent")
        
        assert messages == []


# ─────────────────────────────────────────────────────────────────────────────
# A2AServer Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestA2AServer:
    """Tests for A2AServer."""
    
    def test_init(self):
        """Test server initialization."""
        config = A2AServerConfig(
            agent_name="TestServer",
            port=8080,
        )
        server = A2AServer(config)
        
        assert server.agent_name == "TestServer"
        assert server._handlers == []
    
    def test_register_handler(self):
        """Test registering a handler."""
        config = A2AServerConfig(agent_name="TestServer")
        server = A2AServer(config)
        
        handler = SimpleA2AHandler(
            agent_name="TestServer",
            callback=AsyncMock(return_value="Handled"),
        )
        
        server.register_handler(handler)
        
        assert len(server._handlers) == 1
    
    @pytest.mark.asyncio
    async def test_process_message_wrong_recipient(self):
        """Test processing message for wrong recipient."""
        config = A2AServerConfig(agent_name="TestServer")
        server = A2AServer(config)
        
        response = await server.process_message({
            "message_id": "msg-123",
            "conversation_id": "conv-456",
            "sender_agent": "OtherAgent",
            "recipient_agent": "WrongAgent",
            "message_type": "request",
            "content": "Hello",
        })
        
        assert response["status"] == "error"
        assert "Wrong recipient" in response["error"]


# ─────────────────────────────────────────────────────────────────────────────
# Mock PricingAgent Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockPricingAgent:
    """Tests for MockPricingAgent."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = MockPricingAgent()
        
        assert agent.name == "PricingAgent"
    
    @pytest.mark.asyncio
    async def test_process_paint_price(self):
        """Test getting paint pricing."""
        agent = MockPricingAgent()
        
        result = await agent.process("What's the price for paint?", None)
        
        assert "Paint" in result
        assert "$" in result
    
    @pytest.mark.asyncio
    async def test_process_bulk_pricing(self):
        """Test getting bulk pricing."""
        agent = MockPricingAgent()
        
        result = await agent.process("Show me bulk pricing", None)
        
        assert "Bulk Pricing" in result
        assert "Discount" in result


# ─────────────────────────────────────────────────────────────────────────────
# Mock InventoryCheckAgent Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockInventoryCheckAgent:
    """Tests for MockInventoryCheckAgent."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = MockInventoryCheckAgent()
        
        assert agent.name == "InventoryCheckAgent"
    
    @pytest.mark.asyncio
    async def test_process_low_stock(self):
        """Test getting low stock alerts."""
        agent = MockInventoryCheckAgent()
        
        result = await agent.process("Show me low stock alerts", None)
        
        assert "Stock" in result
    
    @pytest.mark.asyncio
    async def test_process_inventory_summary(self):
        """Test getting inventory summary."""
        agent = MockInventoryCheckAgent()
        
        result = await agent.process("Give me inventory overview", None)
        
        assert "Summary" in result
        assert "Total" in result


# ─────────────────────────────────────────────────────────────────────────────
# Mock FulfilmentAgent Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMockFulfilmentAgent:
    """Tests for MockFulfilmentAgent."""
    
    def test_init(self):
        """Test agent initialization."""
        agent = MockFulfilmentAgent()
        
        assert agent.name == "FulfilmentAgent"
    
    @pytest.mark.asyncio
    async def test_process_order_status(self):
        """Test getting order status."""
        agent = MockFulfilmentAgent()
        
        result = await agent.process("Status of ORD-12345", None)
        
        assert "ORD-12345" in result
        assert "shipped" in result.lower() or "Status" in result
    
    @pytest.mark.asyncio
    async def test_process_all_orders(self):
        """Test getting all orders."""
        agent = MockFulfilmentAgent()
        
        result = await agent.process("Show all orders", None)
        
        assert "Summary" in result or "Total" in result
