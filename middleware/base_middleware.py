# ─────────────────────────────────────────────────────────────────────────────
# Base Middleware Module
# ─────────────────────────────────────────────────────────────────────────────
# Provides the base classes for implementing MAF 1.0 GA middleware pattern.
# Middleware can process requests before they reach agents and responses
# before they return to users.
# ─────────────────────────────────────────────────────────────────────────────

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from auth.entra_auth import UserContext


@dataclass
class MiddlewareContext:
    """
    Context object passed through the middleware pipeline.
    
    This context carries all information needed for middleware to make
    decisions about request processing, including user identity, agent
    information, and arbitrary metadata.
    
    Attributes:
        user: Authenticated user context (from EntraID)
        agent_name: Name of the target agent
        messages: List of messages in the conversation
        metadata: Arbitrary metadata for middleware communication
        request_id: Unique identifier for the request
    """
    user: Optional[UserContext] = None
    agent_name: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    
    def add_message(self, role: str, content: str) -> None:
        """
        Add a message to the conversation.
        
        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.messages.append({"role": role, "content": content})
    
    def get_last_message(self) -> Optional[dict[str, Any]]:
        """
        Get the last message in the conversation.
        
        Returns:
            dict: Last message, or None if no messages
        """
        return self.messages[-1] if self.messages else None
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata value for downstream middleware.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)


@dataclass
class MiddlewareResponse:
    """
    Response from an agent, passing through middleware.
    
    Attributes:
        content: Response content (text)
        agent_name: Name of the agent that generated the response
        metadata: Response metadata
        blocked: Whether the response was blocked by middleware
        block_reason: Reason for blocking (if blocked)
    """
    content: str = ""
    agent_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    blocked: bool = False
    block_reason: str = ""


# Type alias for the next handler in the middleware chain
NextHandler = Callable[[MiddlewareContext], "MiddlewareResponse"]
NextResponseHandler = Callable[[MiddlewareContext, MiddlewareResponse], MiddlewareResponse]


class MiddlewareBase(ABC):
    """
    Abstract base class for MAF 1.0 GA middleware.
    
    Middleware components can intercept and modify both requests (before
    they reach agents) and responses (before they return to users).
    
    Implementation Pattern:
        class MyMiddleware(MiddlewareBase):
            async def on_request(self, context, next_handler):
                # Pre-processing
                modified_context = self.process_request(context)
                # Call next middleware
                response = await next_handler(modified_context)
                return response
            
            async def on_response(self, context, response, next_handler):
                # Post-processing
                modified_response = self.process_response(response)
                return await next_handler(context, modified_response)
    
    Usage:
        pipeline = MiddlewarePipeline([
            AuditLogMiddleware(),
            RBACMiddleware(),
            ContentSafetyMiddleware(),
        ])
        response = await pipeline.execute(context, agent_handler)
    """
    
    @abstractmethod
    async def on_request(
        self,
        context: MiddlewareContext,
        next_handler: NextHandler,
    ) -> MiddlewareResponse:
        """
        Process an incoming request before it reaches the agent.
        
        This method is called for every request passing through the middleware.
        Implementations should call next_handler to continue the chain, or
        return a MiddlewareResponse directly to short-circuit (e.g., for
        blocking requests).
        
        Args:
            context: Request context with user, messages, and metadata
            next_handler: Function to call the next middleware/agent
            
        Returns:
            MiddlewareResponse: Response from agent or middleware
        """
        pass
    
    async def on_response(
        self,
        context: MiddlewareContext,
        response: MiddlewareResponse,
        next_handler: NextResponseHandler,
    ) -> MiddlewareResponse:
        """
        Process an outgoing response before it returns to the user.
        
        This method is called for every response passing through the middleware.
        Default implementation passes through without modification.
        
        Args:
            context: Original request context
            response: Response from agent
            next_handler: Function to call the next middleware
            
        Returns:
            MiddlewareResponse: Possibly modified response
        """
        # Default: pass through without modification
        return await next_handler(context, response)


class MiddlewarePipeline:
    """
    Executes a chain of middleware in order.
    
    The pipeline executes middleware in the order they are provided:
    - Requests flow forward through the chain
    - Responses flow backward through the chain
    
    Example:
        pipeline = MiddlewarePipeline([
            AuditLogMiddleware(),      # 1st for requests, last for responses
            RBACMiddleware(),          # 2nd for requests, 2nd-to-last for responses
            ContentSafetyMiddleware(), # 3rd for requests, 1st for responses
        ])
        
        # Execute with an agent handler
        response = await pipeline.execute(context, agent.invoke)
    """
    
    def __init__(self, middleware: list[MiddlewareBase]):
        """
        Initialize the middleware pipeline.
        
        Args:
            middleware: List of middleware to execute in order
        """
        self.middleware = middleware
    
    async def execute(
        self,
        context: MiddlewareContext,
        agent_handler: Callable[[MiddlewareContext], MiddlewareResponse],
    ) -> MiddlewareResponse:
        """
        Execute the middleware pipeline with the given agent handler.
        
        Args:
            context: Request context
            agent_handler: Function to call the agent
            
        Returns:
            MiddlewareResponse: Final response after all middleware
        """
        # Build the middleware chain
        async def build_chain(index: int) -> NextHandler:
            if index >= len(self.middleware):
                # End of chain - call the agent
                async def final_handler(ctx: MiddlewareContext) -> MiddlewareResponse:
                    return agent_handler(ctx)
                return final_handler
            
            # Get current middleware and next handler
            current_middleware = self.middleware[index]
            next_handler = await build_chain(index + 1)
            
            # Return handler that calls current middleware
            async def handler(ctx: MiddlewareContext) -> MiddlewareResponse:
                return await current_middleware.on_request(ctx, next_handler)
            
            return handler
        
        # Start the chain
        chain = await build_chain(0)
        response = await chain(context)
        
        # Process response through middleware in reverse order
        for middleware in reversed(self.middleware):
            async def identity_handler(
                ctx: MiddlewareContext,
                resp: MiddlewareResponse
            ) -> MiddlewareResponse:
                return resp
            
            response = await middleware.on_response(context, response, identity_handler)
        
        return response
    
    def add(self, middleware: MiddlewareBase) -> "MiddlewarePipeline":
        """
        Add middleware to the pipeline.
        
        Args:
            middleware: Middleware to add
            
        Returns:
            Self for chaining
        """
        self.middleware.append(middleware)
        return self
    
    def insert(self, index: int, middleware: MiddlewareBase) -> "MiddlewarePipeline":
        """
        Insert middleware at a specific position.
        
        Args:
            index: Position to insert at
            middleware: Middleware to insert
            
        Returns:
            Self for chaining
        """
        self.middleware.insert(index, middleware)
        return self
