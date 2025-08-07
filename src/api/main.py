import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.deps import CurrentUser
from src.api.routes import chat_router
from src.core.config import settings
from src.core.database import db_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application lifespan events"""
    # Startup
    if settings.env in ["local", "development"]:
        logger.info("Initializing database tables for development...")
        try:
            db_manager.init_db()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    yield

    # Shutdown
    logger.info("Application shutting down...")


app = FastAPI(
    title="Dwell API",
    description="Real estate listing recommendation API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api/v1")


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    db_healthy = db_manager.check_connection()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
    }


@app.get("/test-auth")
async def test_auth(current_user: CurrentUser) -> Dict[str, Any]:
    """Test endpoint requiring authentication"""
    return {
        "message": "Authentication successful",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
        },
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint"""
    return {"message": "Dwell API - Real estate recommendations"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
