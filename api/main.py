# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Main Application
# ─────────────────────────────────────────────────────────────────────────────
# Entry point for the Multi-Agent API service.
# ─────────────────────────────────────────────────────────────────────────────

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import agent_router, orchestration_router, health_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Multi-Agent API...")
    
    # In production, initialize:
    # - Agent factory
    # - Telemetry
    # - Database connections
    # - Redis connection
    
    yield
    
    # Shutdown
    logger.info("Shutting down Multi-Agent API...")
    
    # In production, cleanup:
    # - Close connections
    # - Flush telemetry


def create_app(
    title: str = "MAFGA Multi-Agent API",
    version: str = "1.0.0",
    enable_cors: bool = True,
    cors_origins: Optional[list[str]] = None,
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        title: API title
        version: API version
        enable_cors: Whether to enable CORS
        cors_origins: Allowed CORS origins
        
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title=title,
        description="""
# MAFGA Multi-Agent API

This API provides access to a multi-agent system built using the **MAF 1.0 GA** (Microsoft Agent Framework General Availability) architecture pattern.

## Key Features

- **Multi-Agent Orchestration**: Magentic, Routing, and Parallel orchestration patterns
- **Human-in-the-Loop**: Approval workflows for plan review
- **MCP Integration**: Tool calling via Model Context Protocol
- **A2A Communication**: Agent-to-agent messaging protocol
- **Observability**: OpenTelemetry tracing and metrics

## Agents

The system includes specialized retail domain agents:
- **MerchPlanner**: Merchandise planning and inventory analysis
- **SpacePlanner**: Store space planning and planograms
- **LoyaltyAgent**: Customer loyalty and personalization
- **ProductsFinder**: Product search and recommendations
- **CommercialSales**: B2B sales and opportunities
- **CampaignAnalyst**: Marketing campaign analysis

## Authentication

This API uses Azure EntraID for authentication. Include a Bearer token in requests:

```
Authorization: Bearer <your-token>
```
        """,
        version=version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins or ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Add exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                },
            },
        )
    
    # Include routers
    app.include_router(health_router)
    app.include_router(agent_router)
    app.include_router(orchestration_router)
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": title,
            "version": version,
            "docs": "/docs",
            "health": "/health",
        }
    
    return app


# Create default app instance
app = create_app()


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
