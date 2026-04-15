# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────
# Metrics collection for agent operations.
# Provides counters, histograms, and gauges for monitoring.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from observability.telemetry import get_meter

# Configure module logger
logger = logging.getLogger(__name__)


class AgentMetrics:
    """
    Metrics collection for agent operations.
    
    Provides:
    - Request counts (total, success, error)
    - Latency histograms
    - Token usage counters
    - Active request gauges
    
    Usage:
        metrics = AgentMetrics()
        
        with metrics.measure_latency("MerchPlanner"):
            # ... agent operation ...
            pass
        
        metrics.record_success("MerchPlanner")
    """
    
    def __init__(self, meter_name: str = "agent_metrics"):
        """
        Initialize agent metrics.
        
        Args:
            meter_name: Name for the meter
        """
        self._meter = get_meter(meter_name)
        
        # Counters
        self._request_counter = self._meter.create_counter(
            name="agent.requests",
            description="Total number of agent requests",
            unit="requests",
        )
        
        self._success_counter = self._meter.create_counter(
            name="agent.success",
            description="Number of successful agent requests",
            unit="requests",
        )
        
        self._error_counter = self._meter.create_counter(
            name="agent.errors",
            description="Number of failed agent requests",
            unit="requests",
        )
        
        self._token_counter = self._meter.create_counter(
            name="agent.tokens",
            description="Total tokens consumed",
            unit="tokens",
        )
        
        # Histograms
        self._latency_histogram = self._meter.create_histogram(
            name="agent.latency",
            description="Agent request latency",
            unit="ms",
        )
        
        # Tool call metrics
        self._tool_call_counter = self._meter.create_counter(
            name="mcp.tool_calls",
            description="Total MCP tool calls",
            unit="calls",
        )
        
        logger.info(f"AgentMetrics initialized with meter: {meter_name}")
    
    def record_request(self, agent_name: str, attributes: Optional[dict] = None) -> None:
        """Record a new request."""
        attrs = {"agent.name": agent_name}
        if attributes:
            attrs.update(attributes)
        self._request_counter.add(1, attrs)
    
    def record_success(self, agent_name: str, attributes: Optional[dict] = None) -> None:
        """Record a successful request."""
        attrs = {"agent.name": agent_name}
        if attributes:
            attrs.update(attributes)
        self._success_counter.add(1, attrs)
    
    def record_error(self, agent_name: str, error_type: str = "unknown", attributes: Optional[dict] = None) -> None:
        """Record a failed request."""
        attrs = {"agent.name": agent_name, "error.type": error_type}
        if attributes:
            attrs.update(attributes)
        self._error_counter.add(1, attrs)
    
    def record_latency(self, agent_name: str, latency_ms: float, attributes: Optional[dict] = None) -> None:
        """Record request latency."""
        attrs = {"agent.name": agent_name}
        if attributes:
            attrs.update(attributes)
        self._latency_histogram.record(latency_ms, attrs)
    
    def record_tokens(self, agent_name: str, input_tokens: int, output_tokens: int) -> None:
        """Record token usage."""
        self._token_counter.add(input_tokens, {
            "agent.name": agent_name,
            "token.type": "input",
        })
        self._token_counter.add(output_tokens, {
            "agent.name": agent_name,
            "token.type": "output",
        })
    
    def record_tool_call(self, server_name: str, tool_name: str, success: bool = True) -> None:
        """Record an MCP tool call."""
        self._tool_call_counter.add(1, {
            "mcp.server": server_name,
            "mcp.tool": tool_name,
            "success": str(success),
        })
    
    class _LatencyContext:
        """Context manager for measuring latency."""
        
        def __init__(self, metrics: "AgentMetrics", agent_name: str, attributes: dict):
            self._metrics = metrics
            self._agent_name = agent_name
            self._attributes = attributes
            self._start_time = None
        
        def __enter__(self):
            self._start_time = time.perf_counter()
            self._metrics.record_request(self._agent_name, self._attributes)
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration_ms = (time.perf_counter() - self._start_time) * 1000
            self._metrics.record_latency(self._agent_name, duration_ms, self._attributes)
            
            if exc_val:
                self._metrics.record_error(
                    self._agent_name,
                    error_type=exc_type.__name__ if exc_type else "unknown",
                    attributes=self._attributes,
                )
            else:
                self._metrics.record_success(self._agent_name, self._attributes)
            
            return False
    
    def measure_latency(self, agent_name: str, attributes: Optional[dict] = None):
        """
        Context manager for measuring operation latency.
        
        Usage:
            with metrics.measure_latency("MerchPlanner") as m:
                result = await agent.invoke(query)
        """
        return self._LatencyContext(self, agent_name, attributes or {})


# ─────────────────────────────────────────────────────────────────────────────
# Module-level convenience functions
# ─────────────────────────────────────────────────────────────────────────────

_default_metrics: Optional[AgentMetrics] = None


def _get_default_metrics() -> AgentMetrics:
    """Get or create default metrics instance."""
    global _default_metrics
    if _default_metrics is None:
        _default_metrics = AgentMetrics()
    return _default_metrics


def record_agent_latency(agent_name: str, latency_ms: float, attributes: Optional[dict] = None) -> None:
    """Record agent latency using default metrics."""
    _get_default_metrics().record_latency(agent_name, latency_ms, attributes)


def record_tool_call(server_name: str, tool_name: str, success: bool = True) -> None:
    """Record MCP tool call using default metrics."""
    _get_default_metrics().record_tool_call(server_name, tool_name, success)


def increment_error_count(agent_name: str, error_type: str = "unknown") -> None:
    """Increment error count using default metrics."""
    _get_default_metrics().record_error(agent_name, error_type)
