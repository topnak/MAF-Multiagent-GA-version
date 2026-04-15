# ─────────────────────────────────────────────────────────────────────────────
# Orchestration Module Tests
# ─────────────────────────────────────────────────────────────────────────────
# Unit tests for:
# - MagenticOrchestrator
# - TrafficRouter
# - ParallelExecutor
# - HumanApprovalManager
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from orchestration.magentic_orchestrator import (
    MagenticOrchestrator,
    MagenticPlan,
    PlanStep,
    PlanStepStatus,
)
from orchestration.traffic_router import (
    TrafficRouter,
    RoutingStrategy,
    RoutingDecision,
)
from orchestration.parallel_executor import (
    ParallelExecutor,
    ParallelTask,
    ParallelResult,
    AggregationStrategy,
)
from orchestration.human_approval import (
    HumanApprovalManager,
    ApprovalRequest,
    ApprovalStatus,
)
from agents.base_agent import AgentResponse


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_chat_client():
    """Create a mock chat client."""
    client = AsyncMock()
    client.chat_completion = AsyncMock(return_value={
        "content": '{"goal": "test", "steps": [{"step_id": "s1", "agent_name": "TestAgent", "task": "Do something", "dependencies": []}]}'
    })
    return client


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    agent = MagicMock()
    agent.name = "TestAgent"
    agent.description = "A test agent for unit testing"
    agent.invoke = AsyncMock(return_value=AgentResponse(
        content="Test response",
        agent_name="TestAgent",
    ))
    agent.to_dict = MagicMock(return_value={
        "name": "TestAgent",
        "description": "A test agent",
    })
    return agent


