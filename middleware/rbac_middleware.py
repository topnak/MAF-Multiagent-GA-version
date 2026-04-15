# ─────────────────────────────────────────────────────────────────────────────
# RBAC (Role-Based Access Control) Middleware
# ─────────────────────────────────────────────────────────────────────────────
# Enforces role-based access control for agent access.
# Users must have the required roles to interact with specific agents.
# Integrates with EntraID for role information.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from dataclasses import dataclass, field
from typing import Optional

from .base_middleware import (
    MiddlewareBase,
    MiddlewareContext,
    MiddlewareResponse,
    NextHandler,
)

# Configure module logger
logger = logging.getLogger(__name__)


class AccessDeniedError(Exception):
    """
    Exception raised when a user is denied access to an agent.
    
    This exception includes details about what access was denied
    for logging and debugging purposes.
    """
    def __init__(self, user_id: str, agent_name: str, required_roles: list[str]):
        self.user_id = user_id
        self.agent_name = agent_name
        self.required_roles = required_roles
        super().__init__(
            f"User {user_id} denied access to agent {agent_name}. "
            f"Required roles: {required_roles}"
        )


@dataclass
class RBACConfig:
    """
    Configuration for RBAC middleware.
    
    Attributes:
        agent_roles: Mapping of agent names to required roles
        default_roles: Roles that can access agents without explicit config
        require_authentication: Whether to require authentication for all requests
        allow_unauthenticated_agents: Agents that can be accessed without auth
    """
    # Map agent names to required roles
    # Example: {"MerchPlanner": ["merchandising", "admin"]}
    agent_roles: dict[str, list[str]] = field(default_factory=dict)
    
    # Roles that can access any agent (e.g., admin roles)
    default_roles: list[str] = field(default_factory=lambda: ["admin"])
    
    # Whether to require authentication for all requests
    require_authentication: bool = True
    
    # Agents that can be accessed without authentication (public agents)
    allow_unauthenticated_agents: list[str] = field(default_factory=list)
    
    @classmethod
    def default(cls) -> "RBACConfig":
        """
        Create default RBAC configuration for retail multi-agent system.
        
        Returns:
            RBACConfig: Default configuration with common retail agent roles
        """
        return cls(
            agent_roles={
                # Merchandising agents require specific roles
                "MerchPlanner": ["merchandising", "analyst", "admin"],
                "SpacePlanner": ["space_planning", "merchandising", "admin"],
                
                # Loyalty agents
                "LoyaltyAgent": ["loyalty", "customer_service", "admin"],
                
                # Product/catalog agents
                "ProductsFinder": ["products", "merchandising", "analyst", "admin"],
                
                # Sales agents require sales role
                "CommercialSales": ["sales", "admin"],
                
                # Campaign/marketing agents
                "CampaignAnalyst": ["marketing", "analyst", "admin"],
            },
            default_roles=["admin", "superuser"],
            require_authentication=True,
            allow_unauthenticated_agents=[],
        )


class RBACMiddleware(MiddlewareBase):
    """
    Role-Based Access Control middleware for MAF agents.
    
    This middleware enforces that users have the required roles to access
    specific agents. It integrates with EntraID for role information.
    
    Features:
    - Agent-level access control
    - Support for default admin roles
    - Configurable authentication requirements
    - Detailed access denial logging
    
    Usage:
        config = RBACConfig.default()
        rbac = RBACMiddleware(config)
        
        # In pipeline
        pipeline = MiddlewarePipeline([rbac])
        response = await pipeline.execute(context, agent_handler)
    """
    
    def __init__(self, config: Optional[RBACConfig] = None):
        """
        Initialize RBAC middleware.
        
        Args:
            config: RBAC configuration. If None, uses default config.
        """
        self.config = config or RBACConfig.default()
    
    async def on_request(
        self,
        context: MiddlewareContext,
        next_handler: NextHandler,
    ) -> MiddlewareResponse:
        """
        Check user authorization before allowing agent access.
        
        Args:
            context: Request context with user and agent info
            next_handler: Next middleware/agent in chain
            
        Returns:
            MiddlewareResponse: Response from agent or access denied message
        """
        # Check if agent requires authentication
        if self._is_public_agent(context.agent_name):
            logger.debug(f"Agent {context.agent_name} is public, skipping auth check")
            return await next_handler(context)
        
        # Check if user is authenticated
        if context.user is None:
            if self.config.require_authentication:
                logger.warning(
                    f"Unauthenticated access attempt to agent {context.agent_name}"
                )
                return MiddlewareResponse(
                    content="Authentication required. Please sign in to continue.",
                    blocked=True,
                    block_reason="authentication_required",
                )
            else:
                # Allow unauthenticated access if not required
                logger.debug(f"Allowing unauthenticated access to {context.agent_name}")
                return await next_handler(context)
        
        # Check if user has required roles
        if self._user_has_access(context.user, context.agent_name):
            logger.debug(
                f"User {context.user.user_id} authorized for agent {context.agent_name}"
            )
            # Add RBAC metadata to context
            context.set_metadata("rbac_validated", True)
            context.set_metadata("user_roles", context.user.roles)
            
            return await next_handler(context)
        else:
            # Access denied
            required_roles = self._get_required_roles(context.agent_name)
            logger.warning(
                f"Access denied: User {context.user.user_id} "
                f"lacks required roles {required_roles} for agent {context.agent_name}. "
                f"User roles: {context.user.roles}"
            )
            return MiddlewareResponse(
                content=(
                    f"Access denied. You don't have permission to use the "
                    f"{context.agent_name} agent. Required roles: {', '.join(required_roles)}"
                ),
                blocked=True,
                block_reason="access_denied",
                metadata={
                    "required_roles": required_roles,
                    "user_roles": context.user.roles,
                },
            )
    
    def _is_public_agent(self, agent_name: str) -> bool:
        """
        Check if an agent is publicly accessible.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            bool: True if agent is public
        """
        return agent_name in self.config.allow_unauthenticated_agents
    
    def _get_required_roles(self, agent_name: str) -> list[str]:
        """
        Get the roles required to access an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            list[str]: Required roles for the agent
        """
        return self.config.agent_roles.get(agent_name, [])
    
    def _user_has_access(self, user: "UserContext", agent_name: str) -> bool:
        """
        Check if a user has access to an agent.
        
        Access is granted if:
        1. User has any of the default (admin) roles, OR
        2. User has any of the agent's required roles, OR
        3. Agent has no specific role requirements
        
        Args:
            user: User context with roles
            agent_name: Name of the agent
            
        Returns:
            bool: True if user has access
        """
        from auth.entra_auth import UserContext
        
        # Check for default/admin roles
        if user.has_any_role(self.config.default_roles):
            return True
        
        # Get required roles for the agent
        required_roles = self._get_required_roles(agent_name)
        
        # If no specific roles required, allow access
        if not required_roles:
            return True
        
        # Check if user has any required role
        return user.has_any_role(required_roles)
    
    def add_agent_roles(self, agent_name: str, roles: list[str]) -> None:
        """
        Add or update role requirements for an agent.
        
        Args:
            agent_name: Name of the agent
            roles: List of roles that can access the agent
        """
        self.config.agent_roles[agent_name] = roles
    
    def remove_agent(self, agent_name: str) -> None:
        """
        Remove role requirements for an agent.
        
        Args:
            agent_name: Name of the agent
        """
        self.config.agent_roles.pop(agent_name, None)
