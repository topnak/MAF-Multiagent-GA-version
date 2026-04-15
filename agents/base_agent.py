# ─────────────────────────────────────────────────────────────────────────────
# Base Retail Agent
# ─────────────────────────────────────────────────────────────────────────────
# Abstract base class for all retail domain agents.
# Implements MAF 1.0 GA Agent pattern with tools and memory.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from .agent_factory import ChatClient

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """Represents a message in the agent conversation."""
    role: str  # user, assistant, system, tool
    content: str
    name: Optional[str] = None  # For tool messages
    tool_call_id: Optional[str] = None  # For tool results
    tool_calls: list[dict] = field(default_factory=list)  # For assistant tool calls


@dataclass
class AgentResponse:
    """Represents an agent's response."""
    content: str
    agent_name: str
    tool_calls_made: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "agent_name": self.agent_name,
            "tool_calls_made": self.tool_calls_made,
            "metadata": self.metadata,
        }


class BaseRetailAgent(ABC):
    """
    Abstract base class for retail domain agents.
    
    This class implements the MAF 1.0 GA Agent pattern:
    - Single Agent class with pluggable chat client
    - Tool registration and execution
    - Memory integration
    - Conversation state management
    
    Subclasses must implement:
    - name: Agent name
    - description: What the agent does
    - instructions: System prompt for the agent
    - _register_tools(): Register MCP tools
    
    Usage:
        class MerchPlannerAgent(BaseRetailAgent):
            name = "MerchPlanner"
            description = "Merchandising planner agent"
            instructions = "You are a merchandising planner..."
            
            def _register_tools(self):
                self.register_tool(snowflake_mcp)
    """
    
    # Subclasses must define these
    name: str = "BaseAgent"
    description: str = "Base retail agent"
    instructions: str = "You are a helpful retail assistant."
    
    def __init__(
        self,
        client: ChatClient,
        memory: Optional[Any] = None,
    ):
        """
        Initialize the agent.
        
        Args:
            client: Chat client for LLM access
            memory: Memory provider for conversation history
        """
        self._client = client
        self._memory = memory
        self._tools: dict[str, dict] = {}
        self._mcp_servers: list[Any] = []
        self._conversation: list[AgentMessage] = []
        
        # Register tools defined by subclass
        self._register_tools()
        
        logger.info(f"Agent {self.name} initialized with {len(self._tools)} tools")
    
    @abstractmethod
    def _register_tools(self) -> None:
        """
        Register tools for this agent.
        
        Subclasses must implement this to register their MCP tools.
        """
        pass
    
    def register_mcp_server(self, server: Any) -> None:
        """
        Register an MCP server and its tools.
        
        Args:
            server: MCP server instance
        """
        self._mcp_servers.append(server)
        
        # Import here to avoid circular dependency
        from mcp_servers.base_mcp_server import BaseMCPServer
        
        if isinstance(server, BaseMCPServer):
            # Register each tool from the server
            for tool_name, tool in server._tools.items():
                self.register_tool_definition(
                    name=f"{server.name}_{tool_name}",
                    description=tool.description,
                    parameters=tool.input_schema,
                    server=server,
                    tool_name=tool_name,
                )
    
    def register_tool_definition(
        self,
        name: str,
        description: str,
        parameters: dict,
        server: Optional[Any] = None,
        tool_name: Optional[str] = None,
    ) -> None:
        """
        Register a tool definition for function calling.
        
        Args:
            name: Tool name as exposed to the LLM
            description: Tool description
            parameters: JSON Schema for parameters
            server: MCP server that handles this tool
            tool_name: Original tool name on the server
        """
        self._tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
            "_server": server,
            "_tool_name": tool_name or name,
        }
    
    async def invoke(
        self,
        message: str,
        context: Optional[dict] = None,
        max_iterations: int = 10,
    ) -> AgentResponse:
        """
        Invoke the agent with a message.
        
        This is the main entry point for agent interaction. The agent will:
        1. Add the user message to conversation
        2. Get LLM response
        3. If tool calls are requested, execute them and loop
        4. Return final response
        
        Args:
            message: User message
            context: Optional context dict
            max_iterations: Maximum tool call iterations
            
        Returns:
            AgentResponse with the agent's response
        """
        # Add user message
        self._conversation.append(AgentMessage(role="user", content=message))
        
        tool_calls_made = []
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            # Build messages for LLM
            messages = self._build_messages()
            
            # Get tools in OpenAI format
            tools = list(self._tools.values()) if self._tools else None
            
            # Get LLM response
            response = await self._client.chat_completion(
                messages=messages,
                tools=tools,
                temperature=0.7,
            )
            
            # Check for tool calls
            if response.get("tool_calls"):
                # Add assistant message with tool calls
                self._conversation.append(AgentMessage(
                    role="assistant",
                    content=response.get("content", ""),
                    tool_calls=response["tool_calls"],
                ))
                
                # Execute each tool call
                for tool_call in response["tool_calls"]:
                    tool_result = await self._execute_tool(tool_call)
                    tool_calls_made.append({
                        "tool": tool_call["function"]["name"],
                        "arguments": tool_call["function"]["arguments"],
                        "result_preview": tool_result[:200] if len(tool_result) > 200 else tool_result,
                    })
                    
                    # Add tool result to conversation
                    self._conversation.append(AgentMessage(
                        role="tool",
                        content=tool_result,
                        name=tool_call["function"]["name"],
                        tool_call_id=tool_call["id"],
                    ))
            else:
                # No tool calls - we have the final response
                content = response.get("content", "")
                
                self._conversation.append(AgentMessage(
                    role="assistant",
                    content=content,
                ))
                
                return AgentResponse(
                    content=content,
                    agent_name=self.name,
                    tool_calls_made=tool_calls_made,
                    metadata={
                        "iterations": iterations,
                        "usage": response.get("usage", {}),
                    },
                )
        
        # Max iterations reached
        return AgentResponse(
            content="I apologize, but I reached the maximum number of iterations. Here's what I found so far based on my tool calls.",
            agent_name=self.name,
            tool_calls_made=tool_calls_made,
            metadata={"iterations": iterations, "max_iterations_reached": True},
        )
    
    async def _execute_tool(self, tool_call: dict) -> str:
        """
        Execute a tool call.
        
        Args:
            tool_call: Tool call dict with function name and arguments
            
        Returns:
            Tool result as string
        """
        tool_name = tool_call["function"]["name"]
        arguments_str = tool_call["function"]["arguments"]
        
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"Error: Invalid JSON arguments: {arguments_str}"
        
        # Find the tool
        tool_def = self._tools.get(tool_name)
        if not tool_def:
            return f"Error: Unknown tool: {tool_name}"
        
        # Get the server and execute
        server = tool_def.get("_server")
        if server:
            from mcp_servers.base_mcp_server import MCPToolCall
            
            result = await server.call_tool(MCPToolCall(
                name=tool_def["_tool_name"],
                arguments=arguments,
                call_id=tool_call.get("id"),
            ))
            
            # Format result
            if result.content:
                return "\n".join(
                    item.get("text", str(item))
                    for item in result.content
                )
            return "Tool executed successfully but returned no content."
        
        return f"Error: No server configured for tool: {tool_name}"
    
    def _build_messages(self) -> list[dict[str, Any]]:
        """Build messages list for LLM call."""
        messages = [
            {"role": "system", "content": self.instructions},
        ]
        
        for msg in self._conversation:
            if msg.role == "tool":
                messages.append({
                    "role": "tool",
                    "content": msg.content,
                    "tool_call_id": msg.tool_call_id,
                })
            elif msg.role == "assistant" and msg.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": msg.tool_calls,
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })
        
        return messages
    
    def reset_conversation(self) -> None:
        """Clear the conversation history."""
        self._conversation = []
    
    def get_conversation_history(self) -> list[dict]:
        """Get the conversation history as a list of dicts."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self._conversation
        ]
    
    def to_dict(self) -> dict[str, Any]:
        """Get agent metadata as dict."""
        return {
            "name": self.name,
            "description": self.description,
            "tools": list(self._tools.keys()),
            "provider": self._client.provider,
        }
