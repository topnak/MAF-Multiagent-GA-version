# ─────────────────────────────────────────────────────────────────────────────
# Orchestration Module
# ─────────────────────────────────────────────────────────────────────────────
# Implements MAF 1.0 GA orchestration patterns:
# - MagenticOrchestration: Task-ledger planning with HITL
# - HandoffOrchestration: Traffic routing
# - ConcurrentOrchestration: Parallel execution
# ─────────────────────────────────────────────────────────────────────────────

from .magentic_orchestrator import (
    MagenticOrchestrator,
    MagenticPlan,
    PlanStep,
    PlanStepStatus,
)
from .traffic_router import TrafficRouter, RoutingDecision, RoutingStrategy
from .parallel_executor import (
    ParallelExecutor,
    ParallelTask,
    ParallelResult,
    AggregationStrategy,
)
from .human_approval import HumanApprovalManager, ApprovalRequest, ApprovalStatus

__all__ = [
    # Magentic Orchestration
    "MagenticOrchestrator",
    "MagenticPlan",
    "PlanStep",
    "PlanStepStatus",
    # Traffic Routing (Handoff)
    "TrafficRouter",
    "RoutingDecision",
    "RoutingStrategy",
    # Parallel Execution (Concurrent)
    "ParallelExecutor",
    "ParallelTask",
    "ParallelResult",
    "AggregationStrategy",
    # Human-in-the-Loop
    "HumanApprovalManager",
    "ApprovalRequest",
    "ApprovalStatus",
]
