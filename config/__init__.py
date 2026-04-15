# ─────────────────────────────────────────────────────────────────────────────
# Config Module
# ─────────────────────────────────────────────────────────────────────────────
# Provides centralized configuration management using Pydantic settings.
# All configuration is loaded from environment variables.
# ─────────────────────────────────────────────────────────────────────────────

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
