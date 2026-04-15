# ─────────────────────────────────────────────────────────────────────────────
# Middleware Module
# ─────────────────────────────────────────────────────────────────────────────
# Provides middleware components for the MAF 1.0 GA agent pipeline:
# - RBAC enforcement
# - Content safety filtering
# - Audit logging
#
# These middleware components follow the MAF 1.0 GA middleware pattern
# and can be stacked in order of execution.
# ─────────────────────────────────────────────────────────────────────────────

from .base_middleware import MiddlewareBase, MiddlewareContext, MiddlewarePipeline
from .rbac_middleware import RBACMiddleware, RBACConfig
from .content_safety_middleware import ContentSafetyMiddleware, ContentSafetyConfig
from .audit_log_middleware import AuditLogMiddleware, AuditLogConfig

__all__ = [
    # Base classes
    "MiddlewareBase",
    "MiddlewareContext",
    "MiddlewarePipeline",
    # RBAC
    "RBACMiddleware",
    "RBACConfig",
    # Content Safety
    "ContentSafetyMiddleware",
    "ContentSafetyConfig",
    # Audit Logging
    "AuditLogMiddleware",
    "AuditLogConfig",
]
