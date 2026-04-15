# ─────────────────────────────────────────────────────────────────────────────
# Audit Log Middleware
# ─────────────────────────────────────────────────────────────────────────────
# Provides comprehensive audit logging for agent interactions.
# Logs all requests and responses for compliance and debugging.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import structlog

from .base_middleware import (
    MiddlewareBase,
    MiddlewareContext,
    MiddlewareResponse,
    NextHandler,
    NextResponseHandler,
)

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class AuditLogEntry:
    """
    Represents a single audit log entry.
    
    Attributes:
        request_id: Unique identifier for the request
        timestamp: When the event occurred
        event_type: Type of event (request, response, error)
        user_id: ID of the user making the request
        user_email: Email of the user
        agent_name: Name of the target agent
        message_preview: Preview of the message content
        response_preview: Preview of the response content
        duration_ms: Time taken to process (for responses)
        was_blocked: Whether the request/response was blocked
        block_reason: Reason for blocking (if blocked)
        metadata: Additional metadata
    """
    request_id: str
    timestamp: datetime
    event_type: str
    user_id: str = ""
    user_email: str = ""
    agent_name: str = ""
    message_preview: str = ""
    response_preview: str = ""
    duration_ms: float = 0.0
    was_blocked: bool = False
    block_reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "user_id": self.user_id,
            "user_email": self.user_email,
            "agent_name": self.agent_name,
            "message_preview": self.message_preview,
            "response_preview": self.response_preview,
            "duration_ms": self.duration_ms,
            "was_blocked": self.was_blocked,
            "block_reason": self.block_reason,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


@dataclass
class AuditLogConfig:
    """
    Configuration for audit log middleware.
    
    Attributes:
        log_requests: Whether to log incoming requests
        log_responses: Whether to log outgoing responses
        log_blocked: Whether to log blocked requests/responses
        message_preview_length: Maximum length of message preview
        response_preview_length: Maximum length of response preview
        include_full_messages: Include full messages in metadata
        log_pii: Whether to log messages that may contain PII
        custom_logger: Custom logger function
        enabled: Whether audit logging is enabled
    """
    # What to log
    log_requests: bool = True
    log_responses: bool = True
    log_blocked: bool = True
    
    # Preview lengths
    message_preview_length: int = 200
    response_preview_length: int = 200
    
    # Full message logging (use with caution - may contain sensitive data)
    include_full_messages: bool = False
    
    # PII handling
    log_pii: bool = False  # If False, skip logging messages with detected PII
    
    # Custom logger (receives AuditLogEntry)
    custom_logger: Optional[Callable[[AuditLogEntry], None]] = None
    
    # Whether audit logging is enabled
    enabled: bool = True


