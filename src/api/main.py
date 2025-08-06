from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.deps import CurrentUser
from src.core.config import settings
from src.core.database import db_manager

app = FastAPI(
    title="Dwell API",
    description="Real estate listing recommendation API",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = db_manager.check_connection()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected",
    }


@app.get("/test-auth")
async def test_auth(current_user: CurrentUser):
    """Test endpoint requiring authentication"""
    return {
        "message": "Authentication successful",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
        },
    }


@app.get("/")
async def root():
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
