# ─────────────────────────────────────────────────────────────────────────────
# Observability Module
# ─────────────────────────────────────────────────────────────────────────────
# Provides telemetry, tracing, and metrics using OpenTelemetry.
# Integrates with Azure Monitor, Jaeger, or other OTLP backends.
# ─────────────────────────────────────────────────────────────────────────────

from observability.telemetry import (
    TelemetryConfig,
    TelemetryProvider,
    init_telemetry,
    get_tracer,
    get_meter,
)
from observability.tracing import (
    trace_agent_call,
    trace_tool_call,
    trace_orchestration,
    SpanContextManager,
)
from observability.metrics import (
    AgentMetrics,
    record_agent_latency,
    record_tool_call,
    increment_error_count,
)

__all__ = [
    # Telemetry
    "TelemetryConfig",
    "TelemetryProvider",
    "init_telemetry",
    "get_tracer",
    "get_meter",
    # Tracing
    "trace_agent_call",
    "trace_tool_call",
    "trace_orchestration",
    "SpanContextManager",
    # Metrics
    "AgentMetrics",
    "record_agent_latency",
    "record_tool_call",
    "increment_error_count",
]
