# ─────────────────────────────────────────────────────────────────────────────
# A2A Server
# ─────────────────────────────────────────────────────────────────────────────
# Server component for receiving A2A messages from external agents.
# Exposes an HTTP endpoint that other agents can POST to.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional
import uuid

from a2a_agents.a2a_client import (
    A2AMessage,
    A2AResponse,
    A2AMessageType,
    A2AStatus,
)

# Configure module logger
logger = logging.getLogger(__name__)


class A2AHandler(ABC):
    """
    Abstract handler for processing A2A messages.
    
    Implement this interface to create custom handlers for
    incoming A2A messages.
    """
    
    @abstractmethod
    async def handle(self, message: A2AMessage) -> A2AResponse:
        """
        Handle an incoming A2A message.
        
        Args:
            message: The incoming A2A message
            
        Returns:
            A2AResponse to send back
        """
        pass
    
    @abstractmethod
    def can_handle(self, message: A2AMessage) -> bool:
        """
        Check if this handler can process the message.
        
        Args:
            message: The incoming message
            
        Returns:
            True if this handler can process the message
        """
        pass


class SimpleA2AHandler(A2AHandler):
    """
    Simple A2A handler that routes messages to a callback function.
    
    Usage:
        async def my_handler(message: A2AMessage) -> str:
            return f"Processed: {message.content}"
        
        handler = SimpleA2AHandler(
            agent_name="MyAgent",
            callback=my_handler,
        )
    """
    
    def __init__(
        self,
        agent_name: str,
        callback: Callable[[A2AMessage], Any],
    ):
        """
        Initialize the handler.
        
        Args:
            agent_name: Name of this agent
            callback: Async callback to process messages
        """
        self._agent_name = agent_name
        self._callback = callback
    
    async def handle(self, message: A2AMessage) -> A2AResponse:
        """Handle an incoming message."""
        try:
            result = await self._callback(message)
            
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.SUCCESS,
                content=str(result) if result else "Processed successfully",
            )
            
        except Exception as e:
            logger.error(f"Handler error: {e}")
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.ERROR,
                error=str(e),
            )
    
    def can_handle(self, message: A2AMessage) -> bool:
        """Check if message is addressed to this agent."""
        return message.recipient_agent == self._agent_name


@dataclass
class A2AServerConfig:
    """Configuration for A2A server."""
    agent_name: str
    host: str = "0.0.0.0"
    port: int = 8000
    path: str = "/a2a"
    require_auth: bool = False
    auth_token: Optional[str] = None


class A2AServer:
    """
    Server for receiving A2A messages from external agents.
    
    This server creates an HTTP endpoint that other agents can POST
    messages to. It routes messages to registered handlers.
    
    The server is designed to be integrated with FastAPI:
    
    Usage:
        # Create server
        a2a_server = A2AServer(
            config=A2AServerConfig(agent_name="MyAgent"),
        )
        
        # Register handlers
        a2a_server.register_handler(MyHandler())
        
        # Mount in FastAPI
        app = FastAPI()
        app.include_router(a2a_server.router, prefix="/a2a")
    """
    
    def __init__(self, config: A2AServerConfig):
        """
        Initialize the A2A server.
        
        Args:
            config: Server configuration
        """
        self._config = config
        self._handlers: list[A2AHandler] = []
        self._message_log: list[A2AMessage] = []
        
        logger.info(f"A2A Server initialized for {config.agent_name}")
    
    def register_handler(self, handler: A2AHandler) -> None:
        """Register a message handler."""
        self._handlers.append(handler)
        logger.info(f"Registered A2A handler: {handler.__class__.__name__}")
    
    async def process_message(self, message_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process an incoming A2A message.
        
        This method is called by the HTTP endpoint. It:
        1. Parses the message
        2. Finds an appropriate handler
        3. Invokes the handler
        4. Returns the response
        
        Args:
            message_data: Raw message dictionary from HTTP request
            
        Returns:
            Response dictionary to send back
        """
        try:
            message = A2AMessage.from_dict(message_data)
            
            logger.info(
                f"Received A2A message: {message.message_id} "
                f"from {message.sender_agent}"
            )
            
            # Log the message
            self._message_log.append(message)
            
            # Validate recipient
            if message.recipient_agent != self._config.agent_name:
                logger.warning(
                    f"Message addressed to {message.recipient_agent}, "
                    f"not {self._config.agent_name}"
                )
                return A2AResponse(
                    message_id=message.message_id,
                    conversation_id=message.conversation_id,
                    status=A2AStatus.ERROR,
                    error=f"Wrong recipient: expected {self._config.agent_name}",
                ).to_dict()
            
            # Find handler
            for handler in self._handlers:
                if handler.can_handle(message):
                    response = await handler.handle(message)
                    return response.to_dict()
            
            # No handler found
            logger.warning(f"No handler found for message {message.message_id}")
            return A2AResponse(
                message_id=message.message_id,
                conversation_id=message.conversation_id,
                status=A2AStatus.ERROR,
                error="No handler available for this message type",
            ).to_dict()
            
        except Exception as e:
            logger.error(f"Error processing A2A message: {e}")
            return A2AResponse(
                message_id=message_data.get("message_id", f"err-{uuid.uuid4().hex[:8]}"),
                conversation_id=message_data.get("conversation_id", "unknown"),
                status=A2AStatus.ERROR,
                error=f"Server error: {str(e)}",
            ).to_dict()
    
    def get_message_log(self, limit: int = 100) -> list[dict]:
        """Get recent message log."""
        return [m.to_dict() for m in self._message_log[-limit:]]
    
    @property
    def agent_name(self) -> str:
        """Get the agent name."""
        return self._config.agent_name
    
    @property
    def endpoint_path(self) -> str:
        """Get the configured endpoint path."""
        return self._config.path
    
    def create_fastapi_router(self):
        """
        Create a FastAPI router for the A2A endpoint.
        
        Returns:
            FastAPI APIRouter configured for A2A
        """
        from fastapi import APIRouter, HTTPException, Header
        from typing import Optional
        
        router = APIRouter()
        
        @router.post(self._config.path)
        async def receive_a2a_message(
            message: dict,
            x_a2a_sender: Optional[str] = Header(None),
            authorization: Optional[str] = Header(None),
        ):
            """Receive and process an A2A message."""
            
            # Check auth if required
            if self._config.require_auth:
                if not authorization or authorization != f"Bearer {self._config.auth_token}":
                    raise HTTPException(status_code=401, detail="Unauthorized")
            
            response = await self.process_message(message)
            return response
        
        @router.get(self._config.path + "/info")
        async def get_agent_info():
            """Get information about this A2A agent."""
            return {
                "agent_name": self._config.agent_name,
                "handlers": [h.__class__.__name__ for h in self._handlers],
                "message_count": len(self._message_log),
            }
        
        return router