class AuditLogMiddleware(MiddlewareBase):
    """
    Audit logging middleware for MAF agents.
    
    This middleware provides comprehensive audit logging for all agent
    interactions. Logs are written using structlog for structured logging
    and can be exported to external systems (SIEM, analytics, etc.).
    
    Features:
    - Request and response logging
    - Configurable preview lengths
    - Duration tracking
    - Block reason logging
    - Custom logger support
    - PII-aware logging
    
    Usage:
        config = AuditLogConfig()
        audit = AuditLogMiddleware(config)
        
        # In pipeline (should be first for accurate timing)
        pipeline = MiddlewarePipeline([audit])
        response = await pipeline.execute(context, agent_handler)
    
    Log Output:
        Logs are written in structured format:
        {
            "request_id": "uuid",
            "timestamp": "ISO8601",
            "event_type": "request|response|blocked",
            "user_id": "...",
            "agent_name": "...",
            ...
        }
    """
    
    def __init__(self, config: Optional[AuditLogConfig] = None):
        """
        Initialize audit log middleware.
        
        Args:
            config: Audit log configuration. If None, uses default config.
        """
        self.config = config or AuditLogConfig()
        
        # Initialize structlog processor
        self._structlog = structlog.get_logger("audit")
        
        # Track request start times for duration calculation
        self._request_times: dict[str, datetime] = {}
    
    async def on_request(
        self,
        context: MiddlewareContext,
        next_handler: NextHandler,
    ) -> MiddlewareResponse:
        """
        Log incoming request and track timing.
        
        Args:
            context: Request context
            next_handler: Next middleware/agent in chain
            
        Returns:
            MiddlewareResponse: Response from chain
        """
        if not self.config.enabled:
            return await next_handler(context)
        
        # Generate request ID if not present
        if not context.request_id:
            context.request_id = str(uuid.uuid4())
        
        # Record start time
        start_time = datetime.now(timezone.utc)
        self._request_times[context.request_id] = start_time
        
        # Get message preview
        last_message = context.get_last_message()
        message_content = last_message.get("content", "") if last_message else ""
        message_preview = self._truncate(message_content, self.config.message_preview_length)
        
        # Check for PII flag from content safety middleware
        has_pii = context.get_metadata("pii_redacted_input", False)
        if has_pii and not self.config.log_pii:
            message_preview = "[PII REDACTED - Content not logged]"
        
        # Log the request
        if self.config.log_requests:
            entry = AuditLogEntry(
                request_id=context.request_id,
                timestamp=start_time,
                event_type="request",
                user_id=context.user.user_id if context.user else "",
                user_email=context.user.email if context.user else "",
                agent_name=context.agent_name,
                message_preview=message_preview,
                metadata={
                    "message_length": len(message_content),
                    "has_pii": has_pii,
                },
            )
            self._log_entry(entry)
        
        # Continue to next handler
        response = await next_handler(context)
        
        return response
    
    async def on_response(
        self,
        context: MiddlewareContext,
        response: MiddlewareResponse,
        next_handler: NextResponseHandler,
    ) -> MiddlewareResponse:
        """
        Log outgoing response with timing information.
        
        Args:
            context: Original request context
            response: Response from agent
            next_handler: Next middleware in chain
            
        Returns:
            MiddlewareResponse: Response passed through
        """
        if not self.config.enabled:
            return await next_handler(context, response)
        
        # Calculate duration
        end_time = datetime.now(timezone.utc)
        start_time = self._request_times.pop(context.request_id, end_time)
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        # Get response preview
        response_preview = self._truncate(response.content, self.config.response_preview_length)
        
        # Check for PII in response
        has_pii = response.metadata.get("pii_redacted_output", False)
        if has_pii and not self.config.log_pii:
            response_preview = "[PII REDACTED - Content not logged]"
        
        # Log response or blocked
        if response.blocked:
            if self.config.log_blocked:
                entry = AuditLogEntry(
                    request_id=context.request_id,
                    timestamp=end_time,
                    event_type="blocked",
                    user_id=context.user.user_id if context.user else "",
                    user_email=context.user.email if context.user else "",
                    agent_name=context.agent_name,
                    response_preview=response_preview,
                    duration_ms=duration_ms,
                    was_blocked=True,
                    block_reason=response.block_reason,
                    metadata=response.metadata,
                )
                self._log_entry(entry)
        else:
            if self.config.log_responses:
                entry = AuditLogEntry(
                    request_id=context.request_id,
                    timestamp=end_time,
                    event_type="response",
                    user_id=context.user.user_id if context.user else "",
                    user_email=context.user.email if context.user else "",
                    agent_name=context.agent_name,
                    response_preview=response_preview,
                    duration_ms=duration_ms,
                    was_blocked=False,
                    metadata={
                        "response_length": len(response.content),
                        "has_pii": has_pii,
                    },
                )
                self._log_entry(entry)
        
        return await next_handler(context, response)
    
    def _truncate(self, text: str, max_length: int) -> str:
        """
        Truncate text to maximum length with ellipsis.
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            
        Returns:
            str: Truncated text
        """
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."
    
    def _log_entry(self, entry: AuditLogEntry) -> None:
        """
        Log an audit entry.
        
        Uses structlog for structured logging and optionally calls
        a custom logger function.
        
        Args:
            entry: Audit log entry to log
        """
        # Log with structlog (structured logging)
        log_method = self._structlog.info
        if entry.was_blocked:
            log_method = self._structlog.warning
        
        log_method(
            "audit_event",
            request_id=entry.request_id,
            event_type=entry.event_type,
            user_id=entry.user_id,
            agent_name=entry.agent_name,
            duration_ms=entry.duration_ms,
            was_blocked=entry.was_blocked,
            block_reason=entry.block_reason,
        )
        
        # Call custom logger if provided
        if self.config.custom_logger:
            try:
                self.config.custom_logger(entry)
            except Exception as e:
                logger.error(f"Custom audit logger failed: {e}")
