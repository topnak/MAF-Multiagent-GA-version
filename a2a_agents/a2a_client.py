# ─────────────────────────────────────────────────────────────────────────────
# A2A Client
# ─────────────────────────────────────────────────────────────────────────────
# Client for Agent-to-Agent communication following the A2A protocol.
# Enables agents to communicate with external agents via HTTP.
#
# A2A Protocol Overview:
# - Agents expose HTTP endpoints for receiving messages
# - Messages contain task descriptions and optional context
# - Responses include results and metadata
# ─────────────────────────────────────────────────────────────────────────────

import logging
import httpx
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
import json

# Configure module logger
logger = logging.getLogger(__name__)


class A2AMessageType(str, Enum):
    """Type of A2A message."""
    REQUEST = "request"         # Initial request to another agent
    RESPONSE = "response"       # Response from an agent
    HANDOFF = "handoff"         # Transfer to another agent
    BROADCAST = "broadcast"     # Message to multiple agents


class A2AStatus(str, Enum):
    """Status of an A2A interaction."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"


@dataclass
class A2AMessage:
    """
    Message sent between agents via A2A protocol.
    
    Attributes:
        message_id: Unique identifier for this message
        conversation_id: ID linking messages in a conversation
        sender_agent: Name of the sending agent
        recipient_agent: Name of the receiving agent
        message_type: Type of message (request, response, etc.)
        content: The task/query content
        context: Optional context from previous interactions
        metadata: Additional metadata (timestamps, tokens, etc.)
        created_at: When the message was created
    """
    message_id: str
    conversation_id: str
    sender_agent: str
    recipient_agent: str
    message_type: A2AMessageType
    content: str
    context: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert message to dictionary for transmission."""
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "sender_agent": self.sender_agent,
            "recipient_agent": self.recipient_agent,
            "message_type": self.message_type.value,
            "content": self.content,
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A2AMessage":
        """Create message from dictionary."""
        return cls(
            message_id=data["message_id"],
            conversation_id=data["conversation_id"],
            sender_agent=data["sender_agent"],
            recipient_agent=data["recipient_agent"],
            message_type=A2AMessageType(data["message_type"]),
            content=data["content"],
            context=data.get("context"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
        )


@dataclass
class A2AResponse:
    """
    Response from an A2A interaction.
    
    Attributes:
        message_id: ID of the original message
        conversation_id: Conversation ID
        status: Status of the response
        content: Response content
        error: Error message if status is ERROR
        metadata: Additional response metadata
        responded_at: When the response was generated
    """
    message_id: str
    conversation_id: str
    status: A2AStatus
    content: Optional[str] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    responded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "status": self.status.value,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata,
            "responded_at": self.responded_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "A2AResponse":
        """Create response from dictionary."""
        return cls(
            message_id=data["message_id"],
            conversation_id=data["conversation_id"],
            status=A2AStatus(data["status"]),
            content=data.get("content"),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
        )


class A2AClient:
    """
    Client for sending messages to external agents via A2A protocol.
    
    This client enables our agents to communicate with external agents
    that implement the A2A protocol. It handles:
    - HTTP POST requests to agent endpoints
    - Message serialization/deserialization
    - Timeout and error handling
    - Conversation tracking
    
    Usage:
        client = A2AClient(
            agent_name="LocalAgent",
            agent_endpoints={
                "PricingAgent": "http://pricing-agent:8000/a2a",
                "InventoryAgent": "http://inventory-agent:8000/a2a",
            },
        )
        
        response = await client.send(
            recipient="PricingAgent",
            content="What's the price for SKU-123?",
        )
    """
    
    def __init__(
        self,
        agent_name: str,
        agent_endpoints: dict[str, str],
        timeout_seconds: float = 30.0,
        headers: Optional[dict[str, str]] = None,
    ):
        """
        Initialize the A2A client.
        
        Args:
            agent_name: Name of the local agent sending messages
            agent_endpoints: Mapping of agent names to their A2A endpoints
            timeout_seconds: Request timeout
            headers: Optional additional headers (e.g., auth tokens)
        """
        self._agent_name = agent_name
        self._endpoints = agent_endpoints
        self._timeout = timeout_seconds
        self._headers = headers or {}
        
        # Conversation tracking
        self._conversations: dict[str, list[A2AMessage]] = {}
        
        logger.info(
            f"A2AClient initialized for {agent_name} "
            f"with {len(agent_endpoints)} registered endpoints"
        )
    
    async def send(
        self,
        recipient: str,
        content: str,
        conversation_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> A2AResponse:
        """
        Send a message to another agent.
        
        Args:
            recipient: Name of the recipient agent
            content: Message content
            conversation_id: Optional conversation ID (auto-generated if not provided)
            context: Optional context to include
            
        Returns:
            A2AResponse from the recipient agent
        """
        import uuid
        
        # Validate recipient
        endpoint = self._endpoints.get(recipient)
        if not endpoint:
            logger.error(f"Unknown recipient agent: {recipient}")
            return A2AResponse(
                message_id=f"msg-{uuid.uuid4().hex[:8]}",
                conversation_id=conversation_id or f"conv-{uuid.uuid4().hex[:8]}",
                status=A2AStatus.ERROR,
                error=f"Unknown recipient agent: {recipient}",
            )
        
        # Create message
        message = A2AMessage(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id or f"conv-{uuid.uuid4().hex[:8]}",
            sender_agent=self._agent_name,
            recipient_agent=recipient,
            message_type=A2AMessageType.REQUEST,
            content=content,
            context=context,
        )
        
        # Track conversation
        if message.conversation_id not in self._conversations:
            self._conversations[message.conversation_id] = []
        self._conversations[message.conversation_id].append(message)
        
        logger.info(f"Sending A2A message to {recipient}: {message.message_id}")
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    endpoint,
                    json=message.to_dict(),
                    headers={
                        "Content-Type": "application/json",
                        "X-A2A-Sender": self._agent_name,
                        **self._headers,
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return A2AResponse.from_dict(data)
                else:
                    logger.error(f"A2A request failed: {response.status_code}")
                    return A2AResponse(
                        message_id=message.message_id,
                        conversation_id=message.conversation_id,
                        status=A2AStatus.ERROR,
                        error=f"HTTP {response.status_code}: {response.text}",
                    )
                    
        except httpx.TimeoutException:
            logger.error(f"A2A request to {recipient} timed out")
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.TIMEOUT,
                error=f"Request timed out after {self._timeout}s",
            )
            
        except Exception as e:
            logger.error(f"A2A request failed: {e}")
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.ERROR,
                error=str(e),
            )
    
    async def handoff(
        self,
        recipient: str,
        content: str,
        conversation_id: str,
        full_context: dict[str, Any],
    ) -> A2AResponse:
        """
        Hand off a conversation to another agent.
        
        A handoff transfers the full conversation context to
        another agent, which takes over the interaction.
        
        Args:
            recipient: Agent to hand off to
            content: Handoff instructions
            conversation_id: Existing conversation ID
            full_context: Full conversation context
            
        Returns:
            A2AResponse from the handoff recipient
        """
        import uuid
        
        endpoint = self._endpoints.get(recipient)
        if not endpoint:
            return A2AResponse(
                message_id=f"msg-{uuid.uuid4().hex[:8]}",
                conversation_id=conversation_id,
                status=A2AStatus.ERROR,
                error=f"Unknown handoff agent: {recipient}",
            )
        
        message = A2AMessage(
            message_id=f"msg-{uuid.uuid4().hex[:8]}",
            conversation_id=conversation_id,
            sender_agent=self._agent_name,
            recipient_agent=recipient,
            message_type=A2AMessageType.HANDOFF,
            content=content,
            context=full_context,
            metadata={"handoff": True, "previous_agent": self._agent_name},
        )
        
        logger.info(f"Handing off conversation {conversation_id} to {recipient}")
        
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    endpoint,
                    json=message.to_dict(),
                    headers={
                        "Content-Type": "application/json",
                        "X-A2A-Sender": self._agent_name,
                        "X-A2A-Handoff": "true",
                        **self._headers,
                    },
                )
                
                if response.status_code == 200:
                    return A2AResponse.from_dict(response.json())
                else:
                    return A2AResponse(
                        message_id=message.message_id,
                        conversation_id=conversation_id,
                        status=A2AStatus.ERROR,
                        error=f"Handoff failed: HTTP {response.status_code}",
                    )
                    
        except Exception as e:
            logger.error(f"Handoff failed: {e}")
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=conversation_id,
                status=A2AStatus.ERROR,
                error=str(e),
            )
    
    def get_conversation(self, conversation_id: str) -> list[A2AMessage]:
        """Get all messages in a conversation."""
        return self._conversations.get(conversation_id, [])
    
    def add_endpoint(self, agent_name: str, endpoint: str) -> None:
        """Add or update an agent endpoint."""
        self._endpoints[agent_name] = endpoint
        logger.info(f"Added endpoint for {agent_name}: {endpoint}")
    
    def remove_endpoint(self, agent_name: str) -> bool:
        """Remove an agent endpoint."""
        if agent_name in self._endpoints:
            del self._endpoints[agent_name]
            logger.info(f"Removed endpoint for {agent_name}")
            return True
        return False
