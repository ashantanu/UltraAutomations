from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from app.middleware.auth import AuthMiddleware
from app.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.agent import router as agent_router
from app.api.youtube import router as youtube_router
from app.api.sanity import router as sanity_router

app = FastAPI(
    title="Your API",
    description="API description",
    version="1.0.0"
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