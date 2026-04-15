# ─────────────────────────────────────────────────────────────────────────────
# Base MCP Server
# ─────────────────────────────────────────────────────────────────────────────
# Defines the base class for MCP (Model Context Protocol) servers.
# MCP provides a standardized way for AI agents to interact with tools
# and external services.
#
# MCP Protocol:
# - tools/list: List available tools
# - tools/call: Execute a tool with arguments
# - resources/list: List available resources
# - resources/read: Read a resource
# ─────────────────────────────────────────────────────────────────────────────

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """
    Represents an MCP tool definition.
    
    This follows the MCP specification for tool definitions, which are
    used by agents to discover and invoke tools.
    
    Attributes:
        name: Unique tool identifier
        description: Human-readable description of what the tool does
        input_schema: JSON Schema for the tool's input parameters
    """
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP tool format."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


@dataclass
class MCPToolCall:
    """
    Represents a request to call an MCP tool.
    
    Attributes:
        name: Name of the tool to call
        arguments: Arguments to pass to the tool
        call_id: Optional unique identifier for the call
    """
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """
    Represents the result of an MCP tool call.
    
    Attributes:
        content: Result content (list of content items)
        is_error: Whether the result indicates an error
        call_id: ID of the call this result is for
    """
    content: list[dict[str, Any]] = field(default_factory=list)
    is_error: bool = False
    call_id: Optional[str] = None
    
    @classmethod
    def success(cls, text: str, call_id: Optional[str] = None) -> "MCPToolResult":
        """Create a successful result with text content."""
        return cls(
            content=[{"type": "text", "text": text}],
            is_error=False,
            call_id=call_id,
        )
    
    @classmethod
    def error(cls, message: str, call_id: Optional[str] = None) -> "MCPToolResult":
        """Create an error result."""
        return cls(
            content=[{"type": "text", "text": f"Error: {message}"}],
            is_error=True,
            call_id=call_id,
        )
    
    @classmethod
    def json_result(cls, data: Any, call_id: Optional[str] = None) -> "MCPToolResult":
        """Create a result with JSON data."""
        import json
        return cls(
            content=[{
                "type": "text",
                "text": json.dumps(data, indent=2, default=str),
            }],
            is_error=False,
            call_id=call_id,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to MCP result format."""
        return {
            "content": self.content,
            "isError": self.is_error,
        }


class BaseMCPServer(ABC):
    """
    Abstract base class for MCP servers.
    
    MCP (Model Context Protocol) servers expose tools and resources that
    can be discovered and used by AI agents. This base class provides
    the structure for implementing MCP-compliant servers.
    
    Protocol Methods:
        - list_tools(): Return available tools
        - call_tool(call): Execute a tool
        - list_resources(): Return available resources (optional)
        - read_resource(uri): Read a resource (optional)
    
    Usage:
        class MyMCPServer(BaseMCPServer):
            def __init__(self):
                super().__init__(
                    name="my-server",
                    version="1.0.0",
                    description="My custom MCP server"
                )
            
            def _register_tools(self):
                self.register_tool(MCPTool(...))
            
            async def _execute_tool(self, call):
                # Implementation
                pass
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        description: str = "",
    ):
        """
        Initialize the MCP server.
        
        Args:
            name: Server name
            version: Server version
            description: Human-readable description
        """
        self.name = name
        self.version = version
        self.description = description
        
        # Registry of available tools
        self._tools: dict[str, MCPTool] = {}
        
        # Register tools defined by subclass
        self._register_tools()
        
        logger.info(f"MCP server '{name}' v{version} initialized with {len(self._tools)} tools")
    
    @abstractmethod
    def _register_tools(self) -> None:
        """
        Register available tools.
        
        Subclasses must implement this method to register their tools
        using self.register_tool().
        """
        pass
    
    @abstractmethod
    async def _execute_tool(self, call: MCPToolCall) -> MCPToolResult:
        """
        Execute a tool call.
        
        Subclasses must implement this method to handle tool execution.
        
        Args:
            call: Tool call request
            
        Returns:
            MCPToolResult with the execution result
        """
        pass
    
    def register_tool(self, tool: MCPTool) -> None:
        """
        Register a tool with the server.
        
        Args:
            tool: Tool definition to register
        """
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    async def list_tools(self) -> list[dict[str, Any]]:
        """
        List all available tools (MCP tools/list).
        
        Returns:
            List of tool definitions in MCP format
        """
        return [tool.to_dict() for tool in self._tools.values()]
    
    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        """
        Execute a tool call (MCP tools/call).
        
        Args:
            call: Tool call request
            
        Returns:
            MCPToolResult with the execution result
        """
        # Check if tool exists
        if call.name not in self._tools:
            logger.warning(f"Tool not found: {call.name}")
            return MCPToolResult.error(f"Tool not found: {call.name}", call.call_id)
        
        try:
            logger.debug(f"Executing tool: {call.name} with args: {call.arguments}")
            result = await self._execute_tool(call)
            result.call_id = call.call_id
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {call.name} - {e}")
            return MCPToolResult.error(str(e), call.call_id)
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        Get a tool definition by name.
        
        Args:
            name: Tool name
            
        Returns:
            MCPTool if found, None otherwise
        """
        return self._tools.get(name)
    
    def get_server_info(self) -> dict[str, Any]:
        """
        Get server information (MCP server info).
        
        Returns:
            Server info in MCP format
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "protocolVersion": "2024-11-05",  # MCP protocol version
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"subscribe": False},
            },
        }


def create_json_schema(
    properties: dict[str, dict],
    required: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Helper function to create JSON Schema for tool inputs.
    
    Args:
        properties: Property definitions
        required: List of required property names
        
    Returns:
        JSON Schema dictionary
        
    Example:
        schema = create_json_schema(
            properties={
                "query": {"type": "string", "description": "SQL query to execute"},
                "limit": {"type": "integer", "description": "Max rows", "default": 100},
            },
            required=["query"]
        )
    """
    schema = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema
