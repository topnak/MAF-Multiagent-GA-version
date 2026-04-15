# ─────────────────────────────────────────────────────────────────────────────
# Configuration Settings Module
# ─────────────────────────────────────────────────────────────────────────────
# Centralized configuration management using Pydantic Settings.
# All values are loaded from environment variables with sensible defaults.
# Secrets should NEVER be hardcoded - always use environment variables.
# ─────────────────────────────────────────────────────────────────────────────

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class uses Pydantic Settings to automatically load configuration
    from environment variables. Sensitive values use SecretStr to prevent
    accidental logging of secrets.
    
    Usage:
        settings = get_settings()
        print(settings.agent_provider)  # "foundry"
        print(settings.azure_openai_api_key.get_secret_value())  # reveals secret
    """
    
    # ─────────────────────────────────────────────────────────────────────────
    # Model configuration - loads from .env file if present
    # ─────────────────────────────────────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AZURE IDENTITY (EntraID)
    # ═══════════════════════════════════════════════════════════════════════════
    azure_tenant_id: str = Field(
        default="",
        description="Azure AD tenant ID for EntraID authentication"
    )
    azure_client_id: str = Field(
        default="",
        description="Azure AD application (client) ID"
    )
    azure_client_secret: SecretStr = Field(
        default=SecretStr(""),
        description="Azure AD client secret - KEEP SECURE"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LLM PROVIDER SELECTION
    # ═══════════════════════════════════════════════════════════════════════════
    agent_provider: Literal["foundry", "openai", "anthropic", "gemini", "ollama", "bedrock"] = Field(
        default="foundry",
        description="LLM provider: foundry (Azure OpenAI), openai, anthropic, gemini, ollama, bedrock"
    )
    
    # ─── Azure OpenAI (Foundry) Settings ───
    azure_openai_endpoint: str = Field(
        default="",
        description="Azure OpenAI endpoint URL"
    )
    azure_openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Azure OpenAI API key - KEEP SECURE"
    )
    azure_openai_deployment: str = Field(
        default="gpt-4o",
        description="Azure OpenAI deployment name"
    )
    azure_openai_api_version: str = Field(
        default="2024-10-21",
        description="Azure OpenAI API version"
    )
    
    # ─── OpenAI Direct Settings ───
    openai_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="OpenAI API key - KEEP SECURE"
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model name"
    )
    
    # ─── Anthropic Settings ───
    anthropic_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Anthropic API key - KEEP SECURE"
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Anthropic model name"
    )
    
    # ─── Google Gemini Settings ───
    google_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Google API key - KEEP SECURE"
    )
    gemini_model: str = Field(
        default="gemini-2.0-flash",
        description="Gemini model name"
    )
    
    # ─── Ollama (Local) Settings ───
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL for local LLM inference"
    )
    ollama_model: str = Field(
        default="llama3.1",
        description="Ollama model name"
    )
    
    # ─── AWS Bedrock Settings ───
    aws_region: str = Field(
        default="us-east-1",
        description="AWS region for Bedrock"
    )
    aws_access_key_id: SecretStr = Field(
        default=SecretStr(""),
        description="AWS access key ID - KEEP SECURE"
    )
    aws_secret_access_key: SecretStr = Field(
        default=SecretStr(""),
        description="AWS secret access key - KEEP SECURE"
    )
    bedrock_model: str = Field(
        default="anthropic.claude-3-sonnet-20240229-v1:0",
        description="Bedrock model ID"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY & STORAGE
    # ═══════════════════════════════════════════════════════════════════════════
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL for chat history and caching"
    )
    redis_password: SecretStr = Field(
        default=SecretStr(""),
        description="Redis password - KEEP SECURE"
    )
    
    cosmos_connection_string: SecretStr = Field(
        default=SecretStr(""),
        description="Azure Cosmos DB connection string - KEEP SECURE"
    )
    cosmos_database: str = Field(
        default="multiagent",
        description="Cosmos DB database name"
    )
    cosmos_container: str = Field(
        default="checkpoints",
        description="Cosmos DB container name for checkpoints"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OBSERVABILITY
    # ═══════════════════════════════════════════════════════════════════════════
    otel_exporter_otlp_endpoint: str = Field(
        default="http://localhost:4317",
        description="OpenTelemetry OTLP exporter endpoint"
    )
    otel_service_name: str = Field(
        default="maf-multiagent-poc",
        description="Service name for OpenTelemetry"
    )
    
    langfuse_public_key: str = Field(
        default="",
        description="Langfuse public key for LLM observability"
    )
    langfuse_secret_key: SecretStr = Field(
        default=SecretStr(""),
        description="Langfuse secret key - KEEP SECURE"
    )
    langfuse_host: str = Field(
        default="https://cloud.langfuse.com",
        description="Langfuse host URL"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # APPLICATION SETTINGS
    # ═══════════════════════════════════════════════════════════════════════════
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Application environment"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    api_host: str = Field(
        default="0.0.0.0",
        description="API server host"
    )
    api_port: int = Field(
        default=8000,
        description="API server port"
    )
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MCP SERVER URLS (Mock servers for POC)
    # ═══════════════════════════════════════════════════════════════════════════
    mcp_snowflake_url: str = Field(
        default="http://localhost:8081",
        description="Snowflake MCP server URL"
    )
    mcp_personalisation_url: str = Field(
        default="http://localhost:8082",
        description="Personalisation MCP server URL"
    )
    mcp_localisation_url: str = Field(
        default="http://localhost:8083",
        description="Localisation MCP server URL"
    )
    mcp_items_api_url: str = Field(
        default="http://localhost:8084",
        description="Items API MCP server URL"
    )
    mcp_salesforce_url: str = Field(
        default="http://localhost:8085",
        description="Salesforce MCP server URL"
    )
    mcp_weather_url: str = Field(
        default="http://localhost:8086",
        description="Weather MCP server URL"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # A2A AGENT ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════════
    a2a_snowflake_cortex_url: str = Field(
        default="http://localhost:9001",
        description="Snowflake Cortex A2A agent URL"
    )
    a2a_vertex_ai_url: str = Field(
        default="http://localhost:9002",
        description="GCP Vertex AI A2A agent URL"
    )
    a2a_salesforce_agentforce_url: str = Field(
        default="http://localhost:9003",
        description="Salesforce AgentForce A2A agent URL"
    )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string to list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def get_llm_config(self) -> dict:
        """
        Get LLM configuration based on selected provider.
        
        Returns:
            dict: Configuration for the selected LLM provider
        """
        if self.agent_provider == "foundry":
            return {
                "provider": "azure_openai",
                "endpoint": self.azure_openai_endpoint,
                "api_key": self.azure_openai_api_key.get_secret_value(),
                "deployment": self.azure_openai_deployment,
                "api_version": self.azure_openai_api_version,
            }
        elif self.agent_provider == "openai":
            return {
                "provider": "openai",
                "api_key": self.openai_api_key.get_secret_value(),
                "model": self.openai_model,
            }
        elif self.agent_provider == "anthropic":
            return {
                "provider": "anthropic",
                "api_key": self.anthropic_api_key.get_secret_value(),
                "model": self.anthropic_model,
            }
        elif self.agent_provider == "gemini":
            return {
                "provider": "gemini",
                "api_key": self.google_api_key.get_secret_value(),
                "model": self.gemini_model,
            }
        elif self.agent_provider == "ollama":
            return {
                "provider": "ollama",
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
            }
        elif self.agent_provider == "bedrock":
            return {
                "provider": "bedrock",
                "region": self.aws_region,
                "access_key_id": self.aws_access_key_id.get_secret_value(),
                "secret_access_key": self.aws_secret_access_key.get_secret_value(),
                "model": self.bedrock_model,
            }
        else:
            raise ValueError(f"Unknown agent provider: {self.agent_provider}")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached application settings.
    
    Uses lru_cache to ensure settings are only loaded once from environment
    variables, improving performance for repeated access.
    
    Returns:
        Settings: Application settings instance
    
    Example:
        settings = get_settings()
        print(settings.agent_provider)
    """
    return Settings()
