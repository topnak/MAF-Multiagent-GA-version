# ─────────────────────────────────────────────────────────────────────────────
# Parallel Executor (Concurrent Orchestration)
# ─────────────────────────────────────────────────────────────────────────────
# Implements the Concurrent orchestration pattern from MAF 1.0 GA.
# Executes multiple agents in parallel for independent tasks.
# Features:
# - Concurrent execution with gather semantics
# - Result aggregation
# - Error handling and partial results
# ─────────────────────────────────────────────────────────────────────────────

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from agents.base_agent import BaseRetailAgent, AgentResponse

# Configure module logger
logger = logging.getLogger(__name__)


class AggregationStrategy(str, Enum):
    """Strategy for aggregating parallel results."""
    ALL = "all"          # Return all results (even if some fail)
    FIRST = "first"      # Return first completed result
    MAJORITY = "majority"  # Return when majority complete


@dataclass
class ParallelTask:
    """
    Represents a task to be executed in parallel.
    
    Attributes:
        task_id: Unique identifier for the task
        agent_name: Name of the agent to execute
        query: Query/task for the agent
        context: Optional context for the agent
    """
    task_id: str
    agent_name: str
    query: str
    context: Optional[dict] = None


@dataclass
class ParallelResult:
    """
    Result from a parallel execution.
    
    Attributes:
        task_id: ID of the original task
        agent_name: Name of the agent that executed
        response: Agent's response (if successful)
        error: Error message (if failed)
        duration_ms: Execution duration in milliseconds
        status: 'completed' or 'failed'
    """
    task_id: str
    agent_name: str
    response: Optional[AgentResponse] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    status: str = "completed"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_name": self.agent_name,
            "response": self.response.to_dict() if self.response else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }


class ParallelExecutor:
    """
    Parallel Executor implementing MAF 1.0 GA Concurrent Orchestration.
    
    This orchestrator executes multiple agents in parallel, which is
    useful when:
    - Tasks are independent of each other
    - You want to gather multiple perspectives
    - Time is critical and parallel execution speeds up results
    
    Key Features:
    - True concurrent execution using asyncio
    - Configurable timeout per task
    - Partial result handling
    - Multiple aggregation strategies
    
    Usage:
        executor = ParallelExecutor(
            agents={"MerchPlanner": merch_agent, "SpacePlanner": space_agent},
        )
        
        tasks = [
            ParallelTask("t1", "MerchPlanner", "Analyze paint sales"),
            ParallelTask("t2", "SpacePlanner", "Suggest paint layout"),
        ]
        
        results = await executor.run(tasks)
    """
    
    def __init__(
        self,
        agents: dict[str, BaseRetailAgent],
        timeout_seconds: float = 30.0,
        aggregation: AggregationStrategy = AggregationStrategy.ALL,
    ):
        """
        Initialize the parallel executor.
        
        Args:
            agents: Dictionary mapping agent names to agent instances
            timeout_seconds: Timeout for each individual task
            aggregation: Strategy for aggregating results
        """
        self._agents = agents
        self._timeout = timeout_seconds
        self._aggregation = aggregation
        
        logger.info(
            f"ParallelExecutor initialized with {len(agents)} agents, "
            f"timeout={timeout_seconds}s, aggregation={aggregation.value}"
        )
    
    async def run(
        self,
        tasks: list[ParallelTask],
    ) -> dict[str, Any]:
        """
        Execute multiple tasks in parallel.
        
        Args:
            tasks: List of tasks to execute in parallel
            
        Returns:
            dict with 'results', 'summary', and execution stats
        """
        start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting parallel execution of {len(tasks)} tasks")
        
        # Create coroutines for each task
        coros = [
            self._execute_task(task)
            for task in tasks
        ]
        
        # Execute in parallel
        results = await asyncio.gather(*coros, return_exceptions=True)
        
        # Process results
        parallel_results: list[ParallelResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                parallel_results.append(ParallelResult(
                    task_id=tasks[i].task_id,
                    agent_name=tasks[i].agent_name,
                    error=str(result),
                    status="failed",
                ))
            else:
                parallel_results.append(result)
        
        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds() * 1000
        
        # Apply aggregation strategy
        final_results = self._apply_aggregation(parallel_results)
        
        # Calculate stats
        completed = sum(1 for r in parallel_results if r.status == "completed")
        failed = len(parallel_results) - completed
        
        return {
            "results": [r.to_dict() for r in final_results],
            "summary": {
                "total_tasks": len(tasks),
                "completed": completed,
                "failed": failed,
                "total_duration_ms": total_duration,
            },
            "execution_start": start_time.isoformat(),
            "execution_end": end_time.isoformat(),
            "status": "completed" if failed == 0 else "partial",
        }
    
    async def _execute_task(self, task: ParallelTask) -> ParallelResult:
        """Execute a single task with timeout."""
        start = datetime.now(timezone.utc)
        
        try:
            agent = self._agents.get(task.agent_name)
            
            if not agent:
                raise ValueError(f"Agent not found: {task.agent_name}")
            
            # Execute with timeout
            response = await asyncio.wait_for(
                agent.invoke(task.query, task.context),
                timeout=self._timeout,
            )
            
            end = datetime.now(timezone.utc)
            duration = (end - start).total_seconds() * 1000
            
            return ParallelResult(
                task_id=task.task_id,
                agent_name=task.agent_name,
                response=response,
                duration_ms=duration,
                status="completed",
            )
            
        except asyncio.TimeoutError:
            end = datetime.now(timezone.utc)
            duration = (end - start).total_seconds() * 1000
            
            logger.warning(f"Task {task.task_id} timed out after {self._timeout}s")
            
            return ParallelResult(
                task_id=task.task_id,
                agent_name=task.agent_name,
                error=f"Timeout after {self._timeout} seconds",
                duration_ms=duration,
                status="failed",
            )
            
        except Exception as e:
            end = datetime.now(timezone.utc)
            duration = (end - start).total_seconds() * 1000
            
            logger.error(f"Task {task.task_id} failed: {e}")
            
            return ParallelResult(
                task_id=task.task_id,
                agent_name=task.agent_name,
                error=str(e),
                duration_ms=duration,
                status="failed",
            )
    
    def _apply_aggregation(
        self,
        results: list[ParallelResult],
    ) -> list[ParallelResult]:
        """Apply the aggregation strategy to results."""
        
        if self._aggregation == AggregationStrategy.ALL:
            return results
        
        elif self._aggregation == AggregationStrategy.FIRST:
            # Return first completed result
            for r in results:
                if r.status == "completed":
                    return [r]
            return results[:1] if results else []
        
        elif self._aggregation == AggregationStrategy.MAJORITY:
            # Return when majority are completed
            completed = [r for r in results if r.status == "completed"]
            if len(completed) >= len(results) / 2:
                return completed
            return results
        
        return results
    
    async def broadcast(
        self,
        query: str,
        agent_names: Optional[list[str]] = None,
        context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Broadcast a query to multiple (or all) agents.
        
        This is a convenience method for running the same query
        across multiple agents.
        
        Args:
            query: Query to broadcast
            agent_names: List of agents to query (default: all)
            context: Optional context
            
        Returns:
            Parallel execution results
        """
        targets = agent_names or list(self._agents.keys())
        
        tasks = [
            ParallelTask(
                task_id=f"broadcast_{i}",
                agent_name=name,
                query=query,
                context=context,
            )
            for i, name in enumerate(targets)
        ]
        
        return await self.run(tasks)
    
    def get_agents(self) -> dict[str, dict]:
        """Get information about available agents."""
        return {
            name: agent.to_dict()
            for name, agent in self._agents.items()
        }
