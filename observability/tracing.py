# ─────────────────────────────────────────────────────────────────────────────
# Tracing Helpers
# ─────────────────────────────────────────────────────────────────────────────
# Decorators and utilities for tracing agent operations.
# ─────────────────────────────────────────────────────────────────────────────

import functools
import logging
from contextlib import contextmanager
from typing import Any, Callable, Optional

from observability.telemetry import get_tracer

# Configure module logger
logger = logging.getLogger(__name__)


class SpanContextManager:
    """
    Context manager for creating and managing spans.
    
    Usage:
        with SpanContextManager("operation_name") as span:
            span.set_attribute("key", "value")
            # ... do work ...
    """
    
    def __init__(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
        tracer_name: Optional[str] = None,
    ):
        """
        Initialize the span context manager.
        
        Args:
            name: Span name
            attributes: Initial attributes to set
            tracer_name: Optional tracer name
        """
        self._name = name
        self._attributes = attributes or {}
        self._tracer_name = tracer_name
        self._span = None
    
    def __enter__(self):
        tracer = get_tracer(self._tracer_name)
        self._span = tracer.start_as_current_span(self._name)
        span = self._span.__enter__()
        
        # Set initial attributes
        for key, value in self._attributes.items():
            span.set_attribute(key, value)
        
        return span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self._span.__exit__(exc_type, exc_val, exc_tb)
            # Record the exception
            span = self._span
            if hasattr(span, 'record_exception'):
                span.record_exception(exc_val)
        else:
            self._span.__exit__(None, None, None)
        
        return False


def trace_agent_call(
    agent_name: Optional[str] = None,
    operation: str = "invoke",
) -> Callable:
    """
    Decorator to trace agent calls.
    
    Creates a span for each agent invocation with relevant attributes.
    
    Usage:
        @trace_agent_call(agent_name="MerchPlanner")
        async def invoke(self, query: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Try to get agent name from self if not provided
            name = agent_name
            if not name and args and hasattr(args[0], 'name'):
                name = args[0].name
            
            tracer = get_tracer("agent")
            span_name = f"agent.{name or 'unknown'}.{operation}"
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("agent.name", name or "unknown")
                span.set_attribute("agent.operation", operation)
                
                # Get query from args/kwargs
                query = kwargs.get('query') or kwargs.get('task')
                if query is None and len(args) > 1:
                    query = args[1]
                
                if query:
                    span.set_attribute("agent.query_length", len(str(query)))
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("agent.success", True)
                    
                    if hasattr(result, 'content'):
                        span.set_attribute("agent.response_length", len(str(result.content)))
                    
                    return result
                    
                except Exception as e:
                    span.set_attribute("agent.success", False)
                    span.set_attribute("agent.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_tool_call(
    tool_name: Optional[str] = None,
    server_name: Optional[str] = None,
) -> Callable:
    """
    Decorator to trace MCP tool calls.
    
    Usage:
        @trace_tool_call(server_name="snowflake_mcp")
        async def execute_query(self, query: str) -> str:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            name = tool_name or func.__name__
            server = server_name
            
            if not server and args and hasattr(args[0], 'name'):
                server = args[0].name
            
            tracer = get_tracer("mcp")
            span_name = f"mcp.{server or 'unknown'}.{name}"
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("mcp.server", server or "unknown")
                span.set_attribute("mcp.tool", name)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("mcp.success", True)
                    return result
                    
                except Exception as e:
                    span.set_attribute("mcp.success", False)
                    span.set_attribute("mcp.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


def trace_orchestration(
    orchestration_type: str = "magentic",
) -> Callable:
    """
    Decorator to trace orchestration operations.
    
    Usage:
        @trace_orchestration(orchestration_type="magentic")
        async def run(self, goal: str) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer("orchestration")
            span_name = f"orchestration.{orchestration_type}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("orchestration.type", orchestration_type)
                
                # Get goal from args
                goal = kwargs.get('goal')
                if goal is None and len(args) > 1:
                    goal = args[1]
                
                if goal:
                    span.set_attribute("orchestration.goal_length", len(str(goal)))
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("orchestration.success", True)
                    
                    if isinstance(result, dict):
                        span.set_attribute("orchestration.status", result.get("status", "unknown"))
                    
                    return result
                    
                except Exception as e:
                    span.set_attribute("orchestration.success", False)
                    span.set_attribute("orchestration.error", str(e))
                    span.record_exception(e)
                    raise
        
        return wrapper
    return decorator


@contextmanager
def trace_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    tracer_name: Optional[str] = None,
):
    """
    Context manager for creating a trace span.
    
    Usage:
        with trace_span("my_operation", {"key": "value"}) as span:
            # ... do work ...
            span.add_event("checkpoint")
    """
    tracer = get_tracer(tracer_name)
    
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        
        yield span
