from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from supabase import create_client, Client
import os
import json
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

supabase: Optional[Client] = None


def _get_supabase() -> Client:
    """
    Lazily initialize Supabase so importing this module does not require env vars.
    This makes local scripts/tests usable without SUPABASE_* configured.
    """
    global supabase
    if supabase is not None:
        return supabase

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")

    supabase = create_client(url, key)
    return supabase

class AuthMiddleware:
    def __init__(self, app):
        self.app = app
        self.security = HTTPBearer()
        # List of paths that don't require authentication
        self.excluded_paths = {
            "/docs",
            "/openapi.json",
            "/redoc",
            "/health",
            "/auth/login",  # Add your auth endpoints here
            "/auth/register"
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope)
        
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await self.app(scope, receive, send)

        try:
            # Get the Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing Authorization header",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Extract the token
            scheme, _, token = auth_header.partition(" ")
            if scheme.lower() != "bearer":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication scheme",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Verify the token with Supabase
            client = _get_supabase()
            try:
                user = client.auth.get_user(token)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Add user to request state for use in route handlers
            scope["state"] = scope.get("state", {})
            scope["state"]["user"] = user

            return await self.app(scope, receive, send)

        except HTTPException as e:
            response_body = json.dumps({"detail": e.detail}).encode()
            headers = e.headers or {}
            
            await send({
                "type": "http.response.start",
                "status": e.status_code,
                "headers": [
                    [b"content-type", b"application/json"],
                    *[[k.encode(), v.encode()] for k, v in headers.items()]
                ],
            })
            
            await send({
                "type": "http.response.body",
                "body": response_body,
            })
        except Exception as e:
            print(e)
            response_body = json.dumps({"detail": "Internal Server error"}).encode()
            
            await send({
                "type": "http.response.start",
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "headers": [
                    [b"content-type", b"application/json"],
                    [b"www-authenticate", b"Bearer"],
                ],
            })
            
            await send({
                "type": "http.response.body",
                "body": response_body,
            }) 