@pytest.fixture
def mock_agents(mock_agent):
    """Create a dictionary of mock agents."""
    agent1 = MagicMock()
    agent1.name = "MerchPlanner"
    agent1.description = "Agent for merchandise planning and inventory"
    agent1.invoke = AsyncMock(return_value=AgentResponse(
        content="Merchandise analysis complete",
        agent_name="MerchPlanner",
    ))
    agent1.to_dict = MagicMock(return_value={"name": "MerchPlanner"})
    
    agent2 = MagicMock()
    agent2.name = "SpacePlanner"
    agent2.description = "Agent for space planning and store layout"
    agent2.invoke = AsyncMock(return_value=AgentResponse(
        content="Space planning complete",
        agent_name="SpacePlanner",
    ))
    agent2.to_dict = MagicMock(return_value={"name": "SpacePlanner"})
    
    return {
        "MerchPlanner": agent1,
        "SpacePlanner": agent2,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PlanStep Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanStep:
    """Tests for PlanStep dataclass."""
    
    def test_create_plan_step(self):
        """Test creating a plan step."""
        step = PlanStep(
            step_id="step_1",
            agent_name="TestAgent",
            task="Do something",
        )
        
        assert step.step_id == "step_1"
        assert step.agent_name == "TestAgent"
        assert step.task == "Do something"
        assert step.status == PlanStepStatus.PENDING
        assert step.dependencies == []
    
    def test_plan_step_to_dict(self):
        """Test converting plan step to dictionary."""
        step = PlanStep(
            step_id="step_1",
            agent_name="TestAgent",
            task="Do something",
            dependencies=["step_0"],
        )
        
        data = step.to_dict()
        
        assert data["step_id"] == "step_1"
        assert data["agent_name"] == "TestAgent"
        assert data["status"] == "pending"
        assert data["dependencies"] == ["step_0"]


# ─────────────────────────────────────────────────────────────────────────────
# MagenticPlan Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMagenticPlan:
    """Tests for MagenticPlan."""
    
    def test_create_plan(self):
        """Test creating a plan."""
        plan = MagenticPlan(
            plan_id="plan-123",
            goal="Test goal",
        )
        
        assert plan.plan_id == "plan-123"
        assert plan.goal == "Test goal"
        assert plan.steps == []
        assert plan.approved is False
    
    def test_get_ready_steps(self):
        """Test getting ready steps (no dependencies)."""
        plan = MagenticPlan(
            plan_id="plan-123",
            goal="Test",
            steps=[
                PlanStep("s1", "Agent1", "Task 1"),
                PlanStep("s2", "Agent2", "Task 2", dependencies=["s1"]),
            ],
        )
        
        ready = plan.get_ready_steps()
        
        assert len(ready) == 1
        assert ready[0].step_id == "s1"
    
    def test_get_ready_steps_with_completed_deps(self):
        """Test getting ready steps when dependencies are met."""
        plan = MagenticPlan(
            plan_id="plan-123",
            goal="Test",
            steps=[
                PlanStep("s1", "Agent1", "Task 1", status=PlanStepStatus.COMPLETED),
                PlanStep("s2", "Agent2", "Task 2", dependencies=["s1"]),
            ],
        )
        
        ready = plan.get_ready_steps()
        
        assert len(ready) == 1
        assert ready[0].step_id == "s2"
    
    def test_is_complete(self):
        """Test checking if plan is complete."""
        plan = MagenticPlan(
            plan_id="plan-123",
            goal="Test",
            steps=[
                PlanStep("s1", "Agent1", "Task 1", status=PlanStepStatus.COMPLETED),
                PlanStep("s2", "Agent2", "Task 2", status=PlanStepStatus.COMPLETED),
            ],
        )
        
        assert plan.is_complete() is True
    
    def test_is_not_complete(self):
        """Test plan is not complete with pending steps."""
        plan = MagenticPlan(
            plan_id="plan-123",
            goal="Test",
            steps=[
                PlanStep("s1", "Agent1", "Task 1", status=PlanStepStatus.COMPLETED),
                PlanStep("s2", "Agent2", "Task 2", status=PlanStepStatus.PENDING),
            ],
        )
        
        assert plan.is_complete() is False


# ─────────────────────────────────────────────────────────────────────────────
# MagenticOrchestrator Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMagenticOrchestrator:
    """Tests for MagenticOrchestrator."""
    
    def test_init(self, mock_chat_client, mock_agents):
        """Test orchestrator initialization."""
        orchestrator = MagenticOrchestrator(
            client=mock_chat_client,
            agents=mock_agents,
        )
        
        assert orchestrator._client == mock_chat_client
        assert len(orchestrator._agents) == 2
    
    @pytest.mark.asyncio
    async def test_run_without_approval(self, mock_chat_client, mock_agents):
        """Test running orchestration without approval requirement."""
        orchestrator = MagenticOrchestrator(
            client=mock_chat_client,
            agents=mock_agents,
        )
        
        # Mock plan creation response
        mock_chat_client.chat_completion.return_value = {
            "content": '{"goal": "Analyze inventory", "steps": [{"step_id": "s1", "agent_name": "MerchPlanner", "task": "Analyze", "dependencies": []}]}'
        }
        
        result = await orchestrator.run(
            "Analyze inventory",
            require_approval=False,
        )
        
        assert result["status"] == "completed"
        assert "result" in result
        assert "plan" in result
    
    @pytest.mark.asyncio
    async def test_run_with_approval_rejected(self, mock_chat_client, mock_agents):
        """Test orchestration with rejected plan."""
        orchestrator = MagenticOrchestrator(
            client=mock_chat_client,
            agents=mock_agents,
            human_approval_callback=lambda plan: False,  # Always reject
        )
        
        result = await orchestrator.run(
            "Analyze inventory",
            require_approval=True,
        )
        
        assert result["status"] == "rejected"
    
    def test_get_agents(self, mock_chat_client, mock_agents):
        """Test getting agent information."""
        orchestrator = MagenticOrchestrator(
            client=mock_chat_client,
            agents=mock_agents,
        )
        
        agents = orchestrator.get_agents()
        
        assert "MerchPlanner" in agents
        assert "SpacePlanner" in agents


# ─────────────────────────────────────────────────────────────────────────────
# TrafficRouter Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTrafficRouter:
    """Tests for TrafficRouter."""
    
    def test_init(self, mock_chat_client, mock_agents):
        """Test router initialization."""
        router = TrafficRouter(
            client=mock_chat_client,
            agents=mock_agents,
        )
        
        assert router._strategy == RoutingStrategy.INTENT_BASED
        assert len(router._agents) == 2
    
    @pytest.mark.asyncio
    async def test_route_round_robin(self, mock_chat_client, mock_agents):
        """Test round-robin routing."""
        router = TrafficRouter(
            client=mock_chat_client,
            agents=mock_agents,
            strategy=RoutingStrategy.ROUND_ROBIN,
        )
        
        result1 = await router.route("First task")
        result2 = await router.route("Second task")
        
        assert result1["status"] == "completed"
        assert result2["status"] == "completed"
        # Round-robin should select different agents
        assert result1["routing"]["agent_name"] != result2["routing"]["agent_name"]
    
    @pytest.mark.asyncio
    async def test_route_capability_match(self, mock_chat_client, mock_agents):
        """Test capability-based routing."""
        router = TrafficRouter(
            client=mock_chat_client,
            agents=mock_agents,
            strategy=RoutingStrategy.CAPABILITY_MATCH,
        )
        
        result = await router.route("merchandise inventory planning")
        
        assert result["status"] == "completed"
        # Should match MerchPlanner due to "merchandise" keyword
        assert result["routing"]["agent_name"] == "MerchPlanner"
    
    def test_set_strategy(self, mock_chat_client, mock_agents):
        """Test changing routing strategy."""
        router = TrafficRouter(
            client=mock_chat_client,
            agents=mock_agents,
        )
        
        router.set_strategy(RoutingStrategy.ROUND_ROBIN)
        
        assert router._strategy == RoutingStrategy.ROUND_ROBIN


# ─────────────────────────────────────────────────────────────────────────────
# ParallelExecutor Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestParallelExecutor:
    """Tests for ParallelExecutor."""
    
    def test_init(self, mock_agents):
        """Test executor initialization."""
        executor = ParallelExecutor(
            agents=mock_agents,
            timeout_seconds=30.0,
        )
        
        assert executor._timeout == 30.0
        assert len(executor._agents) == 2
    
    @pytest.mark.asyncio
    async def test_run_parallel(self, mock_agents):
        """Test parallel execution."""
        executor = ParallelExecutor(agents=mock_agents)
        
        tasks = [
            ParallelTask("t1", "MerchPlanner", "Task 1"),
            ParallelTask("t2", "SpacePlanner", "Task 2"),
        ]
        
        result = await executor.run(tasks)
        
        assert result["summary"]["total_tasks"] == 2
        assert result["summary"]["completed"] == 2
        assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_run_with_missing_agent(self, mock_agents):
        """Test handling of missing agent."""
        executor = ParallelExecutor(agents=mock_agents)
        
        tasks = [
            ParallelTask("t1", "NonExistentAgent", "Task 1"),
        ]
        
        result = await executor.run(tasks)
        
        assert result["summary"]["failed"] == 1
        assert result["status"] == "partial"
    
    @pytest.mark.asyncio
    async def test_broadcast(self, mock_agents):
        """Test broadcast to all agents."""
        executor = ParallelExecutor(agents=mock_agents)
        
        result = await executor.broadcast("Common query")
        
        assert result["summary"]["total_tasks"] == 2
    
    @pytest.mark.asyncio
    async def test_aggregation_first(self, mock_agents):
        """Test FIRST aggregation strategy."""
        executor = ParallelExecutor(
            agents=mock_agents,
            aggregation=AggregationStrategy.FIRST,
        )
        
        tasks = [
            ParallelTask("t1", "MerchPlanner", "Task 1"),
            ParallelTask("t2", "SpacePlanner", "Task 2"),
        ]
        
        result = await executor.run(tasks)
        
        # Should return only one result
        assert len(result["results"]) == 1


# ─────────────────────────────────────────────────────────────────────────────
# HumanApprovalManager Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestHumanApprovalManager:
    """Tests for HumanApprovalManager."""
    
    def test_init(self):
        """Test manager initialization."""
        manager = HumanApprovalManager(
            default_timeout_minutes=30,
            auto_reject_on_timeout=True,
        )
        
        assert manager._default_timeout == timedelta(minutes=30)
        assert manager._auto_reject is True
    
    def test_approve(self):
        """Test approving a request."""
        manager = HumanApprovalManager()
        
        # Manually create a pending request
        request = ApprovalRequest(
            request_id="test-123",
            title="Test",
            description="Test approval",
            plan_data={"test": True},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        manager._pending["test-123"] = request
        
        # Create a future for it
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        future = loop.create_future()
        manager._futures["test-123"] = future
        
        result = manager.approve("test-123", "test_user", "Approved!")
        
        assert result is True
        assert request.status == ApprovalStatus.APPROVED
        assert request.responder == "test_user"
        
        loop.close()
    
    def test_reject(self):
        """Test rejecting a request."""
        manager = HumanApprovalManager()
        
        request = ApprovalRequest(
            request_id="test-456",
            title="Test",
            description="Test rejection",
            plan_data={"test": True},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        manager._pending["test-456"] = request
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        future = loop.create_future()
        manager._futures["test-456"] = future
        
        result = manager.reject("test-456", "test_user", "Not approved")
        
        assert result is True
        assert request.status == ApprovalStatus.REJECTED
        
        loop.close()
    
    def test_get_pending(self):
        """Test getting pending requests."""
        manager = HumanApprovalManager()
        
        request = ApprovalRequest(
            request_id="test-789",
            title="Test",
            description="Pending",
            plan_data={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        manager._pending["test-789"] = request
        
        pending = manager.get_pending()
        
        assert len(pending) == 1
        assert pending[0].request_id == "test-789"
    
    def test_auto_approve_callback(self):
        """Test auto-approve callback."""
        manager = HumanApprovalManager()
        callback = manager.create_auto_approve_callback()
        
        result = callback(None)
        
        assert result is True


# ─────────────────────────────────────────────────────────────────────────────
# ApprovalRequest Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestApprovalRequest:
    """Tests for ApprovalRequest."""
    
    def test_create_request(self):
        """Test creating an approval request."""
        request = ApprovalRequest(
            request_id="req-123",
            title="Test Approval",
            description="Please approve this",
            plan_data={"steps": []},
        )
        
        assert request.request_id == "req-123"
        assert request.status == ApprovalStatus.PENDING
    
    def test_is_expired_false(self):
        """Test request is not expired."""
        request = ApprovalRequest(
            request_id="req-123",
            title="Test",
            description="Test",
            plan_data={},
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        
        assert request.is_expired is False
    
    def test_is_expired_true(self):
        """Test request is expired."""
        request = ApprovalRequest(
            request_id="req-123",
            title="Test",
            description="Test",
            plan_data={},
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        
        assert request.is_expired is True
    
    def test_to_dict(self):
        """Test converting to dictionary."""
        request = ApprovalRequest(
            request_id="req-123",
            title="Test",
            description="Test description",
            plan_data={"key": "value"},
        )
        
        data = request.to_dict()
        
        assert data["request_id"] == "req-123"
        assert data["title"] == "Test"
        assert data["status"] == "pending"
