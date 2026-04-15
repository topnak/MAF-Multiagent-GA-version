# ─────────────────────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────────────────────
# FastAPI route definitions for the Multi-Agent API.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status

from api.models import (
    AgentInvokeRequest,
    AgentInvokeResponse,
    ListAgentsResponse,
    AgentInfo,
    OrchestrationRequest,
    OrchestrationResponse,
    ApprovalRequest,
    ApprovalResponse,
    ListApprovalsResponse,
    PendingApprovalInfo,
    HealthResponse,
    ServiceStatus,
    StatusEnum,
    ErrorDetail,
    PlanInfo,
    PlanStepInfo,
)

# Configure module logger
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Dependencies
# ─────────────────────────────────────────────────────────────────────────────

async def verify_auth_header(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """
    Verify authorization header.
    
    In production, this would validate JWT tokens via EntraID.
    """
    if not authorization:
        return None
    
    # For demo purposes, just extract the token
    if authorization.startswith("Bearer "):
        return authorization[7:]
    
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Agent Router
# ─────────────────────────────────────────────────────────────────────────────

agent_router = APIRouter(prefix="/agents", tags=["Agents"])


@agent_router.get(
    "",
    response_model=ListAgentsResponse,
    summary="List available agents",
    description="Get a list of all available agents and their capabilities.",
)
async def list_agents() -> ListAgentsResponse:
    """List all available agents."""
    # In production, this would come from the agent registry
    agents = [
        AgentInfo(
            name="MerchPlanner",
            description="Merchandise planning and inventory analysis agent",
            capabilities=["inventory_analysis", "assortment_planning", "sales_forecasting"],
            available_tools=["query_sales", "get_inventory"],
        ),
        AgentInfo(
            name="SpacePlanner",
            description="Store space planning and planogram optimization agent",
            capabilities=["planogram_design", "space_allocation", "fixture_planning"],
            available_tools=["query_space_data", "get_planograms"],
        ),
        AgentInfo(
            name="LoyaltyAgent",
            description="Customer loyalty and personalization agent",
            capabilities=["loyalty_analysis", "personalization", "offer_targeting"],
            available_tools=["get_customer_profile", "get_preferences"],
        ),
        AgentInfo(
            name="ProductsFinder",
            description="Product search and recommendation agent",
            capabilities=["product_search", "recommendations", "availability_check"],
            available_tools=["search_products", "get_inventory"],
        ),
        AgentInfo(
            name="CommercialSales",
            description="Commercial sales and B2B opportunity agent",
            capabilities=["lead_management", "opportunity_tracking", "account_analysis"],
            available_tools=["search_opportunities", "get_contacts"],
        ),
        AgentInfo(
            name="CampaignAnalyst",
            description="Marketing campaign analysis agent",
            capabilities=["campaign_analysis", "weather_impact", "promotional_planning"],
            available_tools=["get_weather_forecast", "query_campaign_data"],
        ),
    ]
    
    return ListAgentsResponse(agents=agents, count=len(agents))


@agent_router.get(
    "/{agent_name}",
    response_model=AgentInfo,
    summary="Get agent info",
    description="Get detailed information about a specific agent.",
)
async def get_agent(agent_name: str) -> AgentInfo:
    """Get information about a specific agent."""
    # In production, this would query the agent registry
    agents = await list_agents()
    
    for agent in agents.agents:
        if agent.name.lower() == agent_name.lower():
            return agent
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Agent not found: {agent_name}",
    )


