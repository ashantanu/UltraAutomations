from dotenv import load_dotenv
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
import logging

from app.middleware.auth import AuthMiddleware
from app.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.agent import router as agent_router
from app.api.youtube import router as youtube_router
from app.api.sanity import router as sanity_router
from app.core.startup import download_required_assets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI startup and shutdown events.
    """
    # Startup
    logger.info("Starting up application...")
    
    # Download required assets
    if not await download_required_assets():
        raise RuntimeError("Failed to download required assets")
    
    logger.info("Application startup complete")
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="Your API",
    description="API description",
    version="1.0.0",
    lifespan=lifespan
)

# Add the authentication middleware
app.add_middleware(AuthMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(youtube_router)
app.include_router(sanity_router, tags=["image", "sanity", "test"])

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/protected-route")
async def protected_route(request: Request):
    return {
        "message": "This is a protected route",
        "user": request.state.user.user.email if request.state.user.user else None
    } 