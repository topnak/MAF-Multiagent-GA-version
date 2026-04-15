# ─────────────────────────────────────────────────────────────────────────────
# Agent Factory - Cloud-Agnostic Chat Client Creation
# ─────────────────────────────────────────────────────────────────────────────
# Provides factory functions for creating chat clients that work with any
# LLM provider (Azure OpenAI, OpenAI, Anthropic, Gemini, Ollama, Bedrock).
#
# This is the core of cloud-agnostic design - swap providers with one env var.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Any, Optional

from openai import AsyncAzureOpenAI, AsyncOpenAI

from config import get_settings

# Configure module logger
logger = logging.getLogger(__name__)


class ChatClient:
    """
    Unified chat client interface for MAF 1.0 GA pattern.
    
    This class wraps different LLM providers behind a consistent interface,
    enabling cloud-agnostic agent implementation.
    
    Usage:
        client = create_chat_client()  # Uses AGENT_PROVIDER env var
        response = await client.chat_completion(messages)
    """
    
    def __init__(
        self,
        provider: str,
        client: Any,
        model: str,
        **kwargs,
    ):
        """
        Initialize chat client.
        
        Args:
            provider: Provider name (azure_openai, openai, anthropic, etc.)
            client: The underlying SDK client
            model: Model/deployment name
            **kwargs: Additional provider-specific settings
        """
        self.provider = provider
        self._client = client
        self.model = model
        self._kwargs = kwargs
    
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        tools: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Get a chat completion from the LLM.
        
        Args:
            messages: List of messages with 'role' and 'content'
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            tools: Tool definitions for function calling
            tool_choice: Tool choice mode
            **kwargs: Additional parameters
            
        Returns:
            dict with 'content', 'tool_calls', 'usage', etc.
        """
        if self.provider in ("azure_openai", "openai"):
            return await self._openai_completion(
                messages, temperature, max_tokens, tools, tool_choice, **kwargs
            )
        elif self.provider == "anthropic":
            return await self._anthropic_completion(
                messages, temperature, max_tokens, tools, **kwargs
            )
        elif self.provider == "gemini":
            return await self._gemini_completion(
                messages, temperature, max_tokens, **kwargs
            )
        elif self.provider == "ollama":
            return await self._ollama_completion(
                messages, temperature, max_tokens, **kwargs
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    async def _openai_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[list],
        tool_choice: Optional[str],
        **kwargs,
    ) -> dict[str, Any]:
        """OpenAI/Azure OpenAI completion."""
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            params["max_tokens"] = max_tokens
        if tools:
            params["tools"] = tools
        if tool_choice:
            params["tool_choice"] = tool_choice
        
        response = await self._client.chat.completions.create(**params)
        
        message = response.choices[0].message
        
        return {
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in (message.tool_calls or [])
            ],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "finish_reason": response.choices[0].finish_reason,
        }
    
    async def _anthropic_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int],
        tools: Optional[list],
        **kwargs,
    ) -> dict[str, Any]:
        """Anthropic Claude completion."""
        import anthropic
        
        # Convert messages format
        system_message = None
        claude_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        params = {
            "model": self.model,
            "messages": claude_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        
        if system_message:
            params["system"] = system_message
        
        if tools:
            # Convert OpenAI tool format to Anthropic format
            params["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {}),
                }
                for t in tools
            ]
        
        response = await self._client.messages.create(**params)
        
        content = ""
        tool_calls = []
        
        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": str(block.input),
                    },
                })
        
        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            "finish_reason": response.stop_reason,
        }
    
    async def _gemini_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> dict[str, Any]:
        """Google Gemini completion."""
        import google.generativeai as genai
        
        # Convert messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg["role"] == "system":
                # Prepend system message to first user message
                continue
            gemini_messages.append({
                "role": role,
                "parts": [msg["content"]],
            })
        
        # Get system instruction
        system_instruction = next(
            (m["content"] for m in messages if m["role"] == "system"),
            None
        )
        
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_instruction,
        )
        
        config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )
        
        response = await model.generate_content_async(
            gemini_messages,
            generation_config=config,
        )
        
        return {
            "content": response.text,
            "tool_calls": [],
            "usage": {
                "prompt_tokens": 0,  # Gemini doesn't always return this
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "finish_reason": "stop",
        }
    
    async def _ollama_completion(
        self,
        messages: list[dict],
        temperature: float,
        max_tokens: Optional[int],
        **kwargs,
    ) -> dict[str, Any]:
        """Ollama local completion."""
        import httpx
        
        base_url = self._kwargs.get("base_url", "http://localhost:11434")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens or 2048,
                    },
                },
                timeout=120.0,
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "content": data.get("message", {}).get("content", ""),
            "tool_calls": [],
            "usage": {
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            },
            "finish_reason": "stop",
        }


def create_chat_client(provider: Optional[str] = None) -> ChatClient:
    """
    Create a chat client based on the configured provider.
    
    This is the main entry point for cloud-agnostic LLM access.
    The provider is determined by the AGENT_PROVIDER environment variable,
    or can be overridden with the provider argument.
    
    Args:
        provider: Override provider (optional)
        
    Returns:
        ChatClient configured for the selected provider
        
    Example:
        # Uses AGENT_PROVIDER env var
        client = create_chat_client()
        
        # Override to specific provider
        client = create_chat_client(provider="ollama")
    """
    settings = get_settings()
    provider = provider or settings.agent_provider
    
    logger.info(f"Creating chat client for provider: {provider}")
    
    if provider == "foundry":
        # Azure OpenAI via Foundry
        client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key.get_secret_value(),
            api_version=settings.azure_openai_api_version,
        )
        return ChatClient(
            provider="azure_openai",
            client=client,
            model=settings.azure_openai_deployment,
        )
    
    elif provider == "openai":
        # Direct OpenAI
        client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
        )
        return ChatClient(
            provider="openai",
            client=client,
            model=settings.openai_model,
        )
    
    elif provider == "anthropic":
        # Anthropic Claude
        import anthropic
        client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key.get_secret_value(),
        )
        return ChatClient(
            provider="anthropic",
            client=client,
            model=settings.anthropic_model,
        )
    
    elif provider == "gemini":
        # Google Gemini
        import google.generativeai as genai
        genai.configure(api_key=settings.google_api_key.get_secret_value())
        return ChatClient(
            provider="gemini",
            client=None,  # Gemini uses module-level config
            model=settings.gemini_model,
        )
    
    elif provider == "ollama":
        # Local Ollama
        return ChatClient(
            provider="ollama",
            client=None,
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )
    
    elif provider == "bedrock":
        # AWS Bedrock - requires boto3
        raise NotImplementedError("Bedrock support coming soon")
    
    else:
        raise ValueError(f"Unknown provider: {provider}")


class AgentFactory:
    """
    Factory for creating domain agents with consistent configuration.
    
    This factory ensures all agents are created with:
    - Consistent chat client (same provider)
    - Proper middleware attachment
    - MCP tool registration
    - Memory provider attachment
    
    Usage:
        factory = AgentFactory()
        agents = factory.create_all_agents()
        merch = factory.create_agent("MerchPlanner")
    """
    
    def __init__(
        self,
        chat_client: Optional[ChatClient] = None,
        memory_provider: Optional[Any] = None,
    ):
        """
        Initialize agent factory.
        
        Args:
            chat_client: Chat client to use (creates one if not provided)
            memory_provider: Memory provider for agents
        """
        self._client = chat_client or create_chat_client()
        self._memory = memory_provider
    
    @property
    def client(self) -> ChatClient:
        """Get the chat client."""
        return self._client
    
    def create_all_agents(self) -> dict[str, "BaseRetailAgent"]:
        """
        Create all domain agents.
        
        Returns:
            dict mapping agent names to agent instances
        """
        from .merch_planner import MerchPlannerAgent
        from .space_planner import SpacePlannerAgent
        from .loyalty_agent import LoyaltyAgent
        from .products_finder import ProductsFinderAgent
        from .commercial_sales import CommercialSalesAgent
        from .campaign_analyst import CampaignAnalystAgent
        
        agents = {
            "MerchPlanner": MerchPlannerAgent(self._client, self._memory),
            "SpacePlanner": SpacePlannerAgent(self._client, self._memory),
            "LoyaltyAgent": LoyaltyAgent(self._client, self._memory),
            "ProductsFinder": ProductsFinderAgent(self._client, self._memory),
            "CommercialSales": CommercialSalesAgent(self._client, self._memory),
            "CampaignAnalyst": CampaignAnalystAgent(self._client, self._memory),
        }
        
        logger.info(f"Created {len(agents)} agents with {self._client.provider} provider")
        return agents
    
    def create_agent(self, name: str) -> "BaseRetailAgent":
        """
        Create a specific agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent instance
        """
        agents = self.create_all_agents()
        if name not in agents:
            raise ValueError(f"Unknown agent: {name}. Available: {list(agents.keys())}")
        return agents[name]
