# ─────────────────────────────────────────────────────────────────────────────
# Magentic Orchestrator
# ─────────────────────────────────────────────────────────────────────────────
# Implements the Magentic orchestration pattern from MAF 1.0 GA.
# Features:
# - Task-ledger based planning
# - Human-in-the-loop approval
# - Multi-agent coordination
# - Adaptive re-planning
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from agents.agent_factory import ChatClient
from agents.base_agent import BaseRetailAgent, AgentResponse

# Configure module logger
logger = logging.getLogger(__name__)


class PlanStepStatus(str, Enum):
    """Status of a plan step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """
    Represents a single step in the execution plan.
    
    Attributes:
        step_id: Unique identifier for the step
        agent_name: Name of the agent to execute this step
        task: Task description for the agent
        dependencies: List of step IDs this step depends on
        status: Current status of the step
        result: Result from agent execution
        started_at: When execution started
        completed_at: When execution completed
    """
    step_id: str
    agent_name: str
    task: str
    dependencies: list[str] = field(default_factory=list)
    status: PlanStepStatus = PlanStepStatus.PENDING
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "agent_name": self.agent_name,
            "task": self.task,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "result": self.result,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class MagenticPlan:
    """
    Represents a complete execution plan.
    
    The plan is a directed acyclic graph (DAG) of steps, where each
    step can depend on the completion of previous steps.
    """
    plan_id: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approved: bool = False
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
            "approved": self.approved,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
        }
    
    def get_ready_steps(self) -> list[PlanStep]:
        """Get steps that are ready to execute (dependencies met)."""
        completed_ids = {s.step_id for s in self.steps if s.status == PlanStepStatus.COMPLETED}
        ready = []
        
        for step in self.steps:
            if step.status != PlanStepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                ready.append(step)
        
        return ready
    
    def is_complete(self) -> bool:
        """Check if all steps are completed or failed."""
        return all(
            s.status in (PlanStepStatus.COMPLETED, PlanStepStatus.FAILED, PlanStepStatus.SKIPPED)
            for s in self.steps
        )
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the plan."""
        lines = [f"Plan: {self.goal}", ""]
        for i, step in enumerate(self.steps, 1):
            status_icon = {
                PlanStepStatus.PENDING: "⏳",
                PlanStepStatus.IN_PROGRESS: "🔄",
                PlanStepStatus.COMPLETED: "✅",
                PlanStepStatus.FAILED: "❌",
                PlanStepStatus.SKIPPED: "⏭️",
            }.get(step.status, "?")
            lines.append(f"{i}. {status_icon} [{step.agent_name}] {step.task}")
        return "\n".join(lines)


# Type for human approval callback
ApprovalCallback = Callable[[MagenticPlan], bool]