@agent_router.post(
    "/invoke",
    response_model=AgentInvokeResponse,
    summary="Invoke an agent",
    description="Send a query to a specific agent and get a response.",
)
async def invoke_agent(
    request: AgentInvokeRequest,
    token: Optional[str] = Depends(verify_auth_header),
) -> AgentInvokeResponse:
    """Invoke an agent with a query."""
    logger.info(f"Invoking agent: {request.agent_name}")
    
    try:
        # In production, this would:
        # 1. Load the agent from factory
        # 2. Pass through middleware (auth, rbac, content safety)
        # 3. Invoke the agent
        # 4. Return the response
        
        # For demo, return a mock response
        return AgentInvokeResponse(
            status=StatusEnum.SUCCESS,
            agent_name=request.agent_name,
            content=f"[Mock Response] Processed query: {request.query[:100]}...",
            conversation_id=request.conversation_id or f"conv-{int(time.time())}",
            metadata={
                "tokens_used": 150,
                "latency_ms": 234.5,
            },
        )
        
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}")
        return AgentInvokeResponse(
            status=StatusEnum.ERROR,
            agent_name=request.agent_name,
            content="",
            error=ErrorDetail(
                code="AGENT_ERROR",
                message=str(e),
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration Router
# ─────────────────────────────────────────────────────────────────────────────

orchestration_router = APIRouter(prefix="/orchestration", tags=["Orchestration"])


@orchestration_router.post(
    "/run",
    response_model=OrchestrationResponse,
    summary="Run orchestration",
    description="Execute a goal using multi-agent orchestration.",
)
async def run_orchestration(
    request: OrchestrationRequest,
    token: Optional[str] = Depends(verify_auth_header),
) -> OrchestrationResponse:
    """Run orchestrated multi-agent execution."""
    logger.info(f"Starting orchestration: {request.orchestration_type.value}")
    
    try:
        # In production, this would:
        # 1. Select orchestrator based on type
        # 2. Create execution plan
        # 3. Optionally get human approval
        # 4. Execute plan
        # 5. Synthesize results
        
        # For demo, return mock response
        plan = PlanInfo(
            plan_id=f"plan-{int(time.time())}",
            goal=request.goal,
            steps=[
                PlanStepInfo(
                    step_id="step_1",
                    agent_name="MerchPlanner",
                    task="Analyze current category performance",
                    status="completed",
                    result="Category performance analysis complete",
                ),
                PlanStepInfo(
                    step_id="step_2",
                    agent_name="CampaignAnalyst",
                    task="Recommend promotional strategy",
                    status="completed",
                    result="Promotional recommendations ready",
                ),
            ],
            approved=not request.require_approval,
        )
        
        return OrchestrationResponse(
            status=StatusEnum.COMPLETED,
            result=f"[Mock Result] Orchestration complete for: {request.goal[:100]}",
            plan=plan,
        )
        
    except Exception as e:
        logger.error(f"Orchestration failed: {e}")
        return OrchestrationResponse(
            status=StatusEnum.FAILED,
            result="",
            error=ErrorDetail(
                code="ORCHESTRATION_ERROR",
                message=str(e),
            ),
        )


@orchestration_router.get(
    "/approvals",
    response_model=ListApprovalsResponse,
    summary="List pending approvals",
    description="Get all pending human approval requests.",
)
async def list_approvals(
    token: Optional[str] = Depends(verify_auth_header),
) -> ListApprovalsResponse:
    """List pending approval requests."""
    # In production, this would query the HumanApprovalManager
    return ListApprovalsResponse(approvals=[], count=0)


@orchestration_router.post(
    "/approvals/{request_id}",
    response_model=ApprovalResponse,
    summary="Handle approval",
    description="Approve or reject a pending request.",
)
async def handle_approval(
    request_id: str,
    request: ApprovalRequest,
    token: Optional[str] = Depends(verify_auth_header),
) -> ApprovalResponse:
    """Handle an approval action."""
    logger.info(f"Processing approval: {request_id} - {request.action.value}")
    
    # In production, this would call HumanApprovalManager.approve/reject
    return ApprovalResponse(
        success=True,
        request_id=request_id,
        status=request.action.value,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Health Router
# ─────────────────────────────────────────────────────────────────────────────

health_router = APIRouter(tags=["Health"])

_start_time = time.time()


@health_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the API and its dependencies.",
)
async def health_check() -> HealthResponse:
    """Perform health check."""
    uptime = time.time() - _start_time
    
    # In production, this would check actual service health
    services = [
        ServiceStatus(name="api", status="healthy", latency_ms=0.1),
        ServiceStatus(name="redis", status="healthy", latency_ms=1.2),
        ServiceStatus(name="llm", status="healthy", latency_ms=150.0),
    ]
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=uptime,
        services=services,
    )


@health_router.get(
    "/ready",
    summary="Readiness check",
    description="Check if the service is ready to accept requests.",
)
async def readiness_check() -> dict:
    """Check service readiness."""
    return {"ready": True}


@health_router.get(
    "/live",
    summary="Liveness check",
    description="Check if the service is alive.",
)
async def liveness_check() -> dict:
    """Check service liveness."""
    return {"alive": True}
