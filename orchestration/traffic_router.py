# ─────────────────────────────────────────────────────────────────────────────
# Traffic Router (Handoff Orchestration)
# ─────────────────────────────────────────────────────────────────────────────
# Implements the Handoff orchestration pattern from MAF 1.0 GA.
# Routes incoming requests to the most appropriate agent based on:
# - Intent classification
# - Agent capabilities
# - Load balancing
# ─────────────────────────────────────────────────────────────────────────────

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from agents.agent_factory import ChatClient
from agents.base_agent import BaseRetailAgent, AgentResponse

# Configure module logger
logger = logging.getLogger(__name__)


class RoutingStrategy(str, Enum):
    """Routing strategy for traffic router."""
    INTENT_BASED = "intent_based"       # Route based on classified intent
    ROUND_ROBIN = "round_robin"          # Simple rotation
    CAPABILITY_MATCH = "capability_match"  # Match task to agent capabilities


@dataclass
class RoutingDecision:
    """
    Result of a routing decision.
    
    Attributes:
        agent_name: Name of the selected agent
        confidence: Confidence score (0-1)
        reasoning: Explanation for the routing decision
    """
    agent_name: str
    confidence: float
    reasoning: str


class TrafficRouter:
    """
    Traffic Router implementing MAF 1.0 GA Handoff Orchestration.
    
    This orchestrator routes incoming requests to the most appropriate
    agent based on the task content and agent capabilities.
    
    Key Features:
    - LLM-based intent classification
    - Agent capability matching
    - Confidence-based routing
    - Fallback handling
    
    Usage:
        router = TrafficRouter(
            client=chat_client,
            agents={"MerchPlanner": merch_agent, ...},
        )
        result = await router.route("I need help with inventory planning")
    """
    
    ROUTER_SYSTEM_PROMPT = """You are a routing agent that directs user requests to the most appropriate specialized agent.

Available agents and their capabilities:
{agent_descriptions}

Given a user request, determine which agent should handle it.
Consider:
1. The nature of the task
2. Which agent's capabilities best match
3. Any specific domain knowledge required

Output your decision as JSON:
{{
    "agent_name": "SelectedAgentName",
    "confidence": 0.95,
    "reasoning": "Brief explanation for this routing decision"
}}

If no agent is suitable, use "agent_name": null."""
    
    def __init__(
        self,
        client: ChatClient,
        agents: dict[str, BaseRetailAgent],
        strategy: RoutingStrategy = RoutingStrategy.INTENT_BASED,
        default_agent: Optional[str] = None,
    ):
        """
        Initialize the traffic router.
        
        Args:
            client: Chat client for routing decisions
            agents: Dictionary mapping agent names to agent instances
            strategy: Routing strategy to use
            default_agent: Default agent if routing fails
        """
        self._client = client
        self._agents = agents
        self._strategy = strategy
        self._default_agent = default_agent or (list(agents.keys())[0] if agents else None)
        
        # Round-robin state
        self._rr_index = 0
        self._agent_list = list(agents.keys())
        
        # Build agent descriptions for router
        self._agent_descriptions = "\n".join(
            f"- {name}: {agent.description}"
            for name, agent in agents.items()
        )
        
        logger.info(f"TrafficRouter initialized with {len(agents)} agents, strategy={strategy.value}")
    
    async def route(
        self,
        task: str,
        context: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Route a task and execute with the selected agent.
        
        Args:
            task: The task/query to route
            context: Optional context information
            
        Returns:
            dict with 'result', 'routing', and 'agent_name'
        """
        # Step 1: Make routing decision
        decision = await self._make_routing_decision(task)
        
        logger.info(
            f"Routing decision: {decision.agent_name} "
            f"(confidence={decision.confidence:.2f})"
        )
        
        # Step 2: Execute with selected agent
        agent = self._agents.get(decision.agent_name)
        
        if not agent:
            logger.warning(f"Agent {decision.agent_name} not found, using default")
            agent = self._agents.get(self._default_agent)
            decision.agent_name = self._default_agent
        
        if not agent:
            return {
                "result": "No suitable agent available for this task.",
                "routing": {
                    "agent_name": None,
                    "confidence": 0.0,
                    "reasoning": "No agents available",
                },
                "status": "failed",
            }
        
        # Step 3: Invoke the agent
        response = await agent.invoke(task, context)
        
        return {
            "result": response.content,
            "routing": {
                "agent_name": decision.agent_name,
                "confidence": decision.confidence,
                "reasoning": decision.reasoning,
            },
            "agent_response": response.to_dict(),
            "status": "completed",
        }
    
    async def _make_routing_decision(self, task: str) -> RoutingDecision:
        """Make a routing decision based on the strategy."""
        
        if self._strategy == RoutingStrategy.ROUND_ROBIN:
            # Simple round-robin
            agent_name = self._agent_list[self._rr_index % len(self._agent_list)]
            self._rr_index += 1
            return RoutingDecision(
                agent_name=agent_name,
                confidence=1.0,
                reasoning="Round-robin selection",
            )
        
        elif self._strategy == RoutingStrategy.CAPABILITY_MATCH:
            # Simple keyword matching
            return self._capability_match(task)
        
        else:  # INTENT_BASED (default)
            return await self._intent_based_routing(task)
    
    def _capability_match(self, task: str) -> RoutingDecision:
        """Match task to agent based on keywords in capabilities."""
        task_lower = task.lower()
        
        best_match = None
        best_score = 0
        
        for name, agent in self._agents.items():
            # Simple keyword matching against description
            desc_words = set(agent.description.lower().split())
            task_words = set(task_lower.split())
            
            overlap = len(desc_words & task_words)
            if overlap > best_score:
                best_score = overlap
                best_match = name
        
        if best_match:
            return RoutingDecision(
                agent_name=best_match,
                confidence=min(0.5 + (best_score * 0.1), 1.0),
                reasoning=f"Matched {best_score} keywords in agent description",
            )
        
        return RoutingDecision(
            agent_name=self._default_agent,
            confidence=0.3,
            reasoning="No strong capability match, using default agent",
        )
    
    async def _intent_based_routing(self, task: str) -> RoutingDecision:
        """Use LLM to classify intent and route."""
        import json
        
        system_prompt = self.ROUTER_SYSTEM_PROMPT.format(
            agent_descriptions=self._agent_descriptions
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Route this request: {task}"},
        ]
        
        response = await self._client.chat_completion(
            messages=messages,
            temperature=0.1,  # Very low for consistent routing
        )
        
        content = response.get("content", "")
        
        try:
            # Extract JSON from response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                decision_data = json.loads(content[json_start:json_end])
            else:
                raise ValueError("No JSON found in response")
            
            agent_name = decision_data.get("agent_name")
            
            # Validate agent exists
            if agent_name and agent_name not in self._agents:
                logger.warning(f"Router selected unknown agent: {agent_name}")
                agent_name = self._default_agent
            
            return RoutingDecision(
                agent_name=agent_name or self._default_agent,
                confidence=float(decision_data.get("confidence", 0.5)),
                reasoning=decision_data.get("reasoning", "No reasoning provided"),
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse routing decision: {e}")
            return RoutingDecision(
                agent_name=self._default_agent,
                confidence=0.3,
                reasoning="Failed to parse routing, using default",
            )
    
    def get_agents(self) -> dict[str, dict]:
        """Get information about available agents."""
        return {
            name: agent.to_dict()
            for name, agent in self._agents.items()
        }
    
    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Change the routing strategy."""
        self._strategy = strategy
        logger.info(f"Routing strategy changed to: {strategy.value}")
