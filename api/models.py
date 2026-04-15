# ─────────────────────────────────────────────────────────────────────────────
# API Models
# ─────────────────────────────────────────────────────────────────────────────
# Pydantic models for API request/response validation.
# ─────────────────────────────────────────────────────────────────────────────

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Common Models
# ─────────────────────────────────────────────────────────────────────────────

class StatusEnum(str, Enum):
    """Common status values."""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional details")


# ─────────────────────────────────────────────────────────────────────────────
# Agent Models
# ─────────────────────────────────────────────────────────────────────────────

class AgentInvokeRequest(BaseModel):
    """Request to invoke an agent."""
    
    agent_name: str = Field(
        ...,
        description="Name of the agent to invoke",
        example="MerchPlanner",
    )
    query: str = Field(
        ...,
        description="Query or task for the agent",
        example="Analyze paint category performance for Q4",
    )
    context: Optional[dict[str, Any]] = Field(
        None,
        description="Optional context to pass to the agent",
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Optional conversation ID for stateful interactions",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "MerchPlanner",
                "query": "What is the sell-through rate for the paint category?",
                "context": {"region": "West"},
            }
        }


class AgentInvokeResponse(BaseModel):
    """Response from agent invocation."""
    
    status: StatusEnum = Field(..., description="Result status")
    agent_name: str = Field(..., description="Name of the agent that responded")
    content: str = Field(..., description="Agent's response content")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    tool_calls: Optional[list[dict]] = Field(None, description="Tools called by the agent")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")
    error: Optional[ErrorDetail] = Field(None, description="Error details if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "agent_name": "MerchPlanner",
                "content": "The paint category has a sell-through rate of 72%...",
                "conversation_id": "conv-abc123",
            }
        }


class AgentInfo(BaseModel):
    """Information about an available agent."""
    
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    capabilities: Optional[list[str]] = Field(None, description="Agent capabilities")
    available_tools: Optional[list[str]] = Field(None, description="Available MCP tools")


class ListAgentsResponse(BaseModel):
    """Response listing available agents."""
    
    agents: list[AgentInfo] = Field(..., description="List of available agents")
    count: int = Field(..., description="Number of agents")


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration Models
# ─────────────────────────────────────────────────────────────────────────────

class OrchestrationTypeEnum(str, Enum):
    """Type of orchestration."""
    MAGENTIC = "magentic"
    ROUTING = "routing"
    PARALLEL = "parallel"


class OrchestrationRequest(BaseModel):
    """Request for orchestrated execution."""
    
    goal: str = Field(
        ...,
        description="Goal or task to accomplish",
        example="Analyze paint category and recommend promotional strategy",
    )
    orchestration_type: OrchestrationTypeEnum = Field(
        OrchestrationTypeEnum.MAGENTIC,
        description="Type of orchestration to use",
    )
    require_approval: bool = Field(
        False,
        description="Whether to require human approval for the plan",
    )
    context: Optional[dict[str, Any]] = Field(
        None,
        description="Optional context for the orchestration",
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "goal": "Analyze paint category performance and recommend markdown strategy",
                "orchestration_type": "magentic",
                "require_approval": True,
            }
        }


class PlanStepInfo(BaseModel):
    """Information about a plan step."""
    
    step_id: str = Field(..., description="Step ID")
    agent_name: str = Field(..., description="Agent assigned to this step")
    task: str = Field(..., description="Task description")
    status: str = Field(..., description="Step status")
    result: Optional[str] = Field(None, description="Step result")


class PlanInfo(BaseModel):
    """Information about an execution plan."""
    
    plan_id: str = Field(..., description="Plan ID")
    goal: str = Field(..., description="Plan goal")
    steps: list[PlanStepInfo] = Field(..., description="Plan steps")
    approved: bool = Field(..., description="Whether plan was approved")


class OrchestrationResponse(BaseModel):
    """Response from orchestrated execution."""
    
    status: StatusEnum = Field(..., description="Execution status")
    result: str = Field(..., description="Synthesized result")
    plan: Optional[PlanInfo] = Field(None, description="Execution plan")
    agent_responses: Optional[dict[str, Any]] = Field(None, description="Individual agent responses")
    error: Optional[ErrorDetail] = Field(None, description="Error details if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "result": "Based on analysis, the paint category shows...",
                "plan": {
                    "plan_id": "plan-abc123",
                    "goal": "Analyze paint category",
                    "steps": [],
                    "approved": True,
                },
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# Approval Models
# ─────────────────────────────────────────────────────────────────────────────

class ApprovalActionEnum(str, Enum):
    """Approval action."""
    APPROVE = "approve"
    REJECT = "reject"


class ApprovalRequest(BaseModel):
    """Request to approve or reject a plan."""
    
    request_id: str = Field(..., description="Approval request ID")
    action: ApprovalActionEnum = Field(..., description="Approval action")
    comments: Optional[str] = Field(None, description="Optional comments")


class ApprovalResponse(BaseModel):
    """Response from approval action."""
    
    success: bool = Field(..., description="Whether action succeeded")
    request_id: str = Field(..., description="Approval request ID")
    status: str = Field(..., description="New status")


class PendingApprovalInfo(BaseModel):
    """Information about a pending approval."""
    
    request_id: str = Field(..., description="Request ID")
    title: str = Field(..., description="Approval title")
    description: str = Field(..., description="Approval description")
    created_at: datetime = Field(..., description="When created")
    expires_at: Optional[datetime] = Field(None, description="When expires")


class ListApprovalsResponse(BaseModel):
    """Response listing pending approvals."""
    
    approvals: list[PendingApprovalInfo] = Field(..., description="Pending approvals")
    count: int = Field(..., description="Number of pending approvals")


# ─────────────────────────────────────────────────────────────────────────────
# Health Models
# ─────────────────────────────────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    """Status of a service dependency."""
    
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    latency_ms: Optional[float] = Field(None, description="Latency in ms")


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="API version")
    uptime_seconds: float = Field(..., description="Uptime in seconds")
    services: list[ServiceStatus] = Field(..., description="Service statuses")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "uptime_seconds": 3600.5,
                "services": [
                    {"name": "redis", "status": "healthy", "latency_ms": 1.2},
                ],
            }
        }