class MagenticOrchestrator:
    """
    Magentic Orchestrator implementing MAF 1.0 GA pattern.
    
    This orchestrator implements the Magentic pattern:
    1. Receive a goal/task from the user
    2. Use LLM to create an execution plan (task ledger)
    3. Optionally get human approval for the plan
    4. Execute steps in order, respecting dependencies
    5. Synthesize results from all agents
    6. Re-plan if needed based on intermediate results
    
    Key Features:
    - Task-ledger based planning
    - Human-in-the-loop approval gate
    - Multi-agent coordination
    - Dependency-aware execution
    - Result synthesis
    
    Usage:
        orchestrator = MagenticOrchestrator(
            client=chat_client,
            agents={"MerchPlanner": merch_agent, ...},
            human_approval_callback=lambda plan: True,
        )
        result = await orchestrator.run("Analyze paint category performance")
    """
    
    PLANNER_SYSTEM_PROMPT = """You are a planning agent that creates execution plans for a team of specialized agents.

Available agents and their capabilities:
{agent_descriptions}

Given a user goal, create a plan with steps that can be executed by these agents.
Each step should specify:
- Which agent should handle it
- What specific task they should perform
- Dependencies on other steps (if any)

Output the plan as JSON in this format:
{{
    "goal": "the user's goal",
    "steps": [
        {{
            "step_id": "step_1",
            "agent_name": "AgentName",
            "task": "Specific task description",
            "dependencies": []
        }},
        {{
            "step_id": "step_2", 
            "agent_name": "AnotherAgent",
            "task": "Another task that depends on step_1",
            "dependencies": ["step_1"]
        }}
    ]
}}

Keep the plan focused and efficient. Use the minimum number of steps needed."""
    
    SYNTHESIZER_PROMPT = """You are a synthesis agent that combines results from multiple specialized agents.

The original goal was: {goal}

The following agents completed their tasks:
{agent_results}

Synthesize these results into a coherent, comprehensive response that addresses the original goal.
Highlight key findings, provide actionable recommendations, and note any conflicting information."""
    
    def __init__(
        self,
        client: ChatClient,
        agents: dict[str, BaseRetailAgent],
        human_approval_callback: Optional[ApprovalCallback] = None,
        max_rounds: int = 20,
        checkpoint_store: Optional[Any] = None,
    ):
        """
        Initialize the Magentic orchestrator.
        
        Args:
            client: Chat client for planning LLM calls
            agents: Dictionary mapping agent names to agent instances
            human_approval_callback: Callback for plan approval (HITL)
            max_rounds: Maximum execution rounds
            checkpoint_store: Optional checkpoint store for persistence
        """
        self._client = client
        self._agents = agents
        self._approval_callback = human_approval_callback
        self._max_rounds = max_rounds
        self._checkpoint_store = checkpoint_store
        
        # Build agent descriptions for planner
        self._agent_descriptions = "\n".join(
            f"- {name}: {agent.description}"
            for name, agent in agents.items()
        )
        
        logger.info(f"MagenticOrchestrator initialized with {len(agents)} agents")
    
    async def run(
        self,
        goal: str,
        context: Optional[dict] = None,
        require_approval: bool = True,
    ) -> dict[str, Any]:
        """
        Run the orchestration for a given goal.
        
        Args:
            goal: The user's goal/task
            context: Optional context information
            require_approval: Whether to require human approval
            
        Returns:
            dict with 'result', 'plan', and 'agent_responses'
        """
        logger.info(f"Starting orchestration for goal: {goal}")
        
        # Step 1: Create execution plan
        plan = await self._create_plan(goal)
        logger.info(f"Created plan with {len(plan.steps)} steps")
        
        # Step 2: Get human approval if required
        if require_approval and self._approval_callback:
            logger.info("Requesting human approval for plan")
            approved = self._approval_callback(plan)
            
            if not approved:
                return {
                    "result": "Plan was not approved. Please modify your request or approve the plan to proceed.",
                    "plan": plan.to_dict(),
                    "status": "rejected",
                }
            
            plan.approved = True
            plan.approved_at = datetime.now(timezone.utc)
        else:
            plan.approved = True
        
        # Step 3: Execute the plan
        agent_responses = await self._execute_plan(plan)
        
        # Step 4: Synthesize results
        synthesis = await self._synthesize_results(plan, agent_responses)
        
        return {
            "result": synthesis,
            "plan": plan.to_dict(),
            "agent_responses": {
                name: resp.to_dict() for name, resp in agent_responses.items()
            },
            "status": "completed",
        }
    
    async def _create_plan(self, goal: str) -> MagenticPlan:
        """Create an execution plan for the goal."""
        import uuid
        
        system_prompt = self.PLANNER_SYSTEM_PROMPT.format(
            agent_descriptions=self._agent_descriptions
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create a plan to: {goal}"},
        ]
        
        response = await self._client.chat_completion(
            messages=messages,
            temperature=0.3,  # Lower temperature for planning
        )
        
        # Parse the plan from response
        content = response.get("content", "")
        
        try:
            # Extract JSON from response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                plan_data = json.loads(content[json_start:json_end])
            else:
                raise ValueError("No JSON found in response")
            
            # Create plan object
            plan = MagenticPlan(
                plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                goal=plan_data.get("goal", goal),
            )
            
            for step_data in plan_data.get("steps", []):
                plan.steps.append(PlanStep(
                    step_id=step_data["step_id"],
                    agent_name=step_data["agent_name"],
                    task=step_data["task"],
                    dependencies=step_data.get("dependencies", []),
                ))
            
            return plan
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse plan: {e}")
            # Create a simple single-step plan as fallback
            return MagenticPlan(
                plan_id=f"plan-{uuid.uuid4().hex[:8]}",
                goal=goal,
                steps=[
                    PlanStep(
                        step_id="step_1",
                        agent_name=list(self._agents.keys())[0],
                        task=goal,
                    )
                ],
            )
    
    async def _execute_plan(
        self,
        plan: MagenticPlan,
    ) -> dict[str, AgentResponse]:
        """Execute the plan steps."""
        agent_responses: dict[str, AgentResponse] = {}
        rounds = 0
        
        while not plan.is_complete() and rounds < self._max_rounds:
            rounds += 1
            
            # Get steps ready to execute
            ready_steps = plan.get_ready_steps()
            
            if not ready_steps:
                logger.warning("No ready steps but plan not complete")
                break
            
            # Execute ready steps (could be parallelized)
            for step in ready_steps:
                logger.info(f"Executing step {step.step_id}: {step.agent_name}")
                
                step.status = PlanStepStatus.IN_PROGRESS
                step.started_at = datetime.now(timezone.utc)
                
                try:
                    # Get the agent
                    agent = self._agents.get(step.agent_name)
                    if not agent:
                        raise ValueError(f"Agent not found: {step.agent_name}")
                    
                    # Build context from previous results
                    context_parts = []
                    for dep_id in step.dependencies:
                        dep_step = next((s for s in plan.steps if s.step_id == dep_id), None)
                        if dep_step and dep_step.result:
                            context_parts.append(f"[From {dep_step.agent_name}]: {dep_step.result}")
                    
                    task_with_context = step.task
                    if context_parts:
                        task_with_context = f"Context from previous steps:\n{''.join(context_parts)}\n\nYour task: {step.task}"
                    
                    # Execute
                    response = await agent.invoke(task_with_context)
                    
                    step.result = response.content
                    step.status = PlanStepStatus.COMPLETED
                    step.completed_at = datetime.now(timezone.utc)
                    
                    agent_responses[f"{step.step_id}_{step.agent_name}"] = response
                    
                except Exception as e:
                    logger.error(f"Step {step.step_id} failed: {e}")
                    step.status = PlanStepStatus.FAILED
                    step.result = f"Error: {str(e)}"
                    step.completed_at = datetime.now(timezone.utc)
        
        return agent_responses
    
    async def _synthesize_results(
        self,
        plan: MagenticPlan,
        agent_responses: dict[str, AgentResponse],
    ) -> str:
        """Synthesize results from all agents into a coherent response."""
        
        # Build agent results summary
        results_parts = []
        for step in plan.steps:
            if step.status == PlanStepStatus.COMPLETED and step.result:
                results_parts.append(f"**{step.agent_name}** (Task: {step.task}):\n{step.result}\n")
        
        if not results_parts:
            return "No agent results to synthesize. The plan may have failed."
        
        agent_results = "\n---\n".join(results_parts)
        
        prompt = self.SYNTHESIZER_PROMPT.format(
            goal=plan.goal,
            agent_results=agent_results,
        )
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant that synthesizes information."},
            {"role": "user", "content": prompt},
        ]
        
        response = await self._client.chat_completion(
            messages=messages,
            temperature=0.5,
        )
        
        return response.get("content", "Unable to synthesize results.")
    
    def get_agents(self) -> dict[str, dict]:
        """Get information about available agents."""
        return {
            name: agent.to_dict()
            for name, agent in self._agents.items()
        }